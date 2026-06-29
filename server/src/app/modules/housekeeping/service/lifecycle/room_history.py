"""Room status history / audit trail for every room status change."""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from src.database.connection import get_database
from ..collections import ROOM_STATUS_HISTORY_COLLECTION
from ...schemas import now_iso

logger = logging.getLogger(__name__)


def log_room_status_change(
    *,
    prop_id: int,
    room_label: str,
    old_status: str,
    new_status: str,
    note: str = "",
    changed_by: str = "system",
    booking_id: str | None = None,
) -> dict[str, Any] | None:
    """Insert an audit record every time a room status changes.

    Each record captures the transition from old_status → new_status,
    along with the note, timestamp, and who/what triggered it.

    Returns the inserted document or None on failure.
    """
    try:
        db = get_database()
        now = now_iso()
        doc = {
            "prop_id": prop_id,
            "room_label": room_label,
            "old_status": old_status,
            "new_status": new_status,
            "note": note or "",
            "changed_by": changed_by,
            "created_at": now,
        }
        if booking_id:
            doc["booking_id"] = booking_id

        result = db[ROOM_STATUS_HISTORY_COLLECTION].insert_one(doc)
        doc["_id"] = result.inserted_id
        logger.debug(
            "Room status history logged: %s → %s (room=%s prop=%s)",
            old_status, new_status, room_label, prop_id,
        )
        return _enrich_history_entry(doc)
    except Exception:
        logger.exception(
            "Failed to log room status change for %s (prop=%s) [%s → %s]",
            room_label, prop_id, old_status, new_status,
        )
        return None


def list_room_status_history(
    *,
    prop_id: int | None = None,
    room_label: str | None = None,
    booking_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """List room status history with optional filters, most recent first."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if room_label:
        query["room_label"] = room_label
    if booking_id:
        query["booking_id"] = booking_id

    total = db[ROOM_STATUS_HISTORY_COLLECTION].count_documents(query)
    cursor = (
        db[ROOM_STATUS_HISTORY_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_history_entry(doc) for doc in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def _enrich_history_entry(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc:
        doc["created_at"] = _fmt(doc["created_at"])
    # camelCase aliases for frontend
    doc["propId"] = doc.get("prop_id", 0)
    doc["roomLabel"] = doc.get("room_label", "")
    doc["oldStatus"] = doc.get("old_status", "")
    doc["newStatus"] = doc.get("new_status", "")
    doc["changedBy"] = doc.get("changed_by", "")
    doc["bookingId"] = doc.get("booking_id", "")
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
