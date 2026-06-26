"""Housekeeping dashboard KPIs."""

from __future__ import annotations

from typing import Any

from src.database.connection import get_database
from ..collections import (
    ROOM_STATUS_COLLECTION, HOUSEKEEPING_COLLECTION,
    MAINTENANCE_COLLECTION, CHARGES_COLLECTION,
)
from ...schemas import now_iso


def get_housekeeping_dashboard(prop_id: int | None = None) -> dict[str, Any]:
    db = get_database()
    match: dict[str, Any] = {}
    if prop_id:
        match["prop_id"] = prop_id

    status_counts = {r["_id"]: r["count"] for r in db[ROOM_STATUS_COLLECTION].aggregate([
        {"$match": match}, {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ])}

    pending_hk = db[HOUSEKEEPING_COLLECTION].count_documents({**match, "status": "pending"})

    today = now_iso()[:10]
    completed_today = 0
    result = list(db[HOUSEKEEPING_COLLECTION].aggregate([
        {"$match": {**match, "completed_at": {"$regex": f"^{today}"}}},
        {"$count": "total"},
    ]))
    if result:
        completed_today = result[0]["total"]

    upcoming_mt = db[MAINTENANCE_COLLECTION].count_documents({
        **match, "status": {"$in": ["scheduled", "in_progress"]},
    })

    total_rooms = status_counts.get("available", 0) + status_counts.get("occupied", 0) + status_counts.get("cleaning", 0)
    occupied = status_counts.get("occupied", 0)

    return {
        "total_rooms": total_rooms, "occupied": occupied,
        "occupancy_rate": round((occupied / total_rooms) * 100, 1) if total_rooms else 0,
        "room_statuses": status_counts,
        "pending_housekeeping_tasks": pending_hk,
        "completed_today": completed_today,
        "upcoming_maintenance": upcoming_mt,
        "pending_charges": db[CHARGES_COLLECTION].count_documents(match),
    }


def list_upcoming_events(prop_id: int | None = None, days: int = 30) -> list[dict[str, Any]]:
    """Return upcoming housekeeping tasks and maintenance events for calendar display."""
    db = get_database()
    today = now_iso()[:10]

    query: dict[str, Any] = {"status": {"$ne": "deleted"}}
    if prop_id:
        query["prop_id"] = prop_id

    # Upcoming maintenance tasks
    mt_query = {**query, "status": {"$in": ["scheduled", "in_progress"]}, "scheduled_date": {"$gte": today}}
    maintenance_events = []
    for doc in db[MAINTENANCE_COLLECTION].find(mt_query).sort("scheduled_date", 1).limit(100):
        doc["id"] = str(doc.pop("_id"))
        doc["event_type"] = "maintenance"
        for f in ("created_at", "completed_at", "scheduled_date"):
            if f in doc and hasattr(doc[f], "isoformat"):
                doc[f] = doc[f].isoformat()
            elif f in doc:
                doc[f] = str(doc[f]) if doc[f] else None
        maintenance_events.append(doc)

    # Pending housekeeping tasks (with scheduled_date if available)
    hk_query = {**query, "status": "pending"}
    task_events = []
    for doc in db[HOUSEKEEPING_COLLECTION].find(hk_query).sort("created_at", -1).limit(100):
        doc["id"] = str(doc.pop("_id"))
        doc["event_type"] = "task"
        for f in ("created_at", "completed_at", "scheduled_date"):
            if f in doc and hasattr(doc[f], "isoformat"):
                doc[f] = doc[f].isoformat()
            elif f in doc:
                doc[f] = str(doc[f]) if doc[f] else None
        task_events.append(doc)

    return maintenance_events + task_events
