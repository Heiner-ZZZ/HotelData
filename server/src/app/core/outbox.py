"""Transactional Outbox Pattern for atomic dual-write between operational
and analytical (fact_*) MongoDB collections.

Problem: ``_write_both()`` in reviews and billing modules inserted into
operational and fact collections sequentially. If the second insert failed,
the first was already committed → data inconsistency.

Solution: Write operational document + outbox event in a single MongoDB
transaction, then process the outbox synchronously. If outbox processing
fails, the event stays in the outbox collection for retry.

Usage::

    from src.app.core.outbox import write_with_outbox, update_with_outbox

    # Replace _write_both(collection, fact_collection, doc)
    result_id = write_with_outbox(db, collection, fact_collection, doc)

    # Replace _update_both(collection, fact_collection, doc_id, update)
    update_with_outbox(db, collection, fact_collection, doc_id, update)

Reference: Transactional Outbox — https://microservices.io/patterns/data/transactional-outbox.html
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TypedDict

from bson import ObjectId
from pymongo import IndexModel, ASCENDING
from pymongo.errors import OperationFailure

from src.database.collections import ensure_collection

logger = logging.getLogger(__name__)

OUTBOX_COLLECTION = "outbox"

OUTBOX_STATUS_PENDING = "pending"
OUTBOX_STATUS_PROCESSED = "processed"
OUTBOX_STATUS_FAILED = "failed"
OUTBOX_MAX_RETRIES = 3


class OutboxEvent(TypedDict, total=False):
    """TypedDict for outbox event documents in MongoDB.

    ``total=False`` means all fields are optional — insert events have
    ``document`` and ``operational_id``; update events have ``document_id``
    and ``update``.
    """

    _id: ObjectId
    event_type: str
    target_collection: str
    fact_collection: str
    status: str
    retries: int
    created_at: datetime
    # Insert-specific
    document: dict
    document_id: ObjectId
    operational_id: ObjectId
    # Update-specific
    update: dict
    # Lifecycle
    processed_at: datetime
    last_error: str
    error: str


OUTBOX_INDEXES = [
    IndexModel([("status", ASCENDING), ("created_at", ASCENDING)], name="idx_outbox_status_created"),
    IndexModel(
        [("created_at", ASCENDING)],
        name="idx_outbox_created_ttl",
        expireAfterSeconds=2592000,  # 30 days TTL — only for processed/done events
        partialFilterExpression={"status": {"$in": [OUTBOX_STATUS_PROCESSED, OUTBOX_STATUS_FAILED]}},
    ),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_outbox_collection() -> None:
    ensure_collection(OUTBOX_COLLECTION, OUTBOX_INDEXES)


# ── Public API ──────────────────────────────────────────────────────────


def write_with_outbox(
    db,
    collection_name: str,
    doc: dict,
    fact_collection_name: str,
) -> ObjectId:
    """Insert *doc* into *collection_name* and record an outbox event
    for *fact_collection_name* atomically via a MongoDB transaction.

    Returns the inserted document's ObjectId.
    """
    now = _now()
    doc.setdefault("created_at", now)

    outbox_event = {
        "event_type": "insert",
        "target_collection": collection_name,
        "fact_collection": fact_collection_name,
        "document": doc,
        "status": OUTBOX_STATUS_PENDING,
        "retries": 0,
        "created_at": now,
    }

    try:
        with db.client.start_session() as session:
            with session.start_transaction():
                result = db[collection_name].insert_one(doc, session=session)
                doc["_id"] = result.inserted_id
                outbox_event["document"]["_id"] = result.inserted_id  # type: ignore[index]
                outbox_event["document_id"] = result.inserted_id
                outbox_event["operational_id"] = result.inserted_id
                db[OUTBOX_COLLECTION].insert_one(outbox_event, session=session)

        # Immediately process the outbox synchronously
        _process_one(db, collection_name, fact_collection_name, outbox_event)  # type: ignore[arg-type]

    except OperationFailure:
        logger.exception("Outbox transaction failed for collection=%s", collection_name)
        raise

    return doc["_id"]


def update_with_outbox(
    db,
    collection_name: str,
    doc_id: ObjectId,
    update: dict,
    fact_collection_name: str,
) -> None:
    """Update document *doc_id* in *collection_name* and record an outbox
    event for *fact_collection_name* atomically via a MongoDB transaction.
    """
    now = _now()
    if "$set" in update:
        update = {**update, "$set": {**update["$set"], "updated_at": now}}

    outbox_event = {
        "event_type": "update",
        "target_collection": collection_name,
        "fact_collection": fact_collection_name,
        "document_id": doc_id,
        "update": update,
        "status": OUTBOX_STATUS_PENDING,
        "retries": 0,
        "created_at": now,
    }

    try:
        with db.client.start_session() as session:
            with session.start_transaction():
                db[collection_name].update_one({"_id": doc_id}, update, session=session)
                db[OUTBOX_COLLECTION].insert_one(outbox_event, session=session)

        # Immediately process the outbox synchronously
        _process_one(db, collection_name, fact_collection_name, outbox_event)  # type: ignore[arg-type]

    except OperationFailure:
        logger.exception("Outbox transaction failed for collection=%s doc_id=%s", collection_name, doc_id)
        raise


def process_pending_outbox(db) -> int:
    """Process all pending outbox events. Called on startup and
    periodically to catch up on any failed propagations.

    Returns the number of events processed.
    """
    processed = 0
    cursor = db[OUTBOX_COLLECTION].find(
        {"status": OUTBOX_STATUS_PENDING, "retries": {"$lt": OUTBOX_MAX_RETRIES}}
    ).sort("created_at", 1)

    for event in cursor:
        collection_name = event["target_collection"]
        fact_collection_name = event["fact_collection"]
        success = _process_one(db, collection_name, fact_collection_name, event)
        if success:
            processed += 1

    return processed


# ── Internal helpers ────────────────────────────────────────────────────


def _process_one(db, collection_name: str, fact_collection_name: str, event: OutboxEvent) -> bool:
    """Process a single outbox event: write to the fact collection.

    On success, mark the outbox event as processed.
    On failure, increment retry count.
    """
    event_type = event.get("event_type", "insert")
    event_id = event["_id"]

    try:
        if event_type == "insert":
            doc = event["document"]
            fact_doc = {**doc, "operational_id": event.get("operational_id", doc.get("_id"))}
            # Ensure _id matches operational for lookups
            if "_id" in fact_doc and fact_doc["_id"] == event.get("operational_id"):
                pass  # keep same _id
            db[fact_collection_name].update_one(
                {"_id": fact_doc.get("_id")},
                {"$set": fact_doc},
                upsert=True,
            )

        elif event_type == "update":
            doc_id = event["document_id"]
            update = event["update"]
            db[fact_collection_name].update_one({"_id": doc_id}, update)

        elif event_type == "audit_log_insert":
            # Audit log uses pre-generated _id (see enqueue_audit_log) so the
            # upsert is idempotent across retries and avoids double-row insert.
            doc = event["document"]
            db[fact_collection_name].update_one(
                {"_id": doc["_id"]},
                {"$set": doc},
                upsert=True,
            )

        else:
            logger.warning("Unknown outbox event_type=%s for event=%s", event_type, event_id)
            db[OUTBOX_COLLECTION].update_one(
                {"_id": event_id},
                {"$set": {"status": OUTBOX_STATUS_FAILED, "error": "unknown event_type"}},
            )
            return False

        db[OUTBOX_COLLECTION].update_one(
            {"_id": event_id},
            {"$set": {"status": OUTBOX_STATUS_PROCESSED, "processed_at": _now()}},
        )
        return True

    except Exception as exc:
        logger.warning(
            "Outbox event %s failed (retry %d/%d): %s",
            event_id, event.get("retries", 0) + 1, OUTBOX_MAX_RETRIES, exc,
        )
        db[OUTBOX_COLLECTION].update_one(
            {"_id": event_id},
            {
                "$inc": {"retries": 1},
                "$set": {
                    "status": OUTBOX_STATUS_FAILED if event.get("retries", 0) >= OUTBOX_MAX_RETRIES - 1 else OUTBOX_STATUS_PENDING,
                    "last_error": str(exc)[:500],
                },
            },
        )
        return False


# ── Audit-log short-circuit ────────────────────────────────────────────
# Specialized outbox writer for ``audit_log``: pre-generates ``_id`` so the
# processor's upsert is idempotent across retries. Keeps the inline-then-
# drain pattern but with a tighter event_type branch (``audit_log_insert``)
# that does ``update_one(_id, $setOnInsert)`` directly without the dual
# fact-collection walk-through that reviews/billing need.


def enqueue_audit_log(db, entry: dict) -> None:
    """Write an audit_log row through the outbox pattern.

    Persists the entry to the ``outbox`` collection (~1-2 ms) and immediately
    drains to ``audit_log`` via ``_process_one``. Pre-generating ``_id``
    makes the processor's upsert idempotent across retries. Transient
    inline failures are caught here so audit_log writes are best-effort
    vs the user-facing request — the outbox drainer picks them up.
    """
    if "_id" not in entry:
        entry = {**entry, "_id": ObjectId()}
    now = _now()
    event: OutboxEvent = {
        "event_type": "audit_log_insert",
        "target_collection": "audit_log",
        "fact_collection": "audit_log",
        "document": entry,
        "status": OUTBOX_STATUS_PENDING,
        "retries": 0,
        "created_at": now,
    }
    db[OUTBOX_COLLECTION].insert_one(event)
    try:
        _process_one(db, "audit_log", "audit_log", event)
    except Exception:
        logger.exception(
            "Failed inline outbox processing for audit_log (will retry via drainer)"
        )


def process_pending_outbox_forever(db, *, interval_seconds: int = 60) -> None:
    """Periodic background drainer for outbox events.

    Daemon thread that catches up on any ``audit_log`` writes that failed
    inline (e.g. transient mongo blip). Sleeps ``interval_seconds``
    between sweeps; interruptible via threading.Event so SIGTERM tears
    down cleanly without hanging.
    """
    import threading

    def worker() -> None:
        logger.info(
            "Starting outbox drainer thread (interval=%ss)", interval_seconds
        )
        while True:
            try:
                processed = process_pending_outbox(db)
                if processed:
                    logger.debug(
                        "Outbox drainer processed %d pending events", processed
                    )
            except Exception:
                logger.exception(
                    "Outbox drainer sweep failed; will retry on next interval"
                )
            threading.Event().wait(interval_seconds)

    t = threading.Thread(target=worker, daemon=True, name="OutboxDrainer")
    t.start()

