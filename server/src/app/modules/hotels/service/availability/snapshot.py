"""Per-room next-7-days availability snapshot for hotel detail without dates."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.app.core.timezone import local_today
from src.database.connection import get_database


def _valid_rate_for_room_on_date(prop_id: int, room_type_id: str, date_str: str) -> float | None:
    """Return min valid rate_amount for this room_type on this date, or None.

    Valid = hotel_rate_calendar row with is_closed != True, whose rate_plan
    is_active != False, tied to this room_type (applicable_room_types contains it
    or room_type_id == it), and rate_amount >= base_rate.
    """
    db = get_database()
    # Find calendar rows for this prop/date that are not closed
    rows = list(db.hotel_rate_calendar.find(
        {"prop_id": prop_id, "date": date_str, "is_closed": {"$ne": True}},
        {"_id": 0, "rate_plan_id": 1, "rate_amount": 1},
    ))
    if not rows:
        return None
    # For each row, check its rate_plan is valid for this room_type
    valid_rates: list[float] = []
    for row in rows:
        plan_id = row.get("rate_plan_id")
        amount = row.get("rate_amount")
        if plan_id is None or amount is None:
            continue
        plan = db.rate_plans.find_one(
            {
                "rate_plan_id": plan_id,
                "prop_id": prop_id,
                "is_active": {"$ne": False},
                "$or": [
                    {"applicable_room_types": room_type_id},
                    {"room_type_id": room_type_id},
                ],
            },
            {"_id": 0, "base_rate": 1},
        )
        # Also handle case where applicable_room_types contains the room_type
        # via array contains: the query above with applicable_room_types: room_type_id works for array contains
        # But if not found, try alternative: applicable_room_types contains string
        if not plan:
            # Fallback: check if plan has applicable_room_types array containing room_type_id via direct fetch
            plan2 = db.rate_plans.find_one({"rate_plan_id": plan_id, "is_active": {"$ne": False}}, {"_id": 0, "base_rate": 1, "applicable_room_types": 1, "room_type_id": 1})
            if not plan2:
                continue
            app_types = plan2.get("applicable_room_types") or []
            rt_id = plan2.get("room_type_id") or ""
            if room_type_id not in app_types and rt_id != room_type_id:
                continue
            plan = plan2
        base = plan.get("base_rate")
        if base is not None and float(amount) < float(base):
            continue
        try:
            valid_rates.append(float(amount))
        except (TypeError, ValueError):
            continue
    if not valid_rates:
        return None
    return round(min(valid_rates), 2)


def get_room_availability_snapshot(
    prop_id: int,
    start_date: str | None = None,
    days: int = 7,
) -> dict[str, Any]:
    """Public snapshot: per room_type next N days availability.

    Returns dict with prop_id, start_date, end_date, rooms: [{room_type_id, name, availability: [{date, is_available, available_rooms, min_rate, min_rate_label}]}]
    If hotel has no room_types, rooms is empty but still 200 (guest can see hotel exists).
    """
    db = get_database()
    # Validate days
    days = max(1, min(days, 14))
    # Determine start_date
    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except (ValueError, TypeError):
            start = date.fromisoformat(local_today())
    else:
        start = date.fromisoformat(local_today())
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    end_date = dates[-1]

    # Check hotel exists? If not in dim_hotels and no room_types, still return empty but not 404 for snapshot? For consistency with detail, if hotel is not found at all, return None to trigger 404.
    # We consider hotel exists if dim_hotels has it or room_types has it
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0, "prop_id": 1})
    room_types = list(db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1, "is_active": 1, "base_capacity": 1, "max_adults": 1, "max_children": 1}).sort([("is_active", -1), ("name", 1)]))
    if not hotel and not room_types:
        return None  # type: ignore[return-value]

    rooms: list[dict[str, Any]] = []
    for rt in room_types:
        rt_id = str(rt.get("room_type_id") or "")
        if not rt_id:
            continue
        name = str(rt.get("name") or rt_id)
        availability: list[dict[str, Any]] = []
        for d in dates:
            inv = db.room_inventory_calendar.find_one(
                {"prop_id": prop_id, "room_type_id": rt_id, "date": d},
                {"_id": 0, "available_rooms": 1, "total_rooms": 1},
            )
            available_rooms = int(inv.get("available_rooms") or 0) if inv else 0
            min_rate = _valid_rate_for_room_on_date(prop_id, rt_id, d)
            # is_available requires both inventory >=1 and valid rate
            is_available = available_rooms >= 1 and min_rate is not None
            # If not available due to missing inventory, min_rate is still returned if exists for info, but is_available false
            # For is_closed or orphan, min_rate is None
            availability.append({
                "date": d,
                "is_available": is_available,
                "available_rooms": available_rooms if is_available else 0,
                "min_rate": min_rate if is_available else None,
                "min_rate_label": f"${min_rate:.2f}" if is_available and min_rate is not None else None,
            })
        rooms.append({
            "room_type_id": rt_id,
            "name": name,
            "is_active": bool(rt.get("is_active", True)),
            "base_capacity": rt.get("base_capacity"),
            "max_adults": rt.get("max_adults"),
            "max_children": rt.get("max_children"),
            "availability": availability,
        })

    return {
        "prop_id": prop_id,
        "start_date": dates[0],
        "end_date": end_date,
        "rooms": rooms,
    }
