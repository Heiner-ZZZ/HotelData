from __future__ import annotations

from typing import Any

from src.app.modules.hotels.service._helpers import _safe_float, _safe_int
from src.database.connection import get_database


def _destination_ids(destination: str) -> list[int]:
    destination_id = _safe_int(destination)
    if destination_id is not None:
        return [destination_id]
    if not destination:
        return []
    db = get_database()
    docs = db.dim_destinations.find(
        {
            "$or": [
                {"destination_display_name": {"$regex": destination, "$options": "i"}},
                {"destination_label": {"$regex": destination, "$options": "i"}},
                {"destination_name": {"$regex": destination, "$options": "i"}},
            ]
        },
        {"_id": 0, "srch_destination_id": 1},
    ).limit(200)
    return [int(item["srch_destination_id"]) for item in docs if item.get("srch_destination_id") is not None]


def _hotel_lookup(prop_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not prop_ids:
        return {}
    db = get_database()
    docs = db.dim_hotels.find({"prop_id": {"$in": prop_ids}}, {"_id": 0})
    return {int(item["prop_id"]): item for item in docs if item.get("prop_id") is not None}


def _destination_lookup(destination_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not destination_ids:
        return {}
    db = get_database()
    docs = db.dim_destinations.find({"srch_destination_id": {"$in": destination_ids}}, {"_id": 0})
    return {int(item["srch_destination_id"]): item for item in docs if item.get("srch_destination_id") is not None}


def _country_lookup(country_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not country_ids:
        return {}
    db = get_database()
    docs = db.dim_visitor_countries.find({"visitor_location_country_id": {"$in": country_ids}}, {"_id": 0})
    return {int(item["visitor_location_country_id"]): item for item in docs if item.get("visitor_location_country_id") is not None}


def _site_lookup(site_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not site_ids:
        return {}
    db = get_database()
    docs = db.dim_sites.find({"site_id": {"$in": site_ids}}, {"_id": 0})
    return {int(item["site_id"]): item for item in docs if item.get("site_id") is not None}


def _build_match(filters: dict[str, Any]) -> dict[str, Any] | None:
    match: dict[str, Any] = {}
    destination = str(filters.get("destination") or "").strip()
    destination_ids = _destination_ids(destination)
    if destination:
        if not destination_ids:
            return None
        match["srch_destination_id"] = {"$in": destination_ids}

    min_price = _safe_float(filters.get("min_price"))
    max_price = _safe_float(filters.get("max_price"))
    price_filter: dict[str, Any] = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        match["price_usd"] = price_filter

    min_stars = _safe_float(filters.get("min_stars"))
    if min_stars is not None:
        match["prop_starrating"] = {"$gte": min_stars}

    promotion = str(filters.get("promotion") or "").strip()
    if promotion == "yes":
        match["promotion_flag"] = {"$in": [1, True]}
    elif promotion == "no":
        match["promotion_flag"] = {"$in": [0, False]}

    adults = _safe_int(filters.get("adults"))
    children = _safe_int(filters.get("children"))
    rooms = _safe_int(filters.get("rooms"))
    if adults is not None:
        match["srch_adults_count"] = {"$gte": adults}
    if children is not None:
        match["srch_children_count"] = {"$gte": children}
    if rooms is not None:
        match["srch_room_count"] = {"$gte": rooms}
    return match
