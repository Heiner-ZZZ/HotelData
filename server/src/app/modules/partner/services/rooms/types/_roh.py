"""ROH (Run Of House) room type operations."""

from __future__ import annotations

from typing import Any

from src.app.modules.partner.services.rooms.types._core import create_room_type
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def create_roh_room_type(
    prop_id: int, *, changed_by: str = "system",
) -> dict[str, Any] | None:
    """Create or get an existing ROH room type for a property."""
    db = get_database()
    existing_roh = db.room_types.find_one(
        {"prop_id": prop_id, "is_roh": True, "is_active": True},
        {"_id": 0},
    )
    if existing_roh:
        return existing_roh

    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    room_types = list(db.room_types.find(
        {"prop_id": prop_id},
        {"_id": 0, "max_adults": 1, "max_children": 1, "base_capacity": 1},
    ))
    max_adults_val = max((rt.get("max_adults") or 2 for rt in room_types), default=2)
    max_children_val = max((rt.get("max_children") or 0 for rt in room_types), default=0)
    base_capacity_val = max((rt.get("base_capacity") or 2 for rt in room_types), default=2)

    return create_room_type(
        prop_id,
        name="Run Of House",
        description="Habitación Run Of House — se asigna cualquier habitación disponible al momento del check-in.",
        max_adults=max_adults_val,
        max_children=max_children_val,
        base_capacity=base_capacity_val,
        is_active=True,
        is_roh=True,
        changed_by=changed_by,
    )


def _roh_available_rooms(prop_id: int) -> int:
    """Calculate available rooms for ROH as the sum across all non-ROH room types."""
    db = get_database()
    result = db.room_inventory_calendar.aggregate([
        {"$match": {"prop_id": prop_id, "is_roh": {"$ne": True}}},
        {"$group": {"_id": "$date", "total_available": {"$sum": "$available_rooms"}}},
        {"$sort": {"_id": 1}},
        {"$limit": 365},
    ])
    items = list(result)
    if not items:
        return 0
    return min(item["total_available"] for item in items)


def _roh_min_rate(prop_id: int) -> float | None:
    """Get the lowest nightly rate across all non-ROH rate plans."""
    db = get_database()
    result = db.hotel_rate_calendar.aggregate([
        {"$match": {"prop_id": prop_id, "is_closed": {"$ne": True}}},
        {"$group": {"_id": None, "min_rate": {"$min": "$rate_amount"}}},
    ])
    row = next(result, None)
    return round(float(row["min_rate"]), 2) if row and row.get("min_rate") is not None else None
