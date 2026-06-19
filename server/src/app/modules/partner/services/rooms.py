"""Rooms sub-domain: room types, hotel rooms, inventory and blackout dates.

Owns reads and writes for the partner's room-management UI: defining
room types, registering inventory per date, and creating blackout blocks.
"""
from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import (
    clean_text,
    now_utc,
    safe_bool,
    safe_positive_int,
    slugify,
)
from src.app.modules.partner.services.properties import partner_hotel_detail  # type: ignore[assignment]
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


def _room_types_for_prop(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_types.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )
    for item in items:
        item["capacity_label"] = f"{item.get('base_capacity', 0)} base · {item.get('max_adults', 0)} adultos · {item.get('max_children', 0)} niños"
    return items


def _inventory_for_prop(prop_id: int, limit: int = 90) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_inventory_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("room_type_id", 1)])
        .limit(limit)
    )
    room_name_lookup = {
        item["room_type_id"]: item.get("name") or item["room_type_id"]
        for item in db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
    }
    for item in items:
        item["room_type_name"] = room_name_lookup.get(item["room_type_id"], item["room_type_id"])
        item["occupancy_label"] = f"{item.get('available_rooms', 0)}/{item.get('total_rooms', 0)} disponibles"
    return items


def _blackout_blocks_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.blackout_dates.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("created_at", -1)])
        .limit(limit)
    )
    for item in items:
        item["range_label"] = f"{item.get('start_date')} -> {item.get('end_date')}"
    return items


def _availability_blocks_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_availability_blocks.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("start_date", -1)])
        .limit(limit)
    )
    for item in items:
        item["range_label"] = f"{item.get('start_date')} -> {item.get('end_date')}"
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


def partner_hotel_inventory(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    room_types = _room_types_for_prop(prop_id)
    detail["room_types"] = room_types
    detail["inventory_items"] = _inventory_for_prop(prop_id)
    detail["availability_blocks"] = _availability_blocks_for_prop(prop_id)
    detail["blackout_items"] = _blackout_blocks_for_prop(prop_id)
    return detail


def create_room_type(
    prop_id: int,
    *,
    name: str,
    description: str,
    max_adults: Any,
    max_children: Any,
    base_capacity: Any,
    is_active: Any = True,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_name = clean_text(name)
    if not clean_name:
        raise ValueError("Debe ingresar el nombre del tipo de habitación.")
    room_type_id = f"RT-{prop_id}-{slugify(clean_name)}"
    max_adults_value = safe_positive_int(max_adults, 1)
    max_children_value = safe_positive_int(max_children, 0)
    base_capacity_value = safe_positive_int(base_capacity, max_adults_value or 1)
    payload = {
        "room_type_id": room_type_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": clean_text(description),
        "max_adults": max_adults_value,
        "max_children": max_children_value,
        "base_capacity": base_capacity_value,
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    document = db.room_types.find_one_and_update(
        {"room_type_id": room_type_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    db.hotel_rooms.find_one_and_update(
        {"hotel_room_id": f"HR-{room_type_id}"},
        {
            "$set": {
                "hotel_room_id": f"HR-{room_type_id}",
                "prop_id": prop_id,
                "room_type_id": room_type_id,
                "room_label": clean_name,
                "is_active": payload["is_active"],
                "updated_at": now_utc(),
            },
            "$setOnInsert": {"created_at": now_utc()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return document


def save_inventory_entry(
    prop_id: int,
    *,
    room_type_id: str,
    date: str,
    total_rooms: Any,
    available_rooms: Any,
    blocked_rooms: Any,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_room_type_id = clean_text(room_type_id)
    clean_date = clean_text(date)
    if not clean_room_type_id or not clean_date:
        raise ValueError("Debe indicar room_type_id y fecha.")
    if db.room_types.find_one({"prop_id": prop_id, "room_type_id": clean_room_type_id}, {"_id": 1}) is None:
        raise ValueError("El room_type_id no existe para este hotel.")
    total_value = safe_positive_int(total_rooms, 0)
    blocked_value = safe_positive_int(blocked_rooms, 0)
    available_value = safe_positive_int(available_rooms, 0)
    if blocked_value > total_value:
        blocked_value = total_value
    if available_value > total_value:
        available_value = total_value
    if available_value + blocked_value > total_value:
        available_value = max(total_value - blocked_value, 0)
    payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "date": clean_date,
        "total_rooms": total_value,
        "available_rooms": available_value,
        "blocked_rooms": blocked_value,
        "updated_at": now_utc(),
    }
    return db.room_inventory_calendar.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": clean_room_type_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def create_blackout_block(
    prop_id: int,
    *,
    room_type_id: str,
    start_date: str,
    end_date: str,
    reason: str,
    blocked_rooms: Any,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_room_type_id = clean_text(room_type_id)
    clean_start = clean_text(start_date)
    clean_end = clean_text(end_date)
    if not clean_room_type_id or not clean_start or not clean_end:
        raise ValueError("Debe indicar room_type_id, fecha inicio y fecha fin.")
    if db.room_types.find_one({"prop_id": prop_id, "room_type_id": clean_room_type_id}, {"_id": 1}) is None:
        raise ValueError("El room_type_id no existe para este hotel.")
    blocked_value = safe_positive_int(blocked_rooms, 0)
    blackout_payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "start_date": clean_start,
        "end_date": clean_end,
        "reason": clean_text(reason),
        "blocked_rooms": blocked_value,
        "updated_at": now_utc(),
    }
    blackout_doc = db.blackout_dates.find_one_and_update(
        {
            "prop_id": prop_id,
            "room_type_id": clean_room_type_id,
            "start_date": clean_start,
            "end_date": clean_end,
        },
        {"$set": blackout_payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    db.room_availability_blocks.find_one_and_update(
        {
            "prop_id": prop_id,
            "room_type_id": clean_room_type_id,
            "start_date": clean_start,
            "end_date": clean_end,
        },
        {
            "$set": {
                "prop_id": prop_id,
                "room_type_id": clean_room_type_id,
                "start_date": clean_start,
                "end_date": clean_end,
                "blocked_rooms": blocked_value,
                "reason": blackout_payload["reason"],
                "updated_at": now_utc(),
            },
            "$setOnInsert": {"created_at": now_utc()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return blackout_doc
