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
    along with the note, timestamp, hotel_room_id FK, and who triggered it.

    Returns the inserted document or None on failure.
    """
    try:
        db = get_database()
        now = now_iso()

        # Resolve hotel_room_id from room_label + prop_id
        hotel_room_id = _resolve_hotel_room_id(db, prop_id, room_label)

        doc = {
            "prop_id": prop_id,
            "room_label": room_label,
            "hotel_room_id": hotel_room_id,
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
            "Room status history logged: %s → %s (room=%s hotel_room_id=%s prop=%s)",
            old_status, new_status, room_label, hotel_room_id, prop_id,
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
    room_id: str | None = None,
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
    if room_id:
        query["hotel_room_id"] = room_id
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
    doc["hotelRoomId"] = doc.get("hotel_room_id", "")
    doc["oldStatus"] = doc.get("old_status", "")
    doc["newStatus"] = doc.get("new_status", "")
    doc["changedBy"] = doc.get("changed_by", "")
    doc["bookingId"] = doc.get("booking_id", "")
    return doc


def _resolve_hotel_room_id(db, prop_id: int, room_label: str) -> str:
    """Resolve hotel_room_id from room_label + prop_id.

    Looks up hotel_rooms first, then falls back to room_status_log.
    Returns "" if no match found.
    """
    # Try hotel_rooms (canonical source)
    room = db.hotel_rooms.find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"hotel_room_id": 1},
    )
    if room and room.get("hotel_room_id"):
        return room["hotel_room_id"]

    # Fallback to room_status_log
    from ..collections import ROOM_STATUS_COLLECTION
    status_doc = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"hotel_room_id": 1},
    )
    if status_doc and status_doc.get("hotel_room_id"):
        return status_doc["hotel_room_id"]

    return ""


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
