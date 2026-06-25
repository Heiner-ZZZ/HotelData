"""Helper functions for hotel availability search."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.database.connection import get_database


def _check_inventory_for_dates(
    prop_id: int, room_type_id: str, check_in: str, check_out: str, required_rooms: int,
) -> bool:
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return False
    nights = (end - start).days
    if nights < 1:
        return False
    dates_list = [(start + timedelta(days=i)).isoformat() for i in range(nights)]
    db = get_database()
    count = db.room_inventory_calendar.count_documents({
        "prop_id": prop_id, "room_type_id": room_type_id,
        "date": {"$in": dates_list}, "available_rooms": {"$gte": required_rooms},
    })
    return count == len(dates_list)


def _matching_room_types(prop_id: int, adults: int, children: int) -> list[dict[str, Any]]:
    db = get_database()
    return list(db.room_types.find({
        "prop_id": prop_id, "is_active": True,
        "max_adults": {"$gte": adults or 1},
        "max_children": {"$gte": children or 0},
    }, {"_id": 0}).sort([("base_capacity", 1)]))


def _hotel_min_rate_for_range(prop_id: int, check_in: str, check_out: str) -> float | None:
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return None
    nights = (end - start).days
    if nights < 1:
        return None
    dates_list = [(start + timedelta(days=i)).isoformat() for i in range(nights)]
    db = get_database()
    result = db.hotel_rate_calendar.aggregate([
        {"$match": {"prop_id": prop_id, "date": {"$in": dates_list}, "is_closed": {"$ne": True}}},
        {"$group": {"_id": None, "min_rate": {"$min": "$rate_amount"}}},
    ])
    row = next(result, None)
    return round(float(row["min_rate"]), 2) if row and row.get("min_rate") is not None else None


def _hotel_image_url(prop_id: int) -> str | None:
    db = get_database()
    image = db.hotel_images.find_one({"prop_id": prop_id}, {"_id": 0, "image_url": 1}, sort=[("_id", 1)])
    return image.get("image_url") if image else None


def _destination_display_name(dest: dict[str, Any], dest_id: int | str) -> str:
    return dest.get("display_name") or dest.get("name") or str(dest_id)


def _hotel_display_name(hotel: dict[str, Any], prop_id: int) -> str:
    return hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}"
