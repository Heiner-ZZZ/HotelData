"""Room queries: combined data for partner UI pages."""

from __future__ import annotations

from typing import Any

from src.app.modules.partner.services.properties import partner_hotel_detail
from src.app.modules.partner.services.rooms.types import _room_types_for_prop
from src.database.connection import get_database


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
    for item in items:
        item["room_type_name"] = room_lookup.get(item.get("room_type_id"), item.get("room_type_id"))
        item["room_label"] = item.get("room_label") or item.get("room_type_name") or item.get("hotel_room_id")
    return items


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
