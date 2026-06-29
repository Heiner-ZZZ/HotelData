"""Housekeeping dashboard KPIs with floor-level aggregation.

Returns:
- KPI cards: occupied, clean, pending, in cleaning, out of service, etc.
- Floor-by-floor room grid with status colors
- Supervisor-level metrics
"""

from __future__ import annotations

import re
from typing import Any

from src.database.connection import get_database
from ..collections import (
    ROOM_STATUS_COLLECTION, HOUSEKEEPING_COLLECTION,
    MAINTENANCE_COLLECTION, CHARGES_COLLECTION,
)
from ...schemas import now_iso, ROOM_STATUSES, ROOM_STATUS_COLORS


def _extract_floor(room_label: str) -> str:
    """Extract floor number from room label (e.g. '1201' → '1', '305' → '3')."""
    digits = re.sub(r'\D', '', room_label)
    if len(digits) >= 3:
        return digits[0]
    if len(digits) >= 2:
        return digits[0]
    return "0"


def get_housekeeping_dashboard(prop_id: int | None = None) -> dict[str, Any]:
    db = get_database()
    match: dict[str, Any] = {}
    if prop_id:
        match["prop_id"] = prop_id

    # ── Status counts ──
    pipeline = [{"$match": match}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    raw_counts = {r["_id"]: r["count"] for r in db[ROOM_STATUS_COLLECTION].aggregate(pipeline)}

    # Normalize all known statuses to 0
    status_counts: dict[str, int] = {s: 0 for s in ROOM_STATUSES}
    status_counts.update(raw_counts)

    total_rooms = sum(status_counts.values())
    occupied = status_counts.get("occupied_clean", 0) + status_counts.get("occupied_dirty", 0)
    vacant = status_counts.get("vacant_clean", 0) + status_counts.get("vacant_dirty", 0)
    in_cleaning = status_counts.get("cleaning_in_progress", 0)
    completed = status_counts.get("cleaning_completed", 0)
    inspected = status_counts.get("inspected", 0)
    out_of_service = status_counts.get("out_of_service", 0)
    out_of_order = status_counts.get("out_of_order", 0)
    maintenance_req = status_counts.get("maintenance_requested", 0)
    pending_rooms = status_counts.get("vacant_dirty", 0) + status_counts.get("occupied_dirty", 0)
    clean_rooms = status_counts.get("vacant_clean", 0) + status_counts.get("occupied_clean", 0)

    # ── Task metrics ──
    pending_hk = db[HOUSEKEEPING_COLLECTION].count_documents({**match, "status": "pending"})

    today = now_iso()[:10]
    completed_today = 0
    result = list(db[HOUSEKEEPING_COLLECTION].aggregate([
        {"$match": {**match, "completed_at": {"$regex": f"^{today}"}}},
        {"$count": "total"},
    ]))
    if result:
        completed_today = result[0]["total"]

    # ── Maintenance metrics ──
    upcoming_mt = db[MAINTENANCE_COLLECTION].count_documents({
        **match, "status": {"$in": ["scheduled", "in_progress"]},
    })
    total_mt_completed = db[MAINTENANCE_COLLECTION].count_documents({
        **match, "status": "completed",
    })
    on_time_mt = db[MAINTENANCE_COLLECTION].count_documents({
        **match, "status": "completed",
        "$expr": {
            "$and": [
                {"$ne": ["$completed_at", None]},
                {"$ne": ["$scheduled_date", ""]},
                {"$lte": ["$completed_at", {"$concat": ["$scheduled_date", "T23:59:59"]}]},
            ]
        },
    })
    mt_compliance_pct = round((on_time_mt / total_mt_completed) * 100, 1) if total_mt_completed else 0

    # ── Floor-by-floor aggregation ──
    rooms_cursor = db[ROOM_STATUS_COLLECTION].find(match).sort("room_label", 1).limit(500)
    rooms_list: list[dict[str, Any]] = []
    floors_map: dict[str, list[dict[str, Any]]] = {}

    for doc in rooms_cursor:
        doc["id"] = str(doc.pop("_id"))
        for f in ("created_at", "updated_at", "cleaning_started_at", "cleaning_completed_at"):
            if f in doc and hasattr(doc[f], "isoformat"):
                doc[f] = doc[f].isoformat()
        doc["roomLabel"] = doc.get("room_label", "")
        doc["roomNumber"] = doc.get("room_number", "")
        doc["propId"] = doc.get("prop_id", 0)
        doc["hotelRoomId"] = doc.get("hotel_room_id", "")
        doc["statusLabel"] = ROOM_STATUSES.get(doc.get("status", ""), doc.get("status", ""))
        doc["statusColor"] = ROOM_STATUS_COLORS.get(doc.get("status", ""), "#6f797d")
        rooms_list.append(doc)

        floor = _extract_floor(doc.get("room_label", doc.get("roomNumber", "")))
        if floor not in floors_map:
            floors_map[floor] = []
        floors_map[floor].append(doc)

    # Sort floors naturally
    sorted_floors = sorted(floors_map.keys(), key=lambda f: int(f) if f.isdigit() else 999)

    floors: list[dict[str, Any]] = []
    for fl in sorted_floors:
        floor_rooms = floors_map[fl]
        # Count statuses per floor
        floor_counts: dict[str, int] = {}
        for r in floor_rooms:
            s = r.get("status", "")
            floor_counts[s] = floor_counts.get(s, 0) + 1
        floors.append({
            "floor": fl,
            "rooms": floor_rooms,
            "count": len(floor_rooms),
            "status_counts": floor_counts,
        })

    return {
        "total_rooms": total_rooms,
        "occupied": occupied,
        "vacant": vacant,
        "clean_rooms": clean_rooms,
        "pending_rooms": pending_rooms,
        "in_cleaning": in_cleaning,
        "cleaning_completed": completed,
        "inspected": inspected,
        "out_of_service": out_of_service,
        "out_of_order": out_of_order,
        "maintenance_requested": maintenance_req,
        "occupancy_rate": round((occupied / total_rooms) * 100, 1) if total_rooms else 0,
        "room_statuses": status_counts,
        "status_labels": ROOM_STATUSES,
        "status_colors": ROOM_STATUS_COLORS,
        "rooms": rooms_list,
        "floors": floors,
        "pending_housekeeping_tasks": pending_hk,
        "completed_today": completed_today,
        "upcoming_maintenance": upcoming_mt,
        "maintenance_compliance_pct": mt_compliance_pct,
        "total_maintenance_completed": total_mt_completed,
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
        maintenance_events.append(doc)

    # Pending housekeeping tasks
    hk_query = {**query, "status": {"$in": ["pending", "in_progress"]}}
    task_events = []
    for doc in db[HOUSEKEEPING_COLLECTION].find(hk_query).sort("created_at", -1).limit(100):
        doc["id"] = str(doc.pop("_id"))
        doc["event_type"] = "task"
        for f in ("created_at", "completed_at", "scheduled_date"):
            if f in doc and hasattr(doc[f], "isoformat"):
                doc[f] = doc[f].isoformat()
        task_events.append(doc)

    return maintenance_events + task_events
