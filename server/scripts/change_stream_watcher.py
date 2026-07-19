"""MongoDB Change Stream watcher — hybrid audit enrichment.

Listens to insert/update/replace operations on configured collections and
enriches the most recent audit_log entry with a document-level diff.

If no manual audit_log entry exists (register_action not called),
creates a minimal fallback entry so no change goes untracked.

Usage:
    python change_stream_watcher.py

Environment:
    MONGO_URI       - MongoDB connection string (default: mongodb://mongo:27018)
    MONGO_DATABASE  - Database name (default: hoteldata_hub)
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] change_stream: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27018")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "hoteldata_hub")

# How long to wait for the register_action() audit entry to appear
AUDIT_LOOKUP_RETRY_SECONDS: float = 1.5
AUDIT_LOOKUP_MAX_RETRIES: int = 4

# Fields to exclude from the diff (internal / noisy)
SKIP_FIELDS: set[str] = {"_id", "updated_at", "created_at", "__v"}


@dataclass(frozen=True)
class WatchedCollection:
    """Configuration for a collection watched by the change stream."""

    name: str
    entity_type: str
    id_field: str
    title_field: str
    status_field: str | None = None
    insert_fields: tuple[str, ...] | None = None


# Collections that participate in the hybrid audit
WATCHED_COLLECTIONS = [
    WatchedCollection(
        name="booking_orders",
        entity_type="reservation",
        id_field="booking_id",
        title_field="guest_name",
        status_field="status",
        insert_fields=(
            "booking_id", "guest_name", "prop_id", "status",
            "check_in_date", "check_out_date", "total_price",
        ),
    ),
    WatchedCollection(
        name="expense_invoices",
        entity_type="expense_invoice",
        id_field="_id",
        title_field="vendor_name",
        status_field="status",
        insert_fields=(
            "vendor_name", "category", "description", "amount",
            "tax_amount", "total", "status", "invoice_date",
            "due_date", "prop_id",
        ),
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────────

def _connect() -> tuple[MongoClient, Any]:
    """Connect to MongoDB and return (client, db)."""
    for attempt in range(1, 11):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
            client.admin.command("ping")
            db = client[MONGO_DATABASE]
            logger.info("Connected to %s / %s", MONGO_URI, MONGO_DATABASE)
            return client, db
        except ConnectionFailure:
            logger.warning(
                "MongoDB not ready (attempt %d/10) — retrying in 5s...", attempt,
            )
            time.sleep(5)
    raise RuntimeError("Could not connect to MongoDB after 10 attempts")


# ──────────────────────────────────────────────────────────────────────────────
# Diff builder
# ──────────────────────────────────────────────────────────────────────────────

def _serialize_value(value: Any) -> Any:
    """Recursively convert MongoDB types to JSON-safe Python types."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "strftime"):
        return value.isoformat() if callable(value.isoformat) else str(value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _build_diff(
    operation_type: str,
    full_document: dict[str, Any] | None,
    update_description: dict[str, Any] | None,
    insert_fields: tuple[str, ...] | None = None,
) -> dict[str, Any] | None:
    """Build a human-readable diff from a Change Stream event."""
    if operation_type == "insert" and full_document:
        if insert_fields:
            snapshot = {
                k: _serialize_value(full_document[k])
                for k in insert_fields
                if k in full_document and k not in SKIP_FIELDS
            }
        else:
            snapshot = {
                k: _serialize_value(v)
                for k, v in full_document.items()
                if k not in SKIP_FIELDS
            }
        return {"operation": "insert", "snapshot": snapshot}

    if operation_type in ("update", "replace") and update_description:
        updated = update_description.get("updatedFields", {}) or {}
        removed = update_description.get("removedFields", []) or []
        truncated = update_description.get("truncatedArrays", []) or []

        changed = {
            k: _serialize_value(v)
            for k, v in updated.items()
            if k not in SKIP_FIELDS and not k.startswith("check_out_")
        }

        diff: dict[str, Any] = {"operation": operation_type}
        has_content = False

        if changed:
            diff["changed_fields"] = changed
            has_content = True
        if removed:
            diff["removed_fields"] = [f for f in removed if f not in SKIP_FIELDS]
            has_content = True
        if truncated:
            diff["truncated_arrays"] = truncated
            has_content = True

        return diff if has_content else None

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Enrichment — find audit_log entry & update / create fallback
# ──────────────────────────────────────────────────────────────────────────────

def _enrich_or_create(
    audit_log_col: Any,
    entity_id: str,
    entity_type: str,
    diff: dict[str, Any],
    prop_id: int,
    title: str,
    status: str,
    event_time: datetime,
) -> str:
    """Find the matching audit_log entry and add the diff field.

    If no manual entry is found after retries, creates a minimal
    fallback entry so the change is never lost.

    Returns one of: "enriched", "fallback", "skipped".
    """
    for attempt in range(AUDIT_LOOKUP_MAX_RETRIES):
        entry = audit_log_col.find_one(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "timestamp": {"$lte": event_time},
            },
            sort=[("timestamp", -1)],
            projection={"_id": 1, "action": 1},
        )
        if entry is not None:
            audit_log_col.update_one(
                {"_id": entry["_id"]},
                {"$set": {"diff": diff}},
            )
            return "enriched"

        if attempt < AUDIT_LOOKUP_MAX_RETRIES - 1:
            logger.debug(
                "Waiting for audit entry for %s %s (attempt %d/%d)...",
                entity_type, entity_id, attempt + 1, AUDIT_LOOKUP_MAX_RETRIES,
            )
            time.sleep(AUDIT_LOOKUP_RETRY_SECONDS)

    # No manual entry — create fallback
    audit_log_col.insert_one({
        "timestamp": event_time,
        "prop_id": prop_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": "document_change",
        "summary": f"Cambio automático detectado — {title} (status: {status})",
        "changed_by": "change_stream",
        "diff": diff,
    })
    return "fallback"


# ──────────────────────────────────────────────────────────────────────────────
# Watch loop for a single collection
# ──────────────────────────────────────────────────────────────────────────────

def _watch_collection(
    client: MongoClient,
    db: Any,
    config: WatchedCollection,
) -> None:
    """Open Change Stream on a configured collection and process events forever."""
    collection = db[config.name]
    audit_log = db.audit_log

    # Ensure indexes on audit_log for enrichment queries
    audit_log.create_index([("entity_type", 1), ("entity_id", 1), ("timestamp", -1)])

    pipeline: list[dict[str, Any]] = [
        {"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}},
    ]

    resume_token: Any = None

    while True:
        try:
            stream_opts: dict[str, Any] = {"full_document": "updateLookup"}
            if resume_token:
                stream_opts["resume_after"] = resume_token

            with collection.watch(pipeline, **stream_opts) as stream:
                logger.info("Change Stream active — watching %s...", config.name)
                resume_token = stream.resume_token

                for change in stream:  # type: ignore[attr-defined]
                    resume_token = change.get("_id")
                    op_type: str = change.get("operationType", "unknown")
                    doc_key: dict[str, Any] = change.get("documentKey", {})

                    entity_id = str(doc_key.get(config.id_field) or doc_key.get("_id", ""))
                    if not entity_id:
                        continue

                    full_doc: dict[str, Any] | None = change.get("fullDocument")
                    update_desc: dict[str, Any] | None = change.get("updateDescription")

                    # Skip test bookings
                    if full_doc and full_doc.get("is_test"):
                        continue

                    prop_id = int(full_doc.get("prop_id", 0)) if full_doc else 0
                    title = str(full_doc.get(config.title_field, "desconocido")) if full_doc else "desconocido"
                    status = str(full_doc.get(config.status_field, "")) if full_doc and config.status_field else ""

                    diff = _build_diff(op_type, full_doc, update_desc, config.insert_fields)
                    if not diff:
                        logger.debug(
                            "Skipping empty diff for %s %s (%s)", config.entity_type, entity_id, op_type,
                        )
                        continue

                    event_time = datetime.now(UTC)
                    result = _enrich_or_create(
                        audit_log, entity_id, config.entity_type, diff,
                        prop_id, title, status, event_time,
                    )

                    field_count = len(diff.get("changed_fields", {})) or len(diff.get("snapshot", {}))
                    logger.info(
                        "[%s] %s %s (%s) — %d fields changed",
                        result, config.entity_type, entity_id, op_type, field_count,
                    )

        except (PyMongoError, OperationFailure) as exc:
            logger.error("Change Stream error on %s: %s — reconnecting in 5s...", config.name, exc)
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutting down (SIGINT)...")
            break
        except Exception:
            logger.exception("Unexpected error on %s — reconnecting in 5s...", config.name)
            time.sleep(5)


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def watch() -> None:
    """Start change stream watchers for all configured collections."""
    client, db = _connect()

    threads: list[threading.Thread] = []
    for config in WATCHED_COLLECTIONS:
        t = threading.Thread(target=_watch_collection, args=(client, db, config), daemon=True)
        t.start()
        threads.append(t)
        logger.info("Started watcher thread for %s", config.name)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down (SIGINT)...")
    finally:
        client.close()
        logger.info("Watcher stopped.")


if __name__ == "__main__":
    logger.info(
        "Starting Change Stream watcher — %s / %s", MONGO_URI, MONGO_DATABASE,
    )
    watch()
