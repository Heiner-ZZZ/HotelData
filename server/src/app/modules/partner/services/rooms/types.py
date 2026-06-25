"""Room types: CRUD for room_type definitions and hotel_rooms."""

from __future__ import annotations

from datetime import date
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import (
    clean_text,
    now_utc,
    safe_bool,
    safe_positive_int,
    slugify,
)
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def _room_types_for_prop(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_types.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )
    for item in items:
        item["capacity_label"] = (
            f"{item.get('base_capacity', 0)} base · "
            f"{item.get('max_adults', 0)} adultos · "
            f"{item.get('max_children', 0)} niños"
        )
    return items


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

    adults = safe_positive_int(max_adults, 1)
    if adults < 1:
        return "max_adults debe ser mayor o igual a 1."

    if base_rate is not None:
        try:
            rate = float(base_rate)
            if rate <= 0:
                return "base_rate debe ser mayor que 0."
            if rate > 99999.99:
                return "base_rate no puede superar 99999.99."
        except (ValueError, TypeError):
            return "base_rate debe ser un valor numérico válido."

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
    db = get_database()
    existing = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "prop_id": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    error = _validate_room_type(prop_id, name, room_type_id=room_type_id, max_adults=max_adults, base_rate=base_rate)
    if error:
        raise ValueError(error)

    clean_name = clean_text(name)
    payload = {
        "name": clean_name,
        "description": clean_text(description),
        "max_adults": safe_positive_int(max_adults, 1),
        "max_children": safe_positive_int(max_children, 0),
        "base_capacity": safe_positive_int(base_capacity, safe_positive_int(max_adults, 1) or 1),
        "base_rate": float(base_rate) if base_rate is not None and float(base_rate) > 0 else None,
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    document = db.room_types.find_one_and_update(
        {"room_type_id": room_type_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    db.hotel_rooms.update_one(
        {"hotel_room_id": f"HR-{room_type_id}"},
        {"$set": {"room_label": clean_name, "is_active": payload["is_active"], "updated_at": now_utc()}},
    )
    return document


def delete_room_type(room_type_id: str) -> dict[str, Any] | None:
    db = get_database()
    existing = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "prop_id": 1, "name": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

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

    db.room_types.delete_one({"room_type_id": room_type_id})
    db.hotel_rooms.delete_many({"room_type_id": room_type_id})
    db.room_inventory_calendar.delete_many({"room_type_id": room_type_id})
    return {"room_type_id": room_type_id, "prop_id": prop_id, "deleted": True}
