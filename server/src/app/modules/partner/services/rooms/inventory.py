"""Inventory calendar: room_inventory_calendar CRUD and occupancy helpers."""

from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc, safe_positive_int
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.app.modules.partner.services.rooms.availability import _availability_blocks_for_prop, _blackout_blocks_for_prop
from src.app.modules.partner.services.rooms.types import _room_types_for_prop
from src.database.connection import get_database


def _inventory_for_prop(prop_id: int, limit: int = 365, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    db = get_database()
    query: dict[str, Any] = {"prop_id": prop_id, "is_deleted": {"$ne": True}}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}
    elif end_date:
        query["date"] = {"$lte": end_date}
    items = list(
        db.room_inventory_calendar.find(query, {"_id": 0})
        .sort([("date", 1), ("room_type_id", 1)])
        .limit(limit)
    )
    room_name_lookup = {
        item["room_type_id"]: item.get("name") or item["room_type_id"]
        for item in db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
    }
    for item in items:
        item["room_type_name"] = room_name_lookup.get(item["room_type_id"], item["room_type_id"])
        item["occupancy_label"] = _occupancy_label(item)
        item["occupancy_pct"] = _occupancy_pct(item)
    return items


def _occupancy_label(item: dict[str, Any]) -> str:
    total = item.get("total_rooms", 0) or 0
    available = item.get("available_rooms", 0) or 0
    if total == 0:
        return "--"
    return f"{available}/{total} disponibles"


def _occupancy_pct(item: dict[str, Any]) -> float:
    total = item.get("total_rooms", 0) or 0
    available = item.get("available_rooms", 0) or 0
    if total == 0:
        return 0.0
    return round((1 - available / total) * 100, 1)


def save_inventory_entry(
    prop_id: int,
    *,
    room_type_id: str,
    date: str,
    total_rooms: Any,
    available_rooms: Any,
    blocked_rooms: Any,
    expected_version: int | None = None,
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

    now = now_utc()

    if expected_version is not None:
        filter_ = {
            "prop_id": prop_id, "room_type_id": clean_room_type_id,
            "date": clean_date, "version": expected_version,
        }
        payload = {
            "total_rooms": total_value, "available_rooms": available_value,
            "blocked_rooms": blocked_value, "version": expected_version + 1,
            "updated_at": now,
        }
        result = db.room_inventory_calendar.find_one_and_update(
            filter_, {"$set": payload},
            return_document=ReturnDocument.AFTER, projection={"_id": 0},
        )
        if result is None:
            existing = db.room_inventory_calendar.find_one(
                {"prop_id": prop_id, "room_type_id": clean_room_type_id, "date": clean_date},
            )
            if existing is None:
                raise ValueError("El registro no existe. Use POST sin version para crearlo.")
            current_version = existing.get("version")
            if current_version is None and expected_version == 0:
                return db.room_inventory_calendar.find_one_and_update(
                    {"prop_id": prop_id, "room_type_id": clean_room_type_id, "date": clean_date, "version": {"$exists": False}},
                    {"$set": {"version": 1, "total_rooms": total_value, "available_rooms": available_value, "blocked_rooms": blocked_value, "updated_at": now}},
                    return_document=ReturnDocument.AFTER, projection={"_id": 0},
                )
            raise ValueError(
                f"Conflicto de concurrencia: versión actual={current_version or 0}, "
                f"esperada={expected_version}. Recargue y reintente."
            )
        return result

    payload = {
        "prop_id": prop_id, "room_type_id": clean_room_type_id,
        "date": clean_date, "total_rooms": total_value,
        "available_rooms": available_value, "blocked_rooms": blocked_value,
        "version": 1, "updated_at": now,
    }
    return db.room_inventory_calendar.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": clean_room_type_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0},
    )


def soft_delete_inventory_entry(prop_id: int, *, room_type_id: str, date: str) -> dict[str, Any] | None:
    """Soft-delete an inventory entry by setting is_deleted=True."""
    db = get_database()
    now = now_utc()
    result = db.room_inventory_calendar.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": room_type_id, "date": date},
        {"$set": {"is_deleted": True, "deleted_at": now}},
        return_document=ReturnDocument.AFTER, projection={"_id": 0},
    )
    return result


def partner_hotel_inventory(prop_id: int, days: int = 90, start_date: str = "", end_date: str = "") -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    room_types = _room_types_for_prop(prop_id)
    detail["room_types"] = room_types

    if not start_date and not end_date:
        end = date_type.today() + timedelta(days=days)
        start = date_type.today() - timedelta(days=7)
        start_date = start.isoformat()
        end_date = end.isoformat()

    detail["inventory_items"] = _inventory_for_prop(prop_id, limit=days * 20, start_date=start_date, end_date=end_date)
    detail["availability_blocks"] = _availability_blocks_for_prop(prop_id)
    detail["blackout_items"] = _blackout_blocks_for_prop(prop_id)
    return detail
