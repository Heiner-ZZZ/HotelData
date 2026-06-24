from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId

from src.database.connection import get_database

from .collections import (
    ROOM_STATUS_COLLECTION,
    HOUSEKEEPING_COLLECTION,
    MAINTENANCE_COLLECTION,
    CHARGES_COLLECTION,
)
from ..schemas import (
    AdditionalChargeCreate,
    HousekeepingTaskCreate,
    MaintenanceTaskCreate,
    RoomStatusLogCreate,
    now_iso,
)

# ═══════════════════════════════════════════════
# Room Status (CU-O30, CU-O31, CU-O32)
# ═══════════════════════════════════════════════


def upsert_room_status(payload: RoomStatusLogCreate) -> dict[str, Any]:
    """Create or update a room's status log entry."""
    db = get_database()
    now = now_iso()
    doc = {
        "prop_id": payload.prop_id,
        "room_type_id": payload.room_type_id,
        "room_label": payload.room_label,
        "status": payload.status,
        "note": payload.note,
        "updated_at": now,
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
    """List room statuses with optional filtering."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter

    total = db[ROOM_STATUS_COLLECTION].count_documents(query)
    cursor = (
        db[ROOM_STATUS_COLLECTION]
        .find(query)
        .sort("room_label", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_room_status(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_room_status(record_id: str) -> dict[str, Any] | None:
    """Get a single room status record."""
    db = get_database()
    doc = db[ROOM_STATUS_COLLECTION].find_one({"_id": ObjectId(record_id)})
    return _enrich_room_status(doc) if doc else None


def update_room_status_bulk(prop_id: int, room_labels: list[str], new_status: str, note: str = "") -> int:
    """Update status for multiple rooms at once (e.g. mark all as cleaned)."""
    db = get_database()
    now = now_iso()
    result = db[ROOM_STATUS_COLLECTION].update_many(
        {"prop_id": prop_id, "room_label": {"$in": room_labels}},
        {"$set": {"status": new_status, "note": note, "updated_at": now}},
    )
    return result.modified_count


# ═══════════════════════════════════════════════
# Housekeeping Tasks (CU-O39, CU-T14)
# ═══════════════════════════════════════════════


def create_housekeeping_task(payload: HousekeepingTaskCreate) -> dict[str, Any]:
    """Create a new housekeeping task."""
    db = get_database()
    now = now_iso()
    doc = {
        "prop_id": payload.prop_id,
        "room_label": payload.room_label,
        "task_type": payload.task_type,
        "status": "pending",
        "assigned_to": payload.assigned_to,
        "priority": payload.priority,
        "note": payload.note,
        "created_at": now,
        "completed_at": None,
    }
    result = db[HOUSEKEEPING_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_hk_task(doc)


def list_housekeeping_tasks(
    prop_id: int | None = None,
    status_filter: str | None = None,
    assigned_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List housekeeping tasks with filters."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    if assigned_to:
        query["assigned_to"] = assigned_to

    total = db[HOUSEKEEPING_COLLECTION].count_documents(query)
    cursor = (
        db[HOUSEKEEPING_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_hk_task(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def complete_housekeeping_task(task_id: str, note: str = "") -> dict[str, Any] | None:
    """Mark a housekeeping task as completed."""
    db = get_database()
    now = now_iso()
    update = {"$set": {"status": "completed", "completed_at": now}}
    if note:
        update["$set"]["note"] = note
    doc = db[HOUSEKEEPING_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": "pending"},
        update,
        return_document=True,
    )
    return _enrich_hk_task(doc) if doc else None


# ═══════════════════════════════════════════════
# Maintenance (CU-O40, CU-T15)
# ═══════════════════════════════════════════════


def create_maintenance_task(payload: MaintenanceTaskCreate) -> dict[str, Any]:
    """Create a new maintenance task."""
    db = get_database()
    now = now_iso()
    doc = {
        "prop_id": payload.prop_id,
        "room_label": payload.room_label,
        "task_type": payload.task_type,
        "title": payload.title,
        "description": payload.description,
        "status": "scheduled",
        "priority": payload.priority,
        "scheduled_date": payload.scheduled_date,
        "created_at": now,
        "completed_at": None,
    }
    result = db[MAINTENANCE_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_mt_task(doc)


def list_maintenance_tasks(
    prop_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List maintenance tasks with filters."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter

    total = db[MAINTENANCE_COLLECTION].count_documents(query)
    cursor = (
        db[MAINTENANCE_COLLECTION]
        .find(query)
        .sort("scheduled_date", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_mt_task(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def complete_maintenance_task(task_id: str, note: str = "") -> dict[str, Any] | None:
    """Mark a maintenance task as completed."""
    db = get_database()
    now = now_iso()
    update = {"$set": {"status": "completed", "completed_at": now}}
    if note:
        update["$set"]["note"] = note
    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$in": ["scheduled", "in_progress"]}},
        update,
        return_document=True,
    )
    return _enrich_mt_task(doc) if doc else None


# ═══════════════════════════════════════════════
# Additional Charges (CU-O34)
# ═══════════════════════════════════════════════


def create_additional_charge(payload: AdditionalChargeCreate) -> dict[str, Any] | None:
    """Register an additional charge against a booking."""
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        return None
    now = now_iso()
    doc = {
        "booking_id": payload.booking_id,
        "prop_id": payload.prop_id,
        "concept": payload.concept,
        "amount": round(payload.amount, 2),
        "quantity": max(1, payload.quantity),
        "total": round(payload.amount * max(1, payload.quantity), 2),
        "note": payload.note,
        "created_at": now,
    }
    result = db[CHARGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_charge(doc)


def list_additional_charges(
    booking_id: str | None = None,
    prop_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List additional charges."""
    db = get_database()
    query: dict[str, Any] = {}
    if booking_id:
        query["booking_id"] = booking_id
    if prop_id:
        query["prop_id"] = prop_id

    total = db[CHARGES_COLLECTION].count_documents(query)
    cursor = (
        db[CHARGES_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_charge(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


# ═══════════════════════════════════════════════
# Dashboard / Efficiency (CU-E09)
# ═══════════════════════════════════════════════


def get_housekeeping_dashboard(prop_id: int | None = None) -> dict[str, Any]:
    """Return aggregated KPIs for housekeeping efficiency monitoring."""
    db = get_database()
    match: dict[str, Any] = {}
    if prop_id:
        match["prop_id"] = prop_id

    # Room status counts
    pipeline_status = [
        {"$match": match},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_counts = {r["_id"]: r["count"] for r in db[ROOM_STATUS_COLLECTION].aggregate(pipeline_status)}

    # Pending housekeeping tasks
    pending_hk = db[HOUSEKEEPING_COLLECTION].count_documents({**match, "status": "pending"})

    # Completed today
    today = now_iso()[:10]
    completed_today_pipeline = [
        {"$match": {**match, "completed_at": {"$regex": f"^{today}"}}},
        {"$count": "total"},
    ]
    completed_today = 0
    result = list(db[HOUSEKEEPING_COLLECTION].aggregate(completed_today_pipeline))
    if result:
        completed_today = result[0]["total"]

    # Upcoming maintenance
    upcoming_mt = db[MAINTENANCE_COLLECTION].count_documents({
        **match,
        "status": {"$in": ["scheduled", "in_progress"]},
    })

    # Pending charges today
    pending_charges = db[CHARGES_COLLECTION].count_documents(match)

    total_rooms = status_counts.get("available", 0) + status_counts.get("occupied", 0) + status_counts.get("cleaning", 0)
    occupied = status_counts.get("occupied", 0)

    return {
        "total_rooms": total_rooms,
        "occupied": occupied,
        "occupancy_rate": round((occupied / total_rooms) * 100, 1) if total_rooms else 0,
        "room_statuses": status_counts,
        "pending_housekeeping_tasks": pending_hk,
        "completed_today": completed_today,
        "upcoming_maintenance": upcoming_mt,
        "pending_charges": pending_charges,
    }


# ═══════════════════════════════════════════════
# Enrichment helpers
# ═══════════════════════════════════════════════


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


def _enrich_hk_task(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "completed_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    return doc


def _enrich_mt_task(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "completed_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    return doc


def _enrich_charge(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at",):
        if f in doc:
            doc[f] = _fmt(doc[f])
    return doc
