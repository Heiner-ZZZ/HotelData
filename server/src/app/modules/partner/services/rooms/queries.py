"""Room queries: combined data for partner UI pages."""

from __future__ import annotations

from typing import Any

from src.app.modules.partner.services.properties import partner_hotel_detail
from src.app.modules.partner.services.rooms.types import _room_types_for_prop
from src.database.connection import get_database


def hotel_rooms_by_type(prop_id: int, room_type_id: str) -> list[dict[str, Any]]:
    """Return individual hotel rooms for a specific room type."""
    db = get_database()
    items = list(
        db.hotel_rooms.find(
            {"prop_id": prop_id, "room_type_id": room_type_id, "is_deleted": {"$ne": True}},
            {"_id": 0},
        )
        .sort([("room_number", 1)])
    )
    return items


def _hotel_rooms_for_prop(prop_id: int, limit: int = 80) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.hotel_rooms.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("room_label", 1), ("hotel_room_id", 1)])
        .limit(limit)
    )
    room_lookup = {
        item["room_type_id"]: item.get("name") or item["room_type_id"]
        for item in db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
    }
    # Collect all hotel_room_ids to look up upcoming bookings
    room_ids = [item.get("hotel_room_id") for item in items if item.get("hotel_room_id")]
    # Find future/active bookings that have these rooms assigned
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    upcoming_bookings = list(
        db.booking_orders.find(
            {
                "assigned_rooms": {"$in": room_ids},
                "status": {"$in": ["confirmed", "checked_in", "pending"]},
                "check_out_date": {"$gte": now.strftime("%Y-%m-%d")},
            },
            {"_id": 0, "assigned_rooms": 1, "check_in_date": 1, "check_out_date": 1, "guest_name": 1, "status": 1},
        )
    )
    # Build a lookup: hotel_room_id -> list of upcoming bookings
    room_occupancy: dict[str, list[dict[str, Any]]] = {}
    for booking in upcoming_bookings:
        assigned = booking.get("assigned_rooms", [])
        for room_id in assigned:
            if room_id not in room_occupancy:
                room_occupancy[room_id] = []
            room_occupancy[room_id].append({
                "guest_name": booking.get("guest_name", ""),
                "check_in": booking.get("check_in_date", ""),
                "check_out": booking.get("check_out_date", ""),
                "status": booking.get("status", ""),
            })

    for item in items:
        item["room_type_name"] = room_lookup.get(item.get("room_type_id"), item.get("room_type_id"))
        item["is_roh"] = bool(item.get("is_roh", False))
        item["room_label"] = item.get("room_label") or item.get("room_type_name") or item.get("hotel_room_id")
        # Attach upcoming occupancy
        room_id = item.get("hotel_room_id")
        item["upcoming_bookings"] = room_occupancy.get(room_id, [])
        item["is_occupied_soon"] = len(item["upcoming_bookings"]) > 0
        if item["upcoming_bookings"]:
            item["occupancy_label"] = _occupancy_label(item["upcoming_bookings"])
    return items


def _occupancy_label(bookings: list[dict[str, Any]]) -> str:
    """Build a short label like 'Ocupada del 26/06 al 30/06' from upcoming bookings."""
    labels = []
    for b in bookings:
        check_in = b.get("check_in", "")[:10]
        check_out = b.get("check_out", "")[:10]
        parts = []
        if check_in:
            parts.append(f"del {check_in[-5:]}")
        if check_out:
            parts.append(f"al {check_out[-5:]}")
        label = "Ocupada " + " ".join(parts) if parts else "Próximamente"
        if b.get("status") == "checked_in":
            label = "En uso " + " ".join(parts)
        labels.append(label)
    return " · ".join(labels) if labels else ""


def partner_hotel_rooms(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    room_types = _room_types_for_prop(prop_id)
    hotel_rooms = _hotel_rooms_for_prop(prop_id)
    detail["room_types"] = room_types
    detail["hotel_rooms"] = hotel_rooms
    detail["room_type_count"] = len(room_types)
    detail["hotel_room_count"] = len(hotel_rooms)
    return detail
