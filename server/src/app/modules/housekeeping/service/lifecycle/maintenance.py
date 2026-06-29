"""Maintenance task operations."""

from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId

from pymongo import ReturnDocument

from src.database.connection import get_database
from ..collections import MAINTENANCE_COLLECTION
from ...schemas import MaintenanceTaskCreate, now_iso


def _auto_block_room(db: Any, prop_id: int, room_label: str, scheduled_date: str) -> None:
    """Mark the room as 'maintenance' in room_status_log and create blackout_date.

    RF-002: Bloquear disponibilidad durante mantenimiento.
    This ensures the room cannot be booked while under maintenance.
    """
    if not room_label:
        return
    # Update room status to 'maintenance'
    db.room_status_log.update_one(
        {"prop_id": prop_id, "room_label": room_label},
        {
            "$set": {"status": "maintenance_requested", "note": "Mantenimiento programado", "updated_at": now_iso()},
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


def _unblock_room(db: Any, prop_id: int, room_label: str, scheduled_date: str) -> None:
    """Restore room status to 'available' and remove blackout dates.

    Called when maintenance is completed or deleted.
    """
    if not room_label:
        return
    # Only restore if the room is still marked as maintenance
    current = db.room_status_log.find_one({"prop_id": prop_id, "room_label": room_label}, {"status": 1})
    if current and current.get("status") == "maintenance":
        # Restore to vacant_clean (the new housekeeping status)
        db.room_status_log.update_one(
            {"prop_id": prop_id, "room_label": room_label},
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
    status = payload.status or "scheduled"
    completed_at = now if status == "completed" else None
    doc = {
        "prop_id": payload.prop_id,
        "room_label": payload.room_label,
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
            _auto_block_room(db, payload.prop_id, payload.room_label, payload.scheduled_date)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to auto-block room for maintenance task")
    return _enrich_mt_task(doc)


def list_maintenance_tasks(
    prop_id: int | None = None, status_filter: str | None = None,
    page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {"status": {"$ne": "deleted"}}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
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
    # Fetch previous state to know if we need to unblock old room
    prev = db[MAINTENANCE_COLLECTION].find_one({"_id": ObjectId(task_id)})
    
    set_data = {
        "room_label": payload.room_label,
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
            _unblock_room(db, payload.prop_id, prev.get("room_label", ""), prev.get("scheduled_date", ""))
        
        # If new status is not completed and auto_block is True, block new room/date
        if status != "completed" and payload.auto_block and payload.room_label:
            _auto_block_room(db, payload.prop_id, payload.room_label, payload.scheduled_date)
            
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
            _unblock_room(db, doc.get("prop_id", 0), doc.get("room_label", ""), doc.get("scheduled_date", ""))
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
            _unblock_room(db, doc.get("prop_id", 0), doc.get("room_label", ""), doc.get("scheduled_date", ""))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to unblock room on maintenance deletion")
    return _enrich_mt_task(doc) if doc else None


def _enrich_mt_task(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "completed_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
