"""Availability check logic for booking creation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.database.connection import get_database


def _check_availability(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str = "",
) -> str | None:
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "Invalid date format; expected YYYY-MM-DD"

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]

    if not dates:
        dates = [check_in_date]

    requested_nights = len(dates)

    # ── min_stay baseline from hotel_policies ──
    policy_filter: dict[str, object] = {"prop_id": prop_id}
    if room_type_id:
        policy_filter["room_type_id"] = room_type_id
    else:
        policy_filter["room_type_id"] = {"$in": ["", None]}
    hotel_policy = db.hotel_policies.find_one(
        policy_filter,
        {"_id": 0, "min_stay": 1, "max_stay": 1},
    )
    if not hotel_policy:
        hotel_policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}},
            {"_id": 0, "min_stay": 1, "max_stay": 1},
        )
    policy_min_stay = hotel_policy.get("min_stay") if hotel_policy else None
    policy_max_stay = hotel_policy.get("max_stay") if hotel_policy else None

    if policy_min_stay is not None and requested_nights < policy_min_stay:
        return (
            f"La estancia mínima para esta propiedad es de {policy_min_stay} noche(s). "
            f"Solicitaste {requested_nights} noche(s)."
        )
    if policy_max_stay is not None and requested_nights > policy_max_stay:
        return (
            f"La estancia máxima para esta propiedad es de {policy_max_stay} noche(s). "
            f"Solicitaste {requested_nights} noche(s)."
        )

    # ── min_stay / max_stay from hotel_rate_calendar ──
    if policy_min_stay is None:
        rate_match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}, "is_closed": {"$ne": True}}
        rate_records = list(
            db.hotel_rate_calendar.find(
                rate_match,
                {"_id": 0, "date": 1, "min_stay_nights": 1, "max_stay_nights": 1},
            )
        )
        if rate_records:
            max_min_stay = max((r.get("min_stay_nights") or 1 for r in rate_records), default=1)
            if max_min_stay > requested_nights:
                return f"La estancia mínima es de {max_min_stay} noche(s). Solicitaste {requested_nights} noche(s)."

            non_null_max_stay = [r.get("max_stay_nights") for r in rate_records if r.get("max_stay_nights") is not None]
            if non_null_max_stay:
                min_max_stay = min(non_null_max_stay)
                if min_max_stay < requested_nights:
                    return f"La estancia máxima es de {min_max_stay} noche(s). Solicitaste {requested_nights} noche(s)."

    # ── ROH check ──
    is_roh_booking = False
    if room_type_id:
        roh_check = db.room_types.find_one(
            {"room_type_id": room_type_id, "prop_id": prop_id},
            {"_id": 0, "is_roh": 1},
        )
        if roh_check and roh_check.get("is_roh", False):
            is_roh_booking = True

    # ── Inventory availability check ──
    if is_roh_booking:
        records = list(
            db.room_inventory_calendar.aggregate([
                {"$match": {"prop_id": prop_id, "date": {"$in": dates}, "is_roh": {"$ne": True}}},
                {"$group": {"_id": "$date", "total_available": {"$sum": "$available_rooms"}}},
                {"$sort": {"_id": 1}},
            ])
        )
        found_dates = {r["_id"]: r.get("total_available", 0) for r in records}
    else:
        match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}}
        if room_type_id:
            match["room_type_id"] = room_type_id

        records = list(
            db.room_inventory_calendar.find(match, {"_id": 0, "date": 1, "available_rooms": 1}).sort("date", 1)
        )
        found_dates = {r["date"]: r.get("available_rooms", 0) for r in records}

    for d in dates:
        avail = found_dates.get(d, 0)
        if avail < rooms:
            if d not in found_dates:
                return f"No inventory data for date {d}"
            return f"Only {avail} room(s) available on {d}, requested {rooms}"
    return None
