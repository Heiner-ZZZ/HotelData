from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, normalize_label, now_utc, register_content_change
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.content.amenities import _amenity_category
from src.app.modules.partner.services.content.queries import content_page_for_prop
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def save_partner_hotel_content(
    prop_id: int,
    *,
    description: str,
    highlights: str,
    amenities_text: str,
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "description": clean_text(description),
        "highlights": clean_text(highlights),
        "amenities_text": clean_text(amenities_text),
        "source": "partner_manual",
        "updated_at": now_utc(),
    }
    document = db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_content_change(prop_id, "hotel_content_pages", "upsert", payload, changed_by=changed_by)
    register_action(
        prop_id=prop_id,
        entity_type="content",
        entity_id=f"page_{prop_id}",
        action="update",
        summary="Contenido de propiedad actualizado",
        changed_by=changed_by,
        metadata={"has_description": bool(description), "has_highlights": bool(highlights)},
    )
    return document


def save_partner_hotel_amenities(
    prop_id: int,
    *,
    active_amenities: list[str],
    amenities_text: str | None = None,
    amenity_prices: dict[str, float] | None = None,
    room_type_id: str = "",
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    current = content_page_for_prop(prop_id)
    clean_active: list[str] = []
    seen: set[str] = set()
    for item in active_amenities:
        label = normalize_label(item)
        key = label.lower()
        if not label or key in seen:
            continue
        seen.add(key)
        clean_active.append(label)

    # Merge incoming prices with existing — normalize keys to lowercase for lookup
    existing_prices: dict[str, float] = dict(current.get("amenity_prices") or {})
    if amenity_prices:
        for label, price in amenity_prices.items():
            try:
                existing_prices[normalize_label(label)] = float(price)
            except (ValueError, TypeError):
                pass

    if room_type_id:
        room_amenities = dict(current.get("room_amenities") or {})
        room_amenities[room_type_id] = {
            "active_amenities": clean_active,
            "amenities_text": clean_text(amenities_text) or ", ".join(clean_active),
        }
        document = db.hotel_content_pages.find_one_and_update(
            {"prop_id": prop_id},
            {"$set": {"room_amenities": room_amenities, "updated_at": now_utc()}, "$setOnInsert": {"created_at": now_utc()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    else:
        payload = {
            "prop_id": prop_id,
            "description": current.get("description") or "",
            "highlights": current.get("highlights") or "",
            "amenities_text": clean_text(amenities_text) or ", ".join(clean_active),
            "active_amenities": clean_active,
            "amenities_catalog": [{"category": _amenity_category(label), "label": label} for label in clean_active],
            "amenity_prices": existing_prices,
            "source": current.get("source") or "partner_manual",
            "updated_at": now_utc(),
        }
        document = db.hotel_content_pages.find_one_and_update(
            {"prop_id": prop_id},
            {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    register_content_change(prop_id, "hotel_content_pages", "upsert_amenities", {"room_type_id": room_type_id, "count": len(clean_active)}, changed_by=changed_by)
    scope = f" para tipo de habitación '{room_type_id}'" if room_type_id else ""
    register_action(
        prop_id=prop_id,
        entity_type="amenity",
        entity_id=f"amenities_{prop_id}{'_'+room_type_id if room_type_id else ''}",
        action="update",
        summary=f"Amenidades actualizadas{scope}: {len(clean_active)} activas",
        changed_by=changed_by,
        metadata={"room_type_id": room_type_id, "count": len(clean_active)},
    )
    return document


def _parse_time(value: str) -> str:
    """Validate and normalize HH:MM time format."""
    raw = clean_text(value)
    if not raw:
        return ""
    parts = raw.split(":")
    if len(parts) == 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
        except (ValueError, TypeError):
            pass
    return raw  # Return as-is if unparseable (backward compat)


def _parse_hours(value: Any) -> int:
    """Parse cancellation_hours: positive int, max 720 (30 days)."""
    if value is None:
        return 0
    try:
        hours = int(float(str(value)))
        return max(0, min(hours, 720))
    except (ValueError, TypeError):
        return 0


def save_partner_hotel_policies(
    prop_id: int,
    *,
    check_in_time: str,
    check_out_time: str,
    cancellation_policy: str,
    pet_policy: str,
    children_policy: str,
    extra_bed_policy: str = "",
    payment_policy: str = "",
    house_rules: str = "",
    room_type_id: str = "",
    # New structured fields (SPEC 022)
    cancellation_hours: Any = None,
    pets_allowed: Any = None,
    pet_fee: Any = None,
    children_allowed: Any = None,
    extra_bed_fee: Any = None,
    min_stay: Any = None,
    max_stay: Any = None,
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    # RF-006: Validate check-out > check-in
    ci = _parse_time(check_in_time)
    co = _parse_time(check_out_time)
    if ci and co:
        ci_parts = ci.split(":")
        co_parts = co.split(":")
        ci_minutes = int(ci_parts[0]) * 60 + int(ci_parts[1])
        co_minutes = int(co_parts[0]) * 60 + int(co_parts[1])
        if co_minutes <= ci_minutes:
            raise ValueError("El check-out debe ser posterior al check-in.")

    db = get_database()
    clean_room_type = clean_text(room_type_id)
    # Build the filter: hotel-wide (room_type_id="") or per-room-type
    filter_: dict[str, object] = {"prop_id": prop_id}
    if clean_room_type:
        filter_["room_type_id"] = clean_room_type
    else:
        filter_["room_type_id"] = {"$in": ["", None]}

    # Parse optional numeric fields
    parsed_cancel_hours = _parse_hours(cancellation_hours)
    parsed_pets_allowed = safe_bool(pets_allowed) if pets_allowed is not None else None
    parsed_pet_fee = _parse_fee(pet_fee) if pet_fee is not None else None
    parsed_children_allowed = safe_bool(children_allowed) if children_allowed is not None else None
    parsed_extra_bed_fee = _parse_fee(extra_bed_fee) if extra_bed_fee is not None else None
    parsed_min_stay = _parse_stay(min_stay, 1) if min_stay is not None else None
    parsed_max_stay = _parse_stay(max_stay, 30) if max_stay is not None else None

    # RF-005: Validate min_stay >= 1, max_stay >= min_stay, max_stay <= 365
    if parsed_min_stay is not None and parsed_min_stay < 1:
        raise ValueError("La estancia mínima debe ser al menos 1 noche.")
    if parsed_max_stay is not None:
        if parsed_max_stay < (parsed_min_stay or 1):
            raise ValueError("La estancia máxima no puede ser menor que la mínima.")
        if parsed_max_stay > 365:
            raise ValueError("La estancia máxima no puede superar 365 noches.")

    payload: dict[str, Any] = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type,
        "check_in_time": ci,
        "check_out_time": co,
        "cancellation_policy": clean_text(cancellation_policy),
        "pet_policy": clean_text(pet_policy),
        "children_policy": clean_text(children_policy),
        "extra_bed_policy": clean_text(extra_bed_policy),
        "payment_policy": clean_text(payment_policy),
        "house_rules": clean_text(house_rules),
        "source": "partner_manual",
        "updated_at": now_utc(),
    }

    # Add structured fields only if provided
    if cancellation_hours is not None:
        payload["cancellation_hours"] = parsed_cancel_hours
    if parsed_pets_allowed is not None:
        payload["pets_allowed"] = parsed_pets_allowed
    if parsed_pet_fee is not None:
        payload["pet_fee"] = parsed_pet_fee
    if parsed_children_allowed is not None:
        payload["children_allowed"] = parsed_children_allowed
    if parsed_extra_bed_fee is not None:
        payload["extra_bed_fee"] = parsed_extra_bed_fee
    if parsed_min_stay is not None:
        payload["min_stay"] = parsed_min_stay
    if parsed_max_stay is not None:
        payload["max_stay"] = parsed_max_stay

    document = db.hotel_policies.find_one_and_update(
        filter_,
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    scope = f" para tipo de habitación '{clean_room_type}'" if clean_room_type else ""
    register_action(
        prop_id=prop_id,
        entity_type="policy",
        entity_id=f"policies_{prop_id}{'_'+clean_room_type if clean_room_type else ''}",
        action="update",
        summary=f"Políticas actualizadas{scope}",
        changed_by=changed_by,
        metadata={"room_type_id": clean_room_type},
    )
    register_content_change(prop_id, "hotel_policies", "upsert", payload, changed_by=changed_by)
    return document


def _parse_fee(value: Any) -> float:
    """Parse a fee value: non-negative float."""
    try:
        fee = round(float(str(value or 0)), 2)
        return max(0.0, fee)
    except (ValueError, TypeError):
        return 0.0


def _parse_stay(value: Any, default: int) -> int:
    """Parse stay nights: positive int."""
    try:
        nights = int(float(str(value)))
        return max(1, nights)
    except (ValueError, TypeError):
        return default
