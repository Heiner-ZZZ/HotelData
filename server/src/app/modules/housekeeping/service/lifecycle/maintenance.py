"""Maintenance task operations."""

from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId

from pymongo import ReturnDocument

from src.database.connection import get_database
from ..collections import MAINTENANCE_COLLECTION
from ...schemas import MaintenanceTaskCreate, now_iso


def _resolve_room_from_id(room_id: str, prop_id: int | None = None) -> dict[str, Any] | None:
    """Resolve a hotel room document by its business ID (hotel_room_id)."""
    db = get_database()
    query: dict[str, Any] = {"hotel_room_id": room_id}
    if prop_id is not None:
        query["prop_id"] = prop_id
    return db.hotel_rooms.find_one(
        query,
        {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1, "room_type_id": 1, "prop_id": 1, "floor": 1},
    )


def _room_match(prop_id: int, room_id: str | None = None, room_label: str | None = None) -> dict:
    """Build a query that matches a room_status_log doc by hotel_room_id or room_label/room_number."""
    query: dict[str, Any] = {"prop_id": prop_id}
    if room_id:
        query["hotel_room_id"] = room_id
    elif room_label:
        query["$or"] = [{"room_label": room_label}, {"room_number": room_label}]
    return query


def _auto_block_room(db: Any, prop_id: int, room_id: str, room_label: str, scheduled_date: str) -> None:
    """Mark the room as 'maintenance' in room_status_log and create blackout_date.

    RF-002: Bloquear disponibilidad durante mantenimiento.
    This ensures the room cannot be booked while under maintenance.
    """
    if not room_id and not room_label:
        return
    # Update room status to 'maintenance' — prefer hotel_room_id
    db.room_status_log.update_one(
        _room_match(prop_id, room_id=room_id, room_label=room_label),
        {
            "$set": {
                "status": "maintenance_requested",
                "note": "Mantenimiento programado",
                "updated_at": now_iso(),
                "hotel_room_id": room_id,
                "room_label": room_label,
            },
            "$setOnInsert": {"created_at": now_iso()},
        },
        upsert=True,
    )
    # Create blackout date entry for the scheduled date
    if scheduled_date:
        existing = db.blackout_dates.find_one({
            "prop_id": prop_id,
            "room_label": room_label,
            "start_date": scheduled_date,
            "end_date": scheduled_date,
            "source": "maintenance",
        })
        if not existing:
            db.blackout_dates.insert_one({
                "prop_id": prop_id,
                "room_label": room_label,
                "start_date": scheduled_date,
                "end_date": scheduled_date,
                "source": "maintenance",
                "reason": "Mantenimiento programado",
                "created_at": now_iso(),
            })


def _unblock_room(db: Any, prop_id: int, room_id: str, room_label: str, scheduled_date: str) -> None:
    """Restore room status to 'available' and remove blackout dates.

    Called when maintenance is completed or deleted.
    """
    if not room_id and not room_label:
        return
    # Only restore if the room is still in a blocked state — prefer hotel_room_id
    match = _room_match(prop_id, room_id=room_id, room_label=room_label)
    current = db.room_status_log.find_one(match, {"status": 1})
    if current and current.get("status") in ("maintenance_requested", "out_of_service", "out_of_order"):
        # Restore to vacant_clean (the new housekeeping status)
        db.room_status_log.update_one(
            match,
            {"$set": {"status": "vacant_clean", "note": "", "updated_at": now_iso()}},
        )
    # Remove blackout dates created by maintenance
    if scheduled_date:
        db.blackout_dates.delete_many({
            "prop_id": prop_id,
            "room_label": room_label,
            "start_date": scheduled_date,
            "end_date": scheduled_date,
            "source": "maintenance",
        })


def create_maintenance_task(payload: MaintenanceTaskCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()
    room = _resolve_room_from_id(payload.room_id, payload.prop_id)
    if not room:
        raise ValueError(f"Habitación no encontrada: {payload.room_id}")

    status = payload.status or "scheduled"
    completed_at = now if status == "completed" else None
    room_label = room.get("room_label") or room.get("room_number") or payload.room_id
    doc = {
        "prop_id": room["prop_id"],
        "room_id": room["hotel_room_id"],
        "room_label": room_label,
        "room_type_id": room.get("room_type_id", ""),
        "room_number": room.get("room_number", ""),
        "task_type": payload.task_type,
        "title": payload.title,
        "description": payload.description,
        "status": status,
        "priority": payload.priority,
        "scheduled_date": payload.scheduled_date,
        "auto_block": payload.auto_block,
        "created_at": now,
        "completed_at": completed_at,
    }
    result = db[MAINTENANCE_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    # RF-002: Auto-block room availability if auto_block is True and not completed
    if payload.auto_block and status != "completed":
        try:
            _auto_block_room(db, room["prop_id"], room["hotel_room_id"], room_label, payload.scheduled_date)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to auto-block room for maintenance task")
    return _enrich_mt_task(doc)


def list_maintenance_tasks(
    prop_id: int | None = None, status_filter: str | None = None,
    priority: str | None = None,
    page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {"status": {"$ne": "deleted"}}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    if priority:
        query["priority"] = priority
    total = db[MAINTENANCE_COLLECTION].count_documents(query)
    cursor = db[MAINTENANCE_COLLECTION].find(query).sort("scheduled_date", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_mt_task(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def update_maintenance_task(task_id: str, payload: MaintenanceTaskCreate) -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    status = payload.status or "scheduled"
    # Resolve room from the provided room_id so denormalized fields stay in sync
    room = _resolve_room_from_id(payload.room_id, payload.prop_id)
    if not room:
        raise ValueError(f"Habitación no encontrada: {payload.room_id}")

    # Fetch previous state to know if we need to unblock old room
    prev = db[MAINTENANCE_COLLECTION].find_one({"_id": ObjectId(task_id)})
    room_label = room.get("room_label") or room.get("room_number") or payload.room_id

    set_data = {
        "prop_id": room["prop_id"],
        "room_id": room["hotel_room_id"],
        "room_label": room_label,
        "room_type_id": room.get("room_type_id", ""),
        "room_number": room.get("room_number", ""),
        "task_type": payload.task_type,
        "title": payload.title,
        "description": payload.description or "",
        "priority": payload.priority,
        "scheduled_date": payload.scheduled_date,
        "auto_block": payload.auto_block,
        "status": status,
        "updated_at": now,
    }
    if status == "completed":
        set_data["completed_at"] = now
    else:
        set_data["completed_at"] = None

    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id)},
        {"$set": set_data},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        # If auto_block was enabled on prev, unblock old first
        if prev and prev.get("auto_block"):
            _unblock_room(
                db,
                prev.get("prop_id", 0),
                prev.get("room_id", ""),
                prev.get("room_label", ""),
                prev.get("scheduled_date", ""),
            )

        # If new status is not completed and auto_block is True, block new room/date
        if status != "completed" and payload.auto_block:
            _auto_block_room(
                db,
                room["prop_id"],
                room["hotel_room_id"],
                room_label,
                payload.scheduled_date,
            )

    return _enrich_mt_task(doc) if doc else None


def complete_maintenance_task(task_id: str, note: str = "") -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    update = {"$set": {"status": "completed", "completed_at": now}}
    if note:
        update["$set"]["note"] = note
    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$in": ["scheduled", "in_progress", "inspection"]}},
        update, return_document=True,
    )
    if doc and doc.get("auto_block"):
        try:
            _unblock_room(
                db,
                doc.get("prop_id", 0),
                doc.get("room_id", ""),
                doc.get("room_label", ""),
                doc.get("scheduled_date", ""),
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to unblock room on maintenance completion")
    return _enrich_mt_task(doc) if doc else None


def delete_maintenance_task(task_id: str) -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$ne": "deleted"}},
        {"$set": {"status": "deleted", "deleted_at": now}},
        return_document=True,
    )
    if doc and doc.get("auto_block"):
        try:
            _unblock_room(
                db,
                doc.get("prop_id", 0),
                doc.get("room_id", ""),
                doc.get("room_label", ""),
                doc.get("scheduled_date", ""),
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to unblock room on maintenance deletion")
    return _enrich_mt_task(doc) if doc else None


def _enrich_mt_task(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    # camelCase aliases for frontend
    doc["propId"] = doc.get("prop_id", 0)
    doc["roomId"] = doc.get("room_id", "")
    doc["roomLabel"] = doc.get("room_label", "")
    doc["roomTypeId"] = doc.get("room_type_id", "")
    doc["roomNumber"] = doc.get("room_number", "")
    doc["taskType"] = doc.get("task_type", "")
    doc["scheduledDate"] = doc.get("scheduled_date", "")
    doc["autoBlock"] = doc.get("auto_block", False)
    for f in ("created_at", "completed_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    doc["createdAt"] = doc.get("created_at")
    doc["completedAt"] = doc.get("completed_at")
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
