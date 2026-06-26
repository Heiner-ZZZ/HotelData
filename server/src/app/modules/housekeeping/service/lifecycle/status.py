"""Room status operations and enrichment helpers."""

from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from ..collections import ROOM_STATUS_COLLECTION
from ...schemas import RoomStatusLogCreate, now_iso

HOTEL_ROOMS_COLLECTION = "hotel_rooms"


def upsert_room_status(payload: RoomStatusLogCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()
    doc = {
        "prop_id": payload.prop_id, "room_type_id": payload.room_type_id,
        "room_label": payload.room_label, "status": payload.status,
        "note": payload.note, "updated_at": now,
    }
    result = db[ROOM_STATUS_COLLECTION].update_one(
        {"prop_id": payload.prop_id, "room_label": payload.room_label},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    if result.upserted_id:
        doc["_id"] = result.upserted_id
        doc["created_at"] = now
    else:
        existing = db[ROOM_STATUS_COLLECTION].find_one(
            {"prop_id": payload.prop_id, "room_label": payload.room_label}
        )
        if existing:
            doc["_id"] = existing["_id"]
            doc["created_at"] = existing.get("created_at", now)
    return _enrich_room_status(doc)


def list_room_status(
    prop_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    total = db[ROOM_STATUS_COLLECTION].count_documents(query)
    cursor = db[ROOM_STATUS_COLLECTION].find(query).sort("room_label", 1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_room_status(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def get_room_status(record_id: str) -> dict[str, Any] | None:
    db = get_database()
    doc = db[ROOM_STATUS_COLLECTION].find_one({"_id": ObjectId(record_id)})
    return _enrich_room_status(doc) if doc else None


def update_room_status_bulk(prop_id: int, room_labels: list[str], new_status: str, note: str = "") -> int:
    db = get_database()
    now = now_iso()
    result = db[ROOM_STATUS_COLLECTION].update_many(
        {"prop_id": prop_id, "room_label": {"$in": room_labels}},
        {"$set": {"status": new_status, "note": note, "updated_at": now}},
    )
    return result.modified_count


def sync_room_status_from_hotel_rooms(prop_id: int) -> dict[str, Any]:
    """Auto‑seed room_status_log from hotel_rooms for a property.

    Creates missing records (does not overwrite existing ones) so the
    housekeeping rooms page reflects all known rooms.
    """
    db = get_database()
    now = now_iso()
    rooms = list(db[HOTEL_ROOMS_COLLECTION].find(
        {"prop_id": prop_id},
        {"hotel_room_id": 1, "room_type_id": 1, "room_label": 1, "is_active": 1},
    ))

    created = 0
    for room in rooms:
        room_type_id = room.get("room_type_id", "")
        room_label = room.get("room_label", "")
        if not room_label:
            continue

        existing = db[ROOM_STATUS_COLLECTION].find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"_id": 1},
        )
        if existing:
            continue

        db[ROOM_STATUS_COLLECTION].insert_one({
            "prop_id": prop_id,
            "room_type_id": room_type_id,
            "room_label": room_label,
            "status": "available",
            "note": "",
            "created_at": now,
            "updated_at": now,
        })
        created += 1

    return {"synced": True, "prop_id": prop_id, "created": created, "total_rooms": len(rooms)}


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None


def _enrich_room_status(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    return doc
