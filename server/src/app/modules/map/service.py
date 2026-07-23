from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from src.database.connection import get_database

logger = logging.getLogger(__name__)

DESTINATIONS_COLLECTION = "dim_destinations"
HOTELS_COLLECTION = "dim_hotels"


def list_destinations(
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    has_geo: bool | None = None,
) -> dict[str, Any]:
    """List destinations with optional search and geo filter."""
    db = get_database()
    query: dict[str, Any] = {}

    if search:
        import re
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"destination_display_name": {"$regex": pattern}},
            {"destination_name": {"$regex": pattern}},
            {"visible_name": {"$regex": pattern}},
            {"country": {"$regex": pattern}},
            {"city": {"$regex": pattern}},
        ]
    if has_geo is True:
        query["latitude"] = {"$ne": None, "$exists": True}
        query["longitude"] = {"$ne": None, "$exists": True}
    elif has_geo is False:
        query["$or"] = [
            {"latitude": None},
            {"latitude": {"$exists": False}},
            {"longitude": None},
            {"longitude": {"$exists": False}},
        ]

    total = db[DESTINATIONS_COLLECTION].count_documents(query)
    cursor = (
        db[DESTINATIONS_COLLECTION]
        .find(query, {"_id": 0})
        .sort("destination_display_name", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_serialize_destination(doc) for doc in cursor]
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_destination(destination_id: int) -> dict[str, Any] | None:
    """Get a single destination by ID."""
    db = get_database()
    doc = db[DESTINATIONS_COLLECTION].find_one(
        {"srch_destination_id": destination_id},
        {"_id": 0},
    )
    return _serialize_destination(doc) if doc else None


def update_destination(destination_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update destination metadata (name, coordinates, country, city, description)."""
    db = get_database()

    # Validate destination exists before updating
    existing = db[DESTINATIONS_COLLECTION].find_one(
        {"srch_destination_id": destination_id},
        {"_id": 0, "srch_destination_id": 1},
    )
    if existing is None:
        return None

    update: dict[str, Any] = {}

    # Map frontend camelCase to DB snake_case
    field_map = {
        "visible_name": "visible_name",
        "country": "country",
        "city": "city",
        "description": "description",
        "latitude": "latitude",
        "longitude": "longitude",
    }

    for key, db_field in field_map.items():
        if key in data and data[key] is not None:
            update[db_field] = data[key]

    if not update:
        return get_destination(destination_id)

    db[DESTINATIONS_COLLECTION].update_one(
        {"srch_destination_id": destination_id},
        {"$set": update},
    )

    # Update visible_name display if set
    if "visible_name" in update:
        db[DESTINATIONS_COLLECTION].update_one(
            {"srch_destination_id": destination_id},
            {"$set": {"destination_display_name": update["visible_name"]}},
        )

    return get_destination(destination_id)


def list_geo_destinations() -> list[dict[str, Any]]:
    """List destinations that have coordinates (for map markers)."""
    db = get_database()
    cursor = db[DESTINATIONS_COLLECTION].find(
        {
            "latitude": {"$ne": None, "$exists": True, "$type": "number"},
            "longitude": {"$ne": None, "$exists": True, "$type": "number"},
        },
        {"_id": 0},
    ).sort("destination_display_name", 1).limit(500)
    return [_serialize_destination(doc) for doc in cursor]


def list_hotels_with_geo() -> list[dict[str, Any]]:
    """List hotels that have geo data or destination affiliation (for map markers)."""
    db = get_database()
    cursor = db[HOTELS_COLLECTION].find(
        {},
        {"_id": 0, "prop_id": 1, "hotel_name": 1, "display_name": 1,
         "prop_starrating": 1, "review_score": 1, "srch_destination_id": 1},
    ).sort("display_name", 1).limit(1000)

    # Enrich with destination coordinates
    hotels = []
    dest_coords: dict[int, dict[str, float]] = {}
    for d in db[DESTINATIONS_COLLECTION].find(
        {"latitude": {"$ne": None, "$exists": True, "$type": "number"}},
        {"_id": 0, "srch_destination_id": 1, "latitude": 1, "longitude": 1,
         "destination_display_name": 1},
    ):
        dest_coords[d["srch_destination_id"]] = {
            "lat": d["latitude"],
            "lng": d["longitude"],
            "name": d.get("destination_display_name", ""),
        }

    for doc in cursor:
        dest_id = doc.get("srch_destination_id")
        coords = dest_coords.get(dest_id) if dest_id else None
        hotel = {
            "prop_id": doc.get("prop_id"),
            "hotel_name": doc.get("hotel_name", ""),
            "display_name": doc.get("display_name") or doc.get("hotel_name", ""),
            "stars": doc.get("prop_starrating"),
            "review_score": doc.get("review_score"),
            "srch_destination_id": dest_id,
            "destination_display_name": coords["name"] if coords else "",
            "latitude": coords["lat"] if coords else None,
            "longitude": coords["lng"] if coords else None,
        }
        hotels.append(hotel)

    return hotels


def _serialize_destination(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    return {
        "srch_destination_id": doc.get("srch_destination_id"),
        "destination_display_name": doc.get("destination_display_name") or doc.get("destination_name", ""),
        "destination_name": doc.get("destination_name", ""),
        "visible_name": doc.get("visible_name") or doc.get("destination_display_name") or doc.get("destination_name", ""),
        "country": doc.get("country", ""),
        "city": doc.get("city", ""),
        "description": doc.get("description", ""),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "destination_region_label": doc.get("destination_region_label", ""),
        "active": doc.get("active", True),
    }
