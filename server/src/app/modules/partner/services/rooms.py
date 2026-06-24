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


def _inventory_for_prop(prop_id: int, limit: int = 365, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
    db = get_database()
    query: dict[str, Any] = {"prop_id": prop_id}
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
    """Return occupancy percentage (0-100). 0 = all available, 100 = fully occupied/blocked."""
    total = item.get("total_rooms", 0) or 0
    available = item.get("available_rooms", 0) or 0
    if total == 0:
        return 0.0
    return round((1 - available / total) * 100, 1)


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


def partner_hotel_inventory(prop_id: int, days: int = 90, start_date: str = "", end_date: str = "") -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    room_types = _room_types_for_prop(prop_id)
    detail["room_types"] = room_types
    
    # If no explicit date range, default to last {days} days from today
    if not start_date and not end_date:
        from datetime import date, timedelta
        end = date.today() + timedelta(days=days)
        start = date.today() - timedelta(days=7)
        start_date = start.isoformat()
        end_date = end.isoformat()
    
    detail["inventory_items"] = _inventory_for_prop(prop_id, limit=days * 20, start_date=start_date, end_date=end_date)
    detail["availability_blocks"] = _availability_blocks_for_prop(prop_id)
    detail["blackout_items"] = _blackout_blocks_for_prop(prop_id)
    return detail


def _validate_room_type(
    prop_id: int,
    name: str,
    room_type_id: str | None = None,
    max_adults: Any = None,
    base_rate: Any = None,
) -> str:
    """Validate room type business rules. Returns error message or empty string."""
    clean_name = clean_text(name)
    if not clean_name:
        return "Debe ingresar el nombre del tipo de habitación."
    if len(clean_name) > 100:
        return "El nombre no puede superar los 100 caracteres."

    # max_adults must be >= 1
    adults = safe_positive_int(max_adults, 1)
    if adults < 1:
        return "max_adults debe ser mayor o igual a 1."

    # base_rate must be > 0
    if base_rate is not None:
        try:
            rate = float(base_rate)
            if rate <= 0:
                return "base_rate debe ser mayor que 0."
            if rate > 99999.99:
                return "base_rate no puede superar 99999.99."
        except (ValueError, TypeError):
            return "base_rate debe ser un valor numérico válido."

    # Unique name per property
    db = get_database()
    query: dict[str, Any] = {"prop_id": prop_id, "name": clean_name}
    if room_type_id:
        query["room_type_id"] = {"$ne": room_type_id}
    existing = db.room_types.find_one(query, {"_id": 1})
    if existing is not None:
        return "Ya existe un tipo de habitación con ese nombre en esta propiedad."

    return ""


def create_room_type(
    prop_id: int,
    *,
    name: str,
    description: str,
    max_adults: Any,
    max_children: Any,
    base_capacity: Any,
    base_rate: Any = None,
    is_active: Any = True,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    # Validate business rules
    error = _validate_room_type(prop_id, name, max_adults=max_adults, base_rate=base_rate)
    if error:
        raise ValueError(error)

    db = get_database()
    clean_name = clean_text(name)
    room_type_id = f"RT-{prop_id}-{slugify(clean_name)}"
    max_adults_value = safe_positive_int(max_adults, 1)
    max_children_value = safe_positive_int(max_children, 0)
    base_capacity_value = safe_positive_int(base_capacity, max_adults_value or 1)
    base_rate_value = float(base_rate) if base_rate is not None and float(base_rate) > 0 else None

    payload = {
        "room_type_id": room_type_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": clean_text(description),
        "max_adults": max_adults_value,
        "max_children": max_children_value,
        "base_capacity": base_capacity_value,
        "base_rate": base_rate_value,
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
            "prop_id": prop_id,
            "room_type_id": clean_room_type_id,
            "date": clean_date,
            "version": expected_version,
        }
        payload = {
            "total_rooms": total_value,
            "available_rooms": available_value,
            "blocked_rooms": blocked_value,
            "version": expected_version + 1,
            "updated_at": now,
        }
        result = db.room_inventory_calendar.find_one_and_update(
            filter_,
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
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
                    return_document=ReturnDocument.AFTER,
                    projection={"_id": 0},
                )
            raise ValueError(
                f"Conflicto de concurrencia: versión actual={current_version or 0}, "
                f"esperada={expected_version}. Recargue y reintente."
            )
        return result

    payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "date": clean_date,
        "total_rooms": total_value,
        "available_rooms": available_value,
        "blocked_rooms": blocked_value,
        "version": 1,
        "updated_at": now,
    }
    return db.room_inventory_calendar.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": clean_room_type_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def _validate_blackout_overlap(
    db: Any,
    prop_id: int,
    room_type_id: str,
    start_date: str,
    end_date: str,
    exclude_blackout_id: str | None = None,
) -> str:
    """Check if the given range overlaps with any existing blackout for the same
    prop_id + room_type_id. Returns error message or empty string.
    """
    query: dict[str, Any] = {
        "prop_id": prop_id,
        "room_type_id": room_type_id,
    }
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
    *,  # noqa
    increment: int = 1,
) -> int:
    """Iterate each date in [start_date, end_date] and update
    room_inventory_calendar: increment blocked_rooms by blocked_rooms * increment
    and adjust available_rooms accordingly.

    increment=1  → add blocked rooms (on create)
    increment=-1 → subtract blocked rooms (on delete)

    Returns the number of affected days.
    """
    from datetime import date as date_type, timedelta

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
            result = db.room_inventory_calendar.find_one_and_update(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                {
                    "$inc": {"blocked_rooms": delta, "available_rooms": -delta},
                    "$set": {"updated_at": now},
                },
                projection={"_id": 0, "total_rooms": 1, "blocked_rooms": 1, "available_rooms": 1},
                return_document=ReturnDocument.AFTER,
            )
        else:
            # For decrement, ensure blocked_rooms doesn't go below 0
            existing = db.room_inventory_calendar.find_one(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                {"_id": 0, "blocked_rooms": 1, "available_rooms": 1, "total_rooms": 1},
            )
            if existing:
                current_blocked = existing.get("blocked_rooms", 0) or 0
                current_available = existing.get("available_rooms", 0) or 0
                total = existing.get("total_rooms", 0) or 0
                remove = min(current_blocked, blocked_rooms)  # cannot go below 0
                if remove > 0:
                    db.room_inventory_calendar.update_one(
                        {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                        {
                            "$inc": {"blocked_rooms": -remove, "available_rooms": remove},
                            "$set": {"updated_at": now},
                        },
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

    # RF-004: Validate no overlap
    overlap_error = _validate_blackout_overlap(db, prop_id, clean_room_type_id, clean_start, clean_end)
    if overlap_error:
        raise ValueError(overlap_error)

    blackout_payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "start_date": clean_start,
        "end_date": clean_end,
        "reason": clean_text(reason),
        "blocked_rooms": blocked_value,
        "updated_at": now_utc(),
    }
    blackout_filter = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "start_date": clean_start,
        "end_date": clean_end,
    }
    blackout_doc = db.blackout_dates.find_one_and_update(
        blackout_filter,
        {"$set": blackout_payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    try:
        # RF-005: Update room_inventory_calendar.blocked for all dates in range
        affected_days = _apply_blackout_to_calendar(
            db, prop_id, clean_room_type_id, clean_start, clean_end,
            blocked_value, increment=1,
        )
        blackout_doc["affected_days"] = affected_days

        db.room_availability_blocks.find_one_and_update(
            blackout_filter,
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
    except Exception:
        db.blackout_dates.delete_one(blackout_filter)
        raise
    return blackout_doc


def delete_blackout_block(blackout_id: str) -> dict[str, Any] | None:
    """Delete a blackout block and reverse its effect on room_inventory_calendar.

    Returns the deleted blackout data, or None if not found.
    """
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

    # Reverse calendar effect: subtract blocked_rooms from blocked, add to available
    if blocked_rooms > 0 and start_date and end_date:
        _apply_blackout_to_calendar(
            db, prop_id, room_type_id, start_date, end_date,
            blocked_rooms, increment=-1,
        )

    # Remove from both collections
    db.blackout_dates.delete_one({"_id": obj_id})
    db.room_availability_blocks.delete_one({
        "prop_id": prop_id,
        "room_type_id": room_type_id,
        "start_date": start_date,
        "end_date": end_date,
    })

    return {"blackout_id": blackout_id, "deleted": True, "prop_id": prop_id}


def update_room_type(
    room_type_id: str,
    *,
    name: str,
    description: str,
    max_adults: Any,
    max_children: Any,
    base_capacity: Any,
    base_rate: Any = None,
    is_active: Any = True,
) -> dict[str, Any] | None:
    """Update an existing room type by room_type_id."""
    db = get_database()
    existing = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "prop_id": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    # Validate business rules
    error = _validate_room_type(prop_id, name, room_type_id=room_type_id, max_adults=max_adults, base_rate=base_rate)
    if error:
        raise ValueError(error)

    clean_name = clean_text(name)
    max_adults_value = safe_positive_int(max_adults, 1)
    max_children_value = safe_positive_int(max_children, 0)
    base_capacity_value = safe_positive_int(base_capacity, max_adults_value or 1)
    base_rate_value = float(base_rate) if base_rate is not None and float(base_rate) > 0 else None

    payload = {
        "name": clean_name,
        "description": clean_text(description),
        "max_adults": max_adults_value,
        "max_children": max_children_value,
        "base_capacity": base_capacity_value,
        "base_rate": base_rate_value,
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    document = db.room_types.find_one_and_update(
        {"room_type_id": room_type_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    # Also update the corresponding hotel_room entry
    db.hotel_rooms.update_one(
        {"hotel_room_id": f"HR-{room_type_id}"},
        {
            "$set": {
                "room_label": clean_name,
                "is_active": payload["is_active"],
                "updated_at": now_utc(),
            },
        },
    )
    return document


def list_property_blackouts(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """List all blackout blocks for a property, newest first."""
    return _blackout_blocks_for_prop(prop_id, limit=limit)


def delete_room_type(room_type_id: str) -> dict[str, Any] | None:
    """Delete a room type if it has no active or future bookings.

    Returns the deleted room type data, or None if not found.
    Raises ValueError if the room type has active bookings.
    """
    db = get_database()
    existing = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "prop_id": 1, "name": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    # Check for active or future bookings using this room type
    from datetime import date
    today = date.today().isoformat()
    active_bookings = db.booking_orders.count_documents({
        "prop_id": prop_id,
        "room_type_id": room_type_id,
        "status": {"$nin": ["cancelled", "rejected"]},
        "check_out_date": {"$gte": today},
    })
    if active_bookings > 0:
        raise ValueError(
            f"No se puede eliminar el tipo '{existing.get('name', room_type_id)}' porque "
            f"tiene {active_bookings} reserva(s) activa(s) o futura(s)."
        )

    # Delete room type and associated physical rooms
    db.room_types.delete_one({"room_type_id": room_type_id})
    db.hotel_rooms.delete_many({"room_type_id": room_type_id})
    db.room_inventory_calendar.delete_many({"room_type_id": room_type_id})

    return {"room_type_id": room_type_id, "prop_id": prop_id, "deleted": True}
