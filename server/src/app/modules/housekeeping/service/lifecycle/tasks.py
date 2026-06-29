"""Housekeeping task operations."""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database
from src.app.modules.partner.services.audit import register_action
from ..collections import HOUSEKEEPING_COLLECTION
from ...schemas import HousekeepingTaskCreate, now_iso

logger = logging.getLogger(__name__)


def create_housekeeping_task(payload: HousekeepingTaskCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()
    status = payload.status or "pending"
    completed_at = now if status == "completed" else None
    doc = {
        "prop_id": payload.prop_id,
        "room_label": payload.room_label,
        "task_type": payload.task_type,
        "status": status,
        "assigned_to": payload.assigned_to,
        "priority": payload.priority,
        "note": payload.note,
        "scheduled_date": payload.scheduled_date or "",
        "created_at": now,
        "completed_at": completed_at,
    }
    result = db[HOUSEKEEPING_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_hk_task(doc)


def list_housekeeping_tasks(
    prop_id: int | None = None, status_filter: str | None = None,
    assigned_to: str | None = None, page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {"status": {"$ne": "deleted"}}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    if assigned_to:
        query["assigned_to"] = assigned_to
    total = db[HOUSEKEEPING_COLLECTION].count_documents(query)
    cursor = db[HOUSEKEEPING_COLLECTION].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_hk_task(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def complete_housekeeping_task(task_id: str, note: str = "") -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    update = {"$set": {"status": "completed", "completed_at": now}}
    if note:
        update["$set"]["note"] = note
    doc = db[HOUSEKEEPING_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$in": ["pending", "inspection"]}}, update, return_document=True,
    )

    # ── Auto-transition room status to 'clean' on task completion ──
    if doc:
        try:
            prop_id = doc.get("prop_id")
            room_label = doc.get("room_label", "")
            if prop_id and room_label:
                from ..collections import ROOM_STATUS_COLLECTION
                db[ROOM_STATUS_COLLECTION].update_one(
                    {"prop_id": prop_id, "room_label": room_label},
                    {
                        "$set": {
                            "status": "clean",
                            "note": f"Limpieza completada — tarea {task_id}",
                            "updated_at": now,
                        },
                        "$setOnInsert": {"created_at": now},
                    },
                    upsert=True,
                )
                logger.info(
                    "Room %s (prop %s) auto-transitioned to 'clean' after task %s completed",
                    room_label, prop_id, task_id,
                )
        except Exception:
            logger.exception(
                "Failed to auto-transition room status to 'clean' for task %s", task_id
            )

    return _enrich_hk_task(doc) if doc else None


def update_housekeeping_task(task_id: str, payload: HousekeepingTaskCreate) -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()

    # Fetch task before update to detect status transitions
    old_task = db[HOUSEKEEPING_COLLECTION].find_one(
        {"_id": ObjectId(task_id)},
        {"_id": 0, "status": 1, "task_type": 1, "room_label": 1, "prop_id": 1},
    )

    status = payload.status or "pending"
    old_status = (old_task or {}).get("status", "")

    set_data = {
        "room_label": payload.room_label,
        "task_type": payload.task_type,
        "assigned_to": payload.assigned_to or "",
        "priority": payload.priority,
        "note": payload.note or "",
        "scheduled_date": payload.scheduled_date or "",
        "status": status,
        "updated_at": now,
    }
    if status == "completed":
        set_data["completed_at"] = now
    else:
        set_data["completed_at"] = None

    doc = db[HOUSEKEEPING_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id)},
        {"$set": set_data},
        return_document=ReturnDocument.AFTER,
    )

    if doc and status == "inspection" and old_status != "inspection":
        task_type_name = payload.task_type or old_task.get("task_type", "")
        room_label = payload.room_label or old_task.get("room_label", "")
        prop_id = int(old_task.get("prop_id", 0) or 0)

        # ── Audit log ──
        try:
            register_action(
                prop_id=prop_id,
                entity_type="housekeeping_task",
                entity_id=task_id,
                action="update",
                summary=f"Tarea de limpieza enviada a inspección — Hab. {room_label} ({task_type_name})",
                changed_by=payload.assigned_to or "system",
                metadata={
                    "room_label": room_label,
                    "task_type": task_type_name,
                    "new_status": "inspection",
                    "old_status": old_status,
                },
            )
        except Exception:
            logger.exception("Failed to register audit action for inspection task %s", task_id)

        # ── Notification log ──
        try:
            notification_doc = {
                "notification_type": "housekeeping_inspection",
                "entity_type": "housekeeping_task",
                "entity_id": task_id,
                "prop_id": prop_id,
                "recipient_email": "",  # broadcast to staff
                "subject": f"Inspección requerida — Hab. {room_label}",
                "message": (
                    f"La tarea de limpieza ({task_type_name}) para la habitación {room_label} "
                    f"ha sido marcada como lista para inspección."
                ),
                "status": "pending",
                "created_at": now,
                "metadata": {
                    "room_label": room_label,
                    "task_type": task_type_name,
                    "old_status": old_status,
                    "changed_by": payload.assigned_to or "system",
                },
            }
            db.notification_log.insert_one(notification_doc)
        except Exception:
            logger.exception("Failed to insert notification for inspection task %s", task_id)

    return _enrich_hk_task(doc) if doc else None


def delete_housekeeping_task(task_id: str) -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    doc = db[HOUSEKEEPING_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$ne": "deleted"}},
        {"$set": {"status": "deleted", "deleted_at": now}},
        return_document=True,
    )
    return _enrich_hk_task(doc) if doc else None


def _enrich_hk_task(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "completed_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
