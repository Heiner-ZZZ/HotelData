"""Availability blocks and blackout dates CRUD."""

from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc, safe_positive_int
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def _blackout_blocks_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.blackout_dates.find({"prop_id": prop_id})
        .sort([("created_at", -1)])
        .limit(limit)
    )
    result = []
    for item in items:
        item["range_label"] = f"{item.get('start_date')} -> {item.get('end_date')}"
        item["blackout_id"] = str(item["_id"])
        del item["_id"]
        result.append(item)
    return result


def _availability_blocks_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_availability_blocks.find({"prop_id": prop_id})
        .sort([("start_date", -1)])
        .limit(limit)
    )
    result = []
    for item in items:
        item["range_label"] = f"{item.get('start_date')} -> {item.get('end_date')}"
        item["block_id"] = str(item["_id"])
        del item["_id"]
        result.append(item)
    return result


def _validate_blackout_overlap(
    db: Any,
    prop_id: int,
    room_type_id: str,
    start_date: str,
    end_date: str,
    exclude_blackout_id: str | None = None,
) -> str:
    query: dict[str, Any] = {"prop_id": prop_id, "room_type_id": room_type_id}
    if exclude_blackout_id:
        query["blackout_id"] = {"$ne": exclude_blackout_id}

    existing = db.blackout_dates.find_one(
        {
            **query,
            "start_date": {"$lte": end_date},
            "end_date": {"$gte": start_date},
        },
        {"_id": 0, "start_date": 1, "end_date": 1, "reason": 1},
    )
    if existing:
        return (
            f"El rango {start_date} a {end_date} se solapa con un bloqueo existente "
            f"({existing.get('start_date')} a {existing.get('end_date')}) "
            f"para este tipo de habitación: {existing.get('reason', 'sin motivo')}."
        )
    return ""


def _apply_blackout_to_calendar(
    db: Any,
    prop_id: int,
    room_type_id: str,
    start_date: str,
    end_date: str,
    blocked_rooms: int,
    *,
    increment: int = 1,
) -> int:
    if not start_date or not end_date:
        return 0
    try:
        cur = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)
    except (ValueError, TypeError):
        return 0

    now = now_utc()
    affected = 0
    step = 1 if cur <= end else -1

    while (cur <= end) if step > 0 else (cur >= end):
        date_str = cur.isoformat()
        delta = blocked_rooms * increment

        if delta >= 0:
            db.room_inventory_calendar.find_one_and_update(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                {
                    "$inc": {"blocked_rooms": delta, "available_rooms": -delta},
                    "$set": {"updated_at": now},
                },
                projection={"_id": 0, "total_rooms": 1, "blocked_rooms": 1, "available_rooms": 1},
                return_document=ReturnDocument.AFTER,
            )
        else:
            existing = db.room_inventory_calendar.find_one(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                {"_id": 0, "blocked_rooms": 1, "available_rooms": 1, "total_rooms": 1},
            )
            if existing:
                current_blocked = existing.get("blocked_rooms", 0) or 0
                remove = min(current_blocked, blocked_rooms)
                if remove > 0:
                    db.room_inventory_calendar.update_one(
                        {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                        {"$inc": {"blocked_rooms": -remove, "available_rooms": remove}, "$set": {"updated_at": now}},
                    )

        affected += 1
        cur += timedelta(days=1)

    return affected


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

    blocked_value = safe_positive_int(blocked_rooms, 1)
    if blocked_value < 1:
        raise ValueError("blocked_rooms debe ser mayor que 0.")

    overlap_error = _validate_blackout_overlap(db, prop_id, clean_room_type_id, clean_start, clean_end)
    if overlap_error:
        raise ValueError(overlap_error)

    blackout_payload = {
        "prop_id": prop_id, "room_type_id": clean_room_type_id,
        "start_date": clean_start, "end_date": clean_end,
        "reason": clean_text(reason), "blocked_rooms": blocked_value,
        "updated_at": now_utc(),
    }
    blackout_filter = {
        "prop_id": prop_id, "room_type_id": clean_room_type_id,
        "start_date": clean_start, "end_date": clean_end,
    }
    blackout_doc = db.blackout_dates.find_one_and_update(
        blackout_filter,
        {"$set": blackout_payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0},
    )
    try:
        affected_days = _apply_blackout_to_calendar(
            db, prop_id, clean_room_type_id, clean_start, clean_end,
            blocked_value, increment=1,
        )
        blackout_doc["affected_days"] = affected_days

        db.room_availability_blocks.find_one_and_update(
            blackout_filter,
            {
                "$set": {**blackout_payload},
                "$setOnInsert": {"created_at": now_utc()},
            },
            upsert=True, return_document=ReturnDocument.AFTER,
        )
    except Exception:
        db.blackout_dates.delete_one(blackout_filter)
        raise

    return blackout_doc


def delete_blackout_block(blackout_id: str) -> dict[str, Any] | None:
    from bson.objectid import ObjectId

    db = get_database()
    try:
        obj_id = ObjectId(blackout_id)
    except Exception:
        raise ValueError("ID de bloqueo inválido.")

    existing = db.blackout_dates.find_one({"_id": obj_id}, {"_id": 0})
    if existing is None:
        return None

    prop_id = existing["prop_id"]
    room_type_id = existing["room_type_id"]
    start_date = existing.get("start_date", "")
    end_date = existing.get("end_date", "")
    blocked_rooms = existing.get("blocked_rooms", 0) or 0

    if blocked_rooms > 0 and start_date and end_date:
        _apply_blackout_to_calendar(db, prop_id, room_type_id, start_date, end_date, blocked_rooms, increment=-1)

    db.blackout_dates.delete_one({"_id": obj_id})
    db.room_availability_blocks.delete_one({
        "prop_id": prop_id, "room_type_id": room_type_id,
        "start_date": start_date, "end_date": end_date,
    })
    return {"blackout_id": blackout_id, "deleted": True, "prop_id": prop_id}


def list_property_blackouts(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    return _blackout_blocks_for_prop(prop_id, limit=limit)
