"""Helper functions for hotel availability search."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from src.database.connection import get_database


def _date_range(check_in: str, check_out: str) -> list[str] | None:
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return None
    nights = (end - start).days
    if nights < 1:
        return None
    return [(start + timedelta(days=i)).isoformat() for i in range(nights)]


def _check_inventory_for_dates(
    prop_id: int, room_type_id: str, check_in: str, check_out: str, required_rooms: int,
) -> bool:
    dates_list = _date_range(check_in, check_out)
    if not dates_list:
        return False
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


def _matching_room_types_for_properties(
    prop_ids: list[int], adults: int, children: int,
) -> dict[int, list[dict[str, Any]]]:
    """Load capacity-compatible room types for a page in one Mongo query."""
    if not prop_ids:
        return {}
    db = get_database()
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    cursor = db.room_types.find({
        "prop_id": {"$in": prop_ids},
        "is_active": True,
        "max_adults": {"$gte": adults or 1},
        "max_children": {"$gte": children or 0},
    }, {"_id": 0}).sort([("base_capacity", 1), ("room_type_id", 1)])
    for room_type in cursor:
        grouped[int(room_type["prop_id"])].append(room_type)
    return dict(grouped)


def _available_room_type_summaries_for_properties(
    prop_ids: list[int],
    adults: int,
    children: int,
    check_in: str,
    check_out: str,
    required_rooms: int,
) -> dict[int, dict[str, Any]]:
    """Return one available room-type summary per property.

    This is deliberately a database-side reduction. Search never materializes
    every compatible room type or physical room. Mongo filters capacity,
    verifies coverage for the requested dates, sorts by smallest capacity and
    returns only the first matching type for each property.
    """
    dates_list = _date_range(check_in, check_out)
    if not dates_list or not prop_ids:
        return {}

    db = get_database()
    pipeline: list[dict[str, Any]] = [
        {"$match": {
            "prop_id": {"$in": prop_ids},
            "is_active": True,
            "max_adults": {"$gte": adults or 1},
            "max_children": {"$gte": children or 0},
        }},
        {"$lookup": {
            "from": "room_inventory_calendar",
            "let": {"prop": "$prop_id", "room_type": "$room_type_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$prop_id", "$$prop"]},
                    {"$eq": ["$room_type_id", "$$room_type"]},
                    {"$in": ["$date", dates_list]},
                    {"$gte": ["$available_rooms", required_rooms]},
                ]}}},
                {"$group": {
                    "_id": None,
                    "covered_nights": {"$sum": 1},
                    "min_available": {"$min": "$available_rooms"},
                }},
            ],
            "as": "coverage",
        }},
        {"$match": {"$expr": {"$eq": [
            {"$ifNull": [{"$arrayElemAt": ["$coverage.covered_nights", 0]}, 0]},
            len(dates_list),
        ]}}},
        {"$sort": {"prop_id": 1, "base_capacity": 1, "room_type_id": 1}},
        {"$group": {"_id": "$prop_id", "room_type": {"$first": {
            "room_type_id": "$room_type_id",
            "name": "$name",
            "max_adults": "$max_adults",
            "max_children": "$max_children",
            "base_capacity": "$base_capacity",
            # Min available_rooms across the stay for this room type — the
            # "cuántas quedan a este precio" count on the search card.
            "min_available": {"$arrayElemAt": ["$coverage.min_available", 0]},
        }}}},
    ]
    return {
        int(row["_id"]): row["room_type"]
        for row in db.room_types.aggregate(pipeline)
        if row.get("_id") is not None and row.get("room_type")
    }


def _eligible_room_type_summaries(
    prop_ids: list[int] | None,
    adults: int,
    children: int,
    check_in: str,
    check_out: str,
    required_rooms: int,
) -> dict[int, dict[str, Any]]:
    """INVERTED availability reduction: one pass over room_inventory_calendar.

    Returns prop_id -> {room_type_id, name, max_adults, max_children,
    base_capacity, min_available} for the cheapest room type per property with
    FULL coverage of the stay (every night has available_rooms >= required)
    and capacity for the guests.

    This is the database-side reduction that replaces the search loop's
    per-batch $lookup scan. The inventory collection is typically orders of
    magnitude smaller than the hotel catalog, so the search never iterates
    the full candidate list when few hotels have availability — it queries
    the inventory once (milliseconds) and paginates the tiny eligible set.
    """
    dates_list = _date_range(check_in, check_out)
    if not dates_list:
        return {}
    match: dict[str, Any] = {
        "date": {"$in": dates_list},
        "available_rooms": {"$gte": required_rooms},
    }
    if prop_ids is not None:
        match["prop_id"] = {"$in": prop_ids}
    db = get_database()
    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {"$group": {
            "_id": {"prop": "$prop_id", "rt": "$room_type_id"},
            "covered_nights": {"$sum": 1},
            "min_available": {"$min": "$available_rooms"},
        }},
        {"$match": {"covered_nights": len(dates_list)}},
        {"$lookup": {
            "from": "room_types",
            "let": {"rt": "$_id.rt"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$room_type_id", "$$rt"]},
                             "is_active": True,
                             "max_adults": {"$gte": adults or 1},
                             "max_children": {"$gte": children or 0}}},
                {"$project": {"_id": 0, "room_type_id": 1, "name": 1,
                              "max_adults": 1, "max_children": 1, "base_capacity": 1}},
            ],
            "as": "rt",
        }},
        {"$match": {"rt": {"$ne": []}}},
        # Más barata por capacidad: la misma elección que el search por lote.
        {"$sort": {"_id.prop": 1, "rt.base_capacity": 1, "rt.room_type_id": 1}},
        {"$group": {
            "_id": "$_id.prop",
            "room_type": {"$first": {"$arrayElemAt": ["$rt", 0]}},
            "min_available": {"$first": "$min_available"},
        }},
    ]
    result: dict[int, dict[str, Any]] = {}
    for row in db.room_inventory_calendar.aggregate(pipeline):
        prop_id = row.get("_id")
        room_type = row.get("room_type")
        if prop_id is None or not room_type:
            continue
        result[int(prop_id)] = {
            **room_type,
            "min_available": int(row.get("min_available") or 0),
        }
    return result


def _general_amenities_for_properties(
    prop_ids: list[int], limit: int = 4,
) -> dict[int, list[str]]:
    """Load only hotel-wide amenity labels needed by search cards."""
    if not prop_ids:
        return {}
    db = get_database()
    docs = db.hotel_content_pages.find(
        {"prop_id": {"$in": prop_ids}},
        {"_id": 0, "prop_id": 1, "active_amenities": 1, "amenities_text": 1},
    )
    result: dict[int, list[str]] = {}
    for doc in docs:
        raw = doc.get("active_amenities") or []
        labels = [str(label).strip() for label in raw if str(label).strip()]
        if not labels:
            labels = [part.strip() for part in str(doc.get("amenities_text") or "").split(",") if part.strip()]
        result[int(doc["prop_id"])] = list(dict.fromkeys(labels))[:limit]
    return result


# Kept for existing operational tests and non-search callers. Guest search uses
# `_available_room_type_summaries_for_properties` so it never loads all types.
def _available_room_types_for_properties(
    prop_ids: list[int],
    room_types_by_property: dict[int, list[dict[str, Any]]],
    check_in: str,
    check_out: str,
    required_rooms: int,
) -> dict[int, dict[str, Any]]:
    """Legacy in-memory helper retained for compatibility."""
    dates_list = _date_range(check_in, check_out)
    if not dates_list or not prop_ids:
        return {}
    room_type_ids = [
        room_type["room_type_id"]
        for room_types in room_types_by_property.values()
        for room_type in room_types
    ]
    if not room_type_ids:
        return {}
    db = get_database()
    covered_dates: dict[tuple[int, str], set[str]] = defaultdict(set)
    cursor = db.room_inventory_calendar.find({
        "prop_id": {"$in": prop_ids},
        "room_type_id": {"$in": room_type_ids},
        "date": {"$in": dates_list},
        "available_rooms": {"$gte": required_rooms},
    }, {"_id": 0, "prop_id": 1, "room_type_id": 1, "date": 1})
    for row in cursor:
        covered_dates[(int(row["prop_id"]), str(row["room_type_id"]))].add(str(row["date"]))
    available: dict[int, dict[str, Any]] = {}
    required_dates = set(dates_list)
    for prop_id in prop_ids:
        for room_type in room_types_by_property.get(prop_id, []):
            if covered_dates.get((prop_id, room_type["room_type_id"])) == required_dates:
                available[prop_id] = room_type
                break
    return available


def _hotel_min_rates_for_properties(
    prop_ids: list[int], check_in: str, check_out: str,
) -> dict[int, float]:
    """Load minimum rates for all properties in one aggregation."""
    dates_list = _date_range(check_in, check_out)
    if not dates_list or not prop_ids:
        return {}
    db = get_database()
    rows = db.hotel_rate_calendar.aggregate([
        {"$match": {
            "prop_id": {"$in": prop_ids},
            "date": {"$in": dates_list},
            "is_closed": {"$ne": True},
        }},
        {"$group": {"_id": "$prop_id", "min_rate": {"$min": "$rate_amount"}}},
    ])
    return {
        int(row["_id"]): round(float(row["min_rate"]), 2)
        for row in rows
        if row.get("_id") is not None and row.get("min_rate") is not None
    }


def _hotel_min_rate_for_range(prop_id: int, check_in: str, check_out: str) -> float | None:
    rates = _hotel_min_rates_for_properties([prop_id], check_in, check_out)
    return rates.get(prop_id)


def _hotel_min_rates_from_today_for_properties(prop_ids: list[int]) -> dict[int, float]:
    """Minimum nightly rate from today onward per property — the base 'Desde'
    price for searches without a date range. One aggregation for the batch.
    """
    if not prop_ids:
        return {}
    from src.app.core.timezone import local_today
    db = get_database()
    today = local_today()
    rows = db.hotel_rate_calendar.aggregate([
        {"$match": {
            "prop_id": {"$in": prop_ids},
            "date": {"$gte": today},
            "is_closed": {"$ne": True},
        }},
        {"$group": {"_id": "$prop_id", "min_rate": {"$min": "$rate_amount"}}},
    ])
    return {
        int(row["_id"]): round(float(row["min_rate"]), 2)
        for row in rows
        if row.get("_id") is not None and row.get("min_rate") is not None
    }


def _hotel_image_url(prop_id: int) -> str | None:
    db = get_database()
    image = db.hotel_images.find_one({"prop_id": prop_id}, {"_id": 0, "image_url": 1}, sort=[("_id", 1)])
    return image.get("image_url") if image else None


def _destination_display_name(dest: dict[str, Any], dest_id: int | str) -> str:
    return (
        dest.get("display_name")
        or dest.get("destination_display_name")
        or dest.get("destination_name")
        or dest.get("name")
        or f"Destino {dest_id}"
    )


def _hotel_display_name(hotel: dict[str, Any], prop_id: int) -> str:
    return hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}"
