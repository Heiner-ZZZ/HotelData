"""Housekeeping dashboard KPIs with floor-level aggregation.

Returns:
- KPI cards: occupied, clean, pending, in cleaning, out of service, etc.
- Floor-by-floor room grid with status colors
- Supervisor-level metrics
"""

from __future__ import annotations

from typing import Any

from src.database.connection import get_database
from ..collections import (
    ROOM_STATUS_COLLECTION, HOUSEKEEPING_COLLECTION,
    MAINTENANCE_COLLECTION, CHARGES_COLLECTION,
)
from ...schemas import now_iso, ROOM_STATUSES, ROOM_STATUS_COLORS

# Label for rooms whose hotel_rooms record has no floor set
FLOOR_UNKNOWN = "Sin asignar"


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
        doc["roomNumber"] = doc.get("room_label", "")
        doc["propId"] = doc.get("prop_id", 0)
        doc["hotelRoomId"] = doc.get("hotel_room_id", "")
        doc["statusLabel"] = ROOM_STATUSES.get(doc.get("status", ""), doc.get("status", ""))
        doc["statusColor"] = ROOM_STATUS_COLORS.get(doc.get("status", ""), "#6f797d")
        rooms_list.append(doc)

        # Read floor; fall back to room_number-derived floor (e.g. '301' → '3')
        floor = doc.get("floor")
        if floor is not None and str(floor):
            floor = str(floor)
        else:
            rn = str(doc.get("roomNumber", ""))
            if rn.isdigit():
                floor = str(int(rn) // 100)
            else:
                floor = FLOOR_UNKNOWN
        if floor not in floors_map:
            floors_map[floor] = []
        floors_map[floor].append(doc)

    # Sort floors: numeric first, then "Sin piso" last
    def _floor_sort_key(f: str) -> tuple:
        if f == FLOOR_UNKNOWN:
            return (1, 0)  # after all numeric floors
        try:
            return (0, int(f))
        except ValueError:
            return (0, f)

    sorted_floors = sorted(floors_map.keys(), key=_floor_sort_key)

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


def get_weekly_calendar(
    prop_id: int,
    week_start: str,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    """Return a weekly calendar grid: rooms × days with scheduled tasks.

    Returns:
    {
      "week_days": ["2026-06-22", "2026-06-23", ...],  // 7 days
      "calendar": {
        "1201": {
          "room_label": "1201",
          "status": "vacant_dirty",
          "status_color": "#92400e",
          "days": {
            "2026-06-22": [ { task fields... } ],
            "2026-06-23": [],
            ...
          }
        },
        ...
      },
      "staff": ["María García", "Juan Pérez", ...],  // unique assigned_to
      "summary": { "total_tasks": 42, "by_status": {...} }
    }
    """
    db = get_database()

    # Calculate end of week (7 days from week_start)
    try:
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=6)
        week_end = end_dt.strftime("%Y-%m-%d")
    except ValueError:
        week_end = week_start  # fallback

    # Build week days array
    week_days: list[str] = []
    try:
        cur = start_dt
        for _ in range(7):
            week_days.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
    except Exception:
        week_days = [week_start]

    # 1. Fetch all rooms for this property
    rooms_query: dict[str, Any] = {"prop_id": prop_id}
    rooms_list = list(db[ROOM_STATUS_COLLECTION].find(rooms_query).sort("room_label", 1).limit(500))

    # 2. Fetch tasks scheduled within the week
    task_query: dict[str, Any] = {
        "prop_id": prop_id,
        "status": {"$ne": "deleted"},
        "scheduled_date": {"$gte": week_start, "$lte": week_end},
    }
    if assigned_to:
        task_query["assigned_to"] = assigned_to

    tasks_cursor = db[HOUSEKEEPING_COLLECTION].find(task_query).sort("scheduled_date", 1)

    # 3. Fetch maintenance events within the week
    maint_query: dict[str, Any] = {
        "prop_id": prop_id,
        "status": {"$in": ["scheduled", "in_progress"]},
        "scheduled_date": {"$gte": week_start, "$lte": week_end},
    }
    maint_cursor = db[MAINTENANCE_COLLECTION].find(maint_query).sort("scheduled_date", 1)

    # 4. Build calendar grid: room_label → { days: { date → [tasks] } }
    calendar: dict[str, Any] = {}
    for room in rooms_list:
        label = room.get("room_label", "")
        if not label:
            continue
        status = room.get("status", "")
        days_map: dict[str, list[dict[str, Any]]] = {d: [] for d in week_days}
        calendar[label] = {
            "room_id": room.get("hotel_room_id", ""),
            "room_label": label,
            "room_number": room.get("room_label", ""),
            "status": status,
            "status_color": ROOM_STATUS_COLORS.get(status, "#6f797d"),
            "status_label": ROOM_STATUSES.get(status, status),
            "days": days_map,
        }

    # Place tasks into calendar
    staff_set: set[str] = set()
    task_count_by_status: dict[str, int] = {}
    total_tasks = 0

    for doc in tasks_cursor:
        sid = str(doc.pop("_id"))
        sched = doc.get("scheduled_date", "")
        rl = doc.get("room_label", "")
        if not rl or sched not in week_days:
            continue

        assigned = doc.get("assigned_to", "")
        if assigned:
            staff_set.add(assigned)

        task_item = {
            "id": sid,
            "task_type": doc.get("task_type", "cleaning"),
            "status": doc.get("status", "pending"),
            "assigned_to": assigned,
            "priority": doc.get("priority", "normal"),
            "note": doc.get("note", ""),
            "scheduled_date": sched[:10] if sched else "",
        }
        total_tasks += 1
        st = task_item["status"]
        task_count_by_status[st] = task_count_by_status.get(st, 0) + 1

        if rl in calendar and sched in calendar[rl]["days"]:
            calendar[rl]["days"][sched].append(task_item)

    # Place maintenance events into calendar
    for doc in maint_cursor:
        sid = str(doc.pop("_id"))
        sched = doc.get("scheduled_date", "")
        rl = doc.get("room_label", "")
        if not rl or sched not in week_days:
            continue

        maint_item = {
            "id": sid,
            "task_type": "maintenance",
            "status": doc.get("status", "scheduled"),
            "assigned_to": doc.get("assigned_to", ""),
            "priority": doc.get("priority", "normal"),
            "title": doc.get("title", ""),
            "description": doc.get("description", ""),
            "scheduled_date": sched[:10] if sched else "",
        }
        total_tasks += 1
        mt_st = "maintenance"
        task_count_by_status[mt_st] = task_count_by_status.get(mt_st, 0) + 1

        if rl in calendar and sched in calendar[rl]["days"]:
            calendar[rl]["days"][sched].append(maint_item)

    # Sort rooms naturally
    def _natural_key(label: str) -> tuple:
        digits = "".join(c for c in label if c.isdigit())
        return (len(digits), int(digits) if digits else 0, label)

    sorted_rooms = sorted(calendar.values(), key=lambda r: _natural_key(r["room_label"]))
    sorted_calendar: dict[str, Any] = {}
    for r in sorted_rooms:
        sorted_calendar[r["room_label"]] = r

    # Collect unique staff list
    staff_list = sorted(staff_set)

    return {
        "week_days": week_days,
        "week_start": week_start,
        "week_end": week_end,
        "calendar": sorted_calendar,
        "staff": staff_list,
        "summary": {
            "total_tasks": total_tasks,
            "by_status": task_count_by_status,
        },
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
