"""MongoDB Change Stream watcher — booking_orders → audit_log enrichment.

Listens to insert/update/replace operations on booking_orders and
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
import time
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


# ──────────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────────

def _connect() -> tuple[MongoClient, Any, Any, Any]:
    """Connect to MongoDB and return (client, db, booking_orders, audit_log)."""
    for attempt in range(1, 11):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
            client.admin.command("ping")
            db = client[MONGO_DATABASE]
            logger.info("Connected to %s / %s", MONGO_URI, MONGO_DATABASE)
            return client, db, db.booking_orders, db.audit_log
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
) -> dict[str, Any] | None:
    """Build a human-readable diff from a Change Stream event.

    Returns a dict suitable for the audit_log.diff field, or None
    if there is nothing meaningful to record.
    """
    if operation_type == "insert" and full_document:
        # For inserts, record key fields (not the full doc — too noisy)
        return {
            "operation": "insert",
            "booking_id": full_document.get("booking_id"),
            "guest_name": full_document.get("guest_name"),
            "prop_id": full_document.get("prop_id"),
            "status": full_document.get("status"),
            "check_in_date": full_document.get("check_in_date"),
            "check_out_date": full_document.get("check_out_date"),
            "total_price": full_document.get("total_price"),
        }

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
    booking_id: str,
    diff: dict[str, Any],
    prop_id: int,
    guest_name: str,
    new_status: str,
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
                "entity_type": "reservation",
                "entity_id": booking_id,
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
                "Waiting for audit entry for booking %s (attempt %d/%d)...",
                booking_id, attempt + 1, AUDIT_LOOKUP_MAX_RETRIES,
            )
            time.sleep(AUDIT_LOOKUP_RETRY_SECONDS)

    # No manual entry — create fallback
    audit_log_col.insert_one({
        "timestamp": event_time,
        "prop_id": prop_id,
        "entity_type": "reservation",
        "entity_id": booking_id,
        "action": "document_change",
        "summary": f"Cambio automático detectado — {guest_name} (status: {new_status})",
        "changed_by": "change_stream",
        "diff": diff,
    })
    return "fallback"


# ──────────────────────────────────────────────────────────────────────────────
# Main watch loop
# ──────────────────────────────────────────────────────────────────────────────

def watch() -> None:
    """Open Change Stream on booking_orders and process events forever."""
    client, db, booking_orders, audit_log = _connect()

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
                stream_opts["resumeAfter"] = resume_token

            with booking_orders.watch(pipeline, **stream_opts) as stream:
                logger.info("Change Stream active — watching booking_orders...")
                resume_token = stream.resume_token

                for change in stream:  # type: ignore[attr-defined]
                    resume_token = change.get("_id")
                    op_type: str = change.get("operationType", "unknown")
                    doc_key: dict[str, Any] = change.get("documentKey", {})
                    booking_id: str = str(
                        doc_key.get("booking_id") or doc_key.get("_id", "")
                    )

                    if not booking_id:
                        continue

                    full_doc: dict[str, Any] | None = change.get("fullDocument")
                    update_desc: dict[str, Any] | None = change.get(
                        "updateDescription"
                    )

                    # Skip test bookings
                    if full_doc and full_doc.get("is_test"):
                        continue

                    prop_id = int(full_doc.get("prop_id", 0)) if full_doc else 0
                    guest_name = (
                        full_doc.get("guest_name", "desconocido")
                        if full_doc
                        else "desconocido"
                    )
                    new_status = full_doc.get("status", "") if full_doc else ""

                    diff = _build_diff(op_type, full_doc, update_desc)
                    if not diff:
                        logger.debug(
                            "Skipping empty diff for booking %s (%s)", booking_id, op_type,
                        )
                        continue

                    event_time = datetime.now(UTC)
                    result = _enrich_or_create(
                        audit_log, booking_id, diff, prop_id,
                        guest_name, new_status, event_time,
                    )

                    field_count = len(diff.get("changed_fields", {}))
                    logger.info(
                        "[%s] booking %s (%s) — %d fields changed",
                        result, booking_id, op_type, field_count,
                    )

        except (PyMongoError, OperationFailure) as exc:
            logger.error("Change Stream error: %s — reconnecting in 5s...", exc)
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutting down (SIGINT)...")
            break
        except Exception:
            logger.exception("Unexpected error — reconnecting in 5s...")
            time.sleep(5)

    client.close()
    logger.info("Watcher stopped.")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "Starting Change Stream watcher — %s / %s", MONGO_URI, MONGO_DATABASE,
    )
    watch()
