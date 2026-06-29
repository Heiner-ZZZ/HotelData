"""Room types: CRUD for room_type definitions and hotel_rooms."""

from __future__ import annotations

import uuid
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
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.app.modules.partner.services.rooms.features import _feature_unit_price
from src.database.connection import get_database


def _normalize_features(raw: Any) -> list[dict[str, Any]]:
    """Normalize features from DB (strings or objects) to a list of dicts.

    Legacy string features get their unit_price from the catalog defaults
    (via ``_feature_unit_price``) so prices like "Cama extra" → $25 are
    preserved even for old data.
    """
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for f in raw:
        if isinstance(f, dict):
            result.append({
                "label": str(f.get("label", "")),
                "unit_price": float(f.get("unit_price", 0) or 0),
            })
        elif isinstance(f, str):
            result.append({
                "label": f,
                "unit_price": _feature_unit_price(f),
            })
    return result


def _room_type_by_id(room_type_id: str, prop_id: int | None = None) -> dict[str, Any] | None:
    """Get a single room type by ID."""
    db = get_database()
    query: dict[str, Any] = {"room_type_id": room_type_id}
    if prop_id is not None:
        query["prop_id"] = prop_id
    room = db.room_types.find_one(query, {"_id": 0})
    if room is None:
        return None
    room["capacity_label"] = (
        f"{room.get('base_capacity', 0)} base · "
        f"{room.get('max_adults', 0)} adultos · "
        f"{room.get('max_children', 0)} niños"
    )
    room["features"] = _normalize_features(room.get("features", []))
    room["is_roh"] = bool(room.get("is_roh", False))
    return room


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
        item["features"] = _normalize_features(item.get("features", []))
        item["is_roh"] = bool(item.get("is_roh", False))
    return items


def _validate_room_type(
    prop_id: int,
    name: str,
    room_type_id: str | None = None,
    max_adults: Any = None,
    base_rate: Any = None,
    room_number: str = "",
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

    # The name is NOT unique per property — multiple rooms can have the same name
    # (e.g., "Suite" can exist multiple times). The unique identifier is the
    # room_number within the property.
    clean_rn = clean_text(room_number)
    if clean_rn:
        rn_query: dict[str, Any] = {"prop_id": prop_id, "room_number": clean_rn}
        if room_type_id:
            rn_query["room_type_id"] = {"$ne": room_type_id}
        db = get_database()
        dup = db.room_types.find_one(rn_query, {"_id": 1})
        if dup is not None:
            return f"El número de habitación '{clean_rn}' ya existe en esta propiedad."

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
    room_number: str = "",
    floor: str = "",
    view: str = "",
    smoking: Any = False,
    accessible: Any = False,
    is_roh: Any = False,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    clean_room_number = clean_text(room_number)
    error = _validate_room_type(prop_id, name, max_adults=max_adults, base_rate=base_rate, room_number=clean_room_number)
    if error:
        raise ValueError(error)

    db = get_database()
    clean_name = clean_text(name)
    # Use room_number as unique suffix when available; otherwise append a short hash
    unique_suffix = clean_room_number if clean_room_number else uuid.uuid4().hex[:6]
    room_type_id = f"RT-{prop_id}-{slugify(clean_name)}-{unique_suffix}"
    max_adults_value = safe_positive_int(max_adults, 1)
    max_children_value = safe_positive_int(max_children, 0)
    base_capacity_value = safe_positive_int(base_capacity, max_adults_value or 1)
    base_rate_value = float(base_rate) if base_rate is not None and float(base_rate) > 0 else None

    clean_floor = clean_text(floor)
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
        "room_number": clean_room_number,
        "floor": clean_floor,
        "view": clean_text(view),
        "smoking": safe_bool(smoking),
        "accessible": safe_bool(accessible),
        "is_roh": safe_bool(is_roh),
        "updated_at": now_utc(),
    }
    document = db.room_types.find_one_and_update(
        {"room_type_id": room_type_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    # Skip hotel_rooms creation for ROH types (they use pooled inventory)
    if not safe_bool(is_roh):
        db.hotel_rooms.find_one_and_update(
            {"hotel_room_id": f"HR-{room_type_id}"},
            {
                "$set": {
                    "hotel_room_id": f"HR-{room_type_id}",
                    "prop_id": prop_id,
                    "room_type_id": room_type_id,
                    "room_label": clean_name,
                    "is_active": payload["is_active"],
                    "is_roh": payload["is_roh"],
                    "room_number": clean_room_number,
                    "floor": clean_floor,
                    "view": payload["view"],
                    "smoking": payload["smoking"],
                    "accessible": payload["accessible"],
                    "updated_at": now_utc(),
                },
                "$setOnInsert": {"created_at": now_utc()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    register_action(
        prop_id=prop_id,
        entity_type="room_type",
        entity_id=room_type_id,
        action="create",
        summary=f"Tipo de habitación '{clean_name}' creado",
        changed_by=changed_by,
        metadata={"name": clean_name, "room_number": clean_room_number, "floor": clean_floor, "max_adults": max_adults_value, "view": clean_text(view), "smoking": safe_bool(smoking), "accessible": safe_bool(accessible)},
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
    room_number: str = "",
    floor: str = "",
    view: str = "",
    smoking: Any = False,
    accessible: Any = False,
    is_roh: Any = False,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    db = get_database()
    existing = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "prop_id": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    clean_room_number = clean_text(room_number)
    error = _validate_room_type(prop_id, name, room_type_id=room_type_id, max_adults=max_adults, base_rate=base_rate, room_number=clean_room_number)
    if error:
        raise ValueError(error)

    clean_name = clean_text(name)
    clean_floor = clean_text(floor)
    payload = {
        "name": clean_name,
        "description": clean_text(description),
        "max_adults": safe_positive_int(max_adults, 1),
        "max_children": safe_positive_int(max_children, 0),
        "base_capacity": safe_positive_int(base_capacity, safe_positive_int(max_adults, 1) or 1),
        "base_rate": float(base_rate) if base_rate is not None and float(base_rate) > 0 else None,
        "is_active": safe_bool(is_active),
        "room_number": clean_room_number,
        "floor": clean_floor,
        "view": clean_text(view),
        "smoking": safe_bool(smoking),
        "accessible": safe_bool(accessible),
        "is_roh": safe_bool(is_roh),
        "updated_at": now_utc(),
    }
    document = db.room_types.find_one_and_update(
        {"room_type_id": room_type_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    # Only update hotel_rooms for non-ROH types
    existing_room = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "is_roh": 1})
    if existing_room and not existing_room.get("is_roh", False):
        db.hotel_rooms.update_one(
            {"hotel_room_id": f"HR-{room_type_id}"},
            {"$set": {
                "room_label": clean_name,
                "is_active": payload["is_active"],
                "is_roh": payload["is_roh"],
                "room_number": clean_room_number,
                "floor": clean_floor,
                "view": payload["view"],
                "smoking": payload["smoking"],
                "accessible": payload["accessible"],
                "updated_at": now_utc(),
            }},
        )
    register_action(
        prop_id=prop_id,
        entity_type="room_type",
        entity_id=room_type_id,
        action="update",
        summary=f"Tipo de habitación '{clean_name}' actualizado",
        changed_by=changed_by,
        metadata={"name": clean_name},
    )
    return document


def create_roh_room_type(
    prop_id: int,
    *,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Create or get an existing Run Of House (ROH) room type for a property.

    ROH is a virtual room type that represents "any available room" at the
    property. It uses pooled inventory (sum of availability across all room
    types) and the lowest nightly rate.
    """
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

    # Determine max capacity from existing room types
    room_types = list(db.room_types.find({"prop_id": prop_id}, {"_id": 0, "max_adults": 1, "max_children": 1, "base_capacity": 1}))
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


def delete_room_type(room_type_id: str, changed_by: str = "system") -> dict[str, Any] | None:
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

    room_name = existing.get("name", room_type_id)
    db.room_types.delete_one({"room_type_id": room_type_id})
    db.hotel_rooms.delete_many({"room_type_id": room_type_id})
    db.room_inventory_calendar.delete_many({"room_type_id": room_type_id})
    register_action(
        prop_id=prop_id,
        entity_type="room_type",
        entity_id=room_type_id,
        action="delete",
        summary=f"Tipo de habitación '{room_name}' eliminado",
        changed_by=changed_by,
        metadata={"name": room_name},
    )
    return {"room_type_id": room_type_id, "prop_id": prop_id, "deleted": True}
