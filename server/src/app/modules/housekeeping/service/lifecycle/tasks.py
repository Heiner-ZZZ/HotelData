"""Housekeeping task operations."""

from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from ..collections import HOUSEKEEPING_COLLECTION
from ...schemas import HousekeepingTaskCreate, now_iso


def create_housekeeping_task(payload: HousekeepingTaskCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()
    doc = {
        "prop_id": payload.prop_id, "room_label": payload.room_label,
        "task_type": payload.task_type, "status": "pending",
        "assigned_to": payload.assigned_to, "priority": payload.priority,
        "note": payload.note, "created_at": now, "completed_at": None,
    }
    result = db[HOUSEKEEPING_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_hk_task(doc)


def list_housekeeping_tasks(
    prop_id: int | None = None, status_filter: str | None = None,
    assigned_to: str | None = None, page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {}
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
        {"_id": ObjectId(task_id), "status": "pending"}, update, return_document=True,
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
