from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import (
    clean_text,
    normalize_label,
    now_utc,
    register_content_change,
    safe_bool,
)
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.content.amenities import _amenity_category
from src.app.modules.partner.services.content.queries import content_page_for_prop
from src.app.modules.partner.services.content.special_requests import DEFAULT_SPECIAL_REQUESTS
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


_VALID_REQUEST_FLAGS = {"pet_related", "late_arrival", "chargeable"}


def save_special_requests(
    prop_id: int,
    *,
    special_requests: list[dict[str, Any]],
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    """Replace the hotel's special-requests catalog (labels/prices/flags).

    The Amenities page tab sends the FULL configured list; this upserts it on
    ``hotel_content_pages``. Entries are validated and deduplicated by
    normalized label. (El umbral ``high_floor_from`` se eliminó 2026-08: las
    peticiones ya no se validan contra el piso.)

    Returns the updated content-page document (or None if the property
    doesn't exist). Raises ``ValueError`` on invalid entries.
    """
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in special_requests:
        if not isinstance(entry, dict):
            continue
        label = normalize_label(entry.get("label"))
        if not label:
            raise ValueError("Cada petición necesita un label.")
        key = label.lower()
        try:
            price = round(float(entry.get("unit_price") or 0.0), 2)
        except (ValueError, TypeError):
            price = 0.0
        if price < 0:
            raise ValueError(f"El precio de '{label}' no puede ser negativo.")
        flags = [str(f).strip().lower() for f in (entry.get("flags") or []) if str(f).strip()]
        unknown = set(flags) - _VALID_REQUEST_FLAGS
        if unknown:
            raise ValueError(f"Flags inválidas para '{label}': {sorted(unknown)}")
        if key in seen:
            # La última entrada gana sobre la duplicada (mismo label normalizado).
            for existing in clean:
                if normalize_label(existing["label"]).lower() == key:
                    existing["label"] = label
                    existing["unit_price"] = price
                    existing["flags"] = sorted(set(flags))
                    break
            continue
        seen.add(key)
        clean.append({"label": label, "unit_price": price, "flags": sorted(set(flags))})

    # Tombstones: defaults que el hotel eliminó explícitamente. El read
    # (special_requests_payload_for_prop) mergea los defaults por label; sin
    # esto, borrar una petición default era ficticio: al guardar volvía.
    sent_keys = {normalize_label(e["label"]).lower() for e in clean}
    removed_requests = sorted(
        normalize_label(d["label"])
        for d in DEFAULT_SPECIAL_REQUESTS
        if normalize_label(d["label"]).lower() not in sent_keys
    )

    db = get_database()
    document = db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {
            "$set": {
                "special_requests": clean,
                "removed_requests": removed_requests,
                "updated_at": now_utc(),
            },
            "$setOnInsert": {"created_at": now_utc()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_content_change(
        prop_id, "hotel_content_pages", "upsert_special_requests",
        {"count": len(clean)},
        changed_by=changed_by,
    )
    register_action(
        prop_id=prop_id,
        entity_type="special_request",
        entity_id=f"special_requests_{prop_id}",
        action="update",
        summary=f"Catálogo de peticiones especiales actualizado: {len(clean)} peticiones",
        changed_by=changed_by,
        metadata={"count": len(clean)},
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
    rate_plan_id: str = "",
    season_id: str = "",
    # New structured fields (SPEC 022)
    cancellation_hours: Any = None,
    pets_allowed: Any = None,
    pet_fee: Any = None,
    children_allowed: Any = None,
    extra_bed_fee: Any = None,
    min_stay: Any = None,
    max_stay: Any = None,
    deposit_percent: Any = None,
    deposit_required: Any = None,
    cancellation_penalty_percent: Any = None,
    early_check_in_enabled: Any = None,
    early_check_in_courtesy_minutes: Any = None,
    early_check_in_default_fee: Any = None,
    late_checkout_enabled: Any = None,
    late_checkout_courtesy_minutes: Any = None,
    late_checkout_default_fee: Any = None,
    guaranteed_reservation: Any = None,
    late_arrival_cutoff: Any = None,
    no_show_execution: Any = None,
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    # Check-out y check-in son días distintos (ej. 15:00 / 12:00), no se comparan
    ci = _parse_time(check_in_time)
    co = _parse_time(check_out_time)

    db = get_database()
    clean_room_type = clean_text(room_type_id)
    clean_rate_plan = clean_text(rate_plan_id)
    clean_season = clean_text(season_id)
    # Build the filter: rate_plan > room_type > hotel-wide, optionally per-season
    filter_: dict[str, object] = {"prop_id": prop_id}
    if clean_rate_plan:
        filter_["rate_plan_id"] = clean_rate_plan
    elif clean_room_type:
        filter_["room_type_id"] = clean_room_type
        filter_["rate_plan_id"] = {"$in": ["", None]}
    else:
        filter_["room_type_id"] = {"$in": ["", None]}
        filter_["rate_plan_id"] = {"$in": ["", None]}
    if clean_season:
        filter_["season_id"] = clean_season
    else:
        filter_["season_id"] = {"$in": ["", None]}

    # Parse optional numeric fields
    parsed_cancel_hours = _parse_hours(cancellation_hours)
    parsed_pets_allowed = safe_bool(pets_allowed) if pets_allowed is not None else None
    parsed_pet_fee = _parse_fee(pet_fee) if pet_fee is not None else None
    parsed_children_allowed = safe_bool(children_allowed) if children_allowed is not None else None
    parsed_extra_bed_fee = _parse_fee(extra_bed_fee) if extra_bed_fee is not None else None
    parsed_min_stay = _parse_stay(min_stay, 1) if min_stay is not None else None
    parsed_max_stay = _parse_stay(max_stay, 30) if max_stay is not None else None
    try:
        parsed_deposit_percent = int(float(str(deposit_percent))) if deposit_percent is not None else None
    except (ValueError, TypeError):
        parsed_deposit_percent = None
    parsed_deposit_required = safe_bool(deposit_required) if deposit_required is not None else None
    try:
        parsed_cancel_penalty = int(float(str(cancellation_penalty_percent))) if cancellation_penalty_percent is not None else None
    except (ValueError, TypeError):
        parsed_cancel_penalty = None
    parsed_early_enabled = safe_bool(early_check_in_enabled) if early_check_in_enabled is not None else None
    try:
        parsed_early_courtesy = max(0, min(int(float(str(early_check_in_courtesy_minutes))), 240)) if early_check_in_courtesy_minutes is not None else None
    except (ValueError, TypeError):
        parsed_early_courtesy = None
    parsed_early_fee = _parse_fee(early_check_in_default_fee) if early_check_in_default_fee is not None else None
    # Late check-out: misma política hotel-wide que early check-in (la ventana
    # de salida es global del hotel, nunca por tipo de habitación / plan).
    parsed_late_checkout_enabled = safe_bool(late_checkout_enabled) if late_checkout_enabled is not None else None
    try:
        parsed_late_courtesy = max(0, min(int(float(str(late_checkout_courtesy_minutes))), 240)) if late_checkout_courtesy_minutes is not None else None
    except (ValueError, TypeError):
        parsed_late_courtesy = None
    parsed_late_fee = _parse_fee(late_checkout_default_fee) if late_checkout_default_fee is not None else None
    parsed_guaranteed = safe_bool(guaranteed_reservation) if guaranteed_reservation is not None else None
    parsed_late_cutoff: str | None = None
    if late_arrival_cutoff not in (None, ""):
        # _parse_time devuelve el raw sin normalizar cuando no parsea
        # (backward compat) — validar HH:MM aquí de forma explícita.
        raw_cutoff = clean_text(late_arrival_cutoff)
        cutoff_parts = raw_cutoff.split(":")
        cutoff_ok = len(cutoff_parts) == 2
        if cutoff_ok:
            try:
                cutoff_h, cutoff_m = int(cutoff_parts[0]), int(cutoff_parts[1])
                cutoff_ok = 0 <= cutoff_h <= 23 and 0 <= cutoff_m <= 59
            except (TypeError, ValueError):
                cutoff_ok = False
        if not cutoff_ok:
            raise ValueError("La hora límite de llegada debe tener formato HH:MM (ej. 23:59).")
        parsed_late_cutoff = f"{cutoff_h:02d}:{cutoff_m:02d}"
    parsed_no_show_execution = (
        clean_text(no_show_execution).lower() if no_show_execution not in (None, "") else None
    )
    if parsed_no_show_execution not in (None, "next_day", "same_day_cutoff", "manual"):
        raise ValueError("La ejecución de no-show debe ser next_day, same_day_cutoff o manual.")

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
        "rate_plan_id": clean_rate_plan,
        "season_id": clean_season,
        "cancellation_policy": clean_text(cancellation_policy),
        "pet_policy": clean_text(pet_policy),
        "children_policy": clean_text(children_policy),
        "extra_bed_policy": clean_text(extra_bed_policy),
        "payment_policy": clean_text(payment_policy),
        "house_rules": clean_text(house_rules),
        "source": "partner_manual",
        "updated_at": now_utc(),
    }

    # Check-in/check-out: only set for hotel-wide saves (not per-room-type or per-rate-plan),
    # because these are global hotel settings
    if not clean_room_type and not clean_rate_plan:
        payload["check_in_time"] = ci
        payload["check_out_time"] = co

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
    if parsed_deposit_percent is not None:
        payload["deposit_percent"] = max(0, min(parsed_deposit_percent, 100))
    if parsed_deposit_required is not None:
        payload["deposit_required"] = parsed_deposit_required
    if parsed_cancel_penalty is not None:
        payload["cancellation_penalty_percent"] = max(0, min(parsed_cancel_penalty, 100))
    # Early check-in is a hotel-wide arrival policy, just like check-in/out
    # hours; room-type and rate-plan scopes must not silently override it.
    if not clean_room_type and not clean_rate_plan:
        if parsed_early_enabled is not None:
            payload["early_check_in_enabled"] = parsed_early_enabled
        if parsed_early_courtesy is not None:
            payload["early_check_in_courtesy_minutes"] = parsed_early_courtesy
        if parsed_early_fee is not None:
            payload["early_check_in_default_fee"] = parsed_early_fee
        if parsed_late_checkout_enabled is not None:
            payload["late_checkout_enabled"] = parsed_late_checkout_enabled
        if parsed_late_courtesy is not None:
            payload["late_checkout_courtesy_minutes"] = parsed_late_courtesy
        if parsed_late_fee is not None:
            payload["late_checkout_default_fee"] = parsed_late_fee
        # Late arrival / no-show es política hotel-wide, mismo contrato que
        # early_check_in: las filas por tipo de habitación / plan tarifario
        # nunca deben pisar los valores globales.
        if parsed_guaranteed is not None:
            payload["guaranteed_reservation"] = parsed_guaranteed
        if parsed_late_cutoff is not None:
            payload["late_arrival_cutoff"] = parsed_late_cutoff
        if parsed_no_show_execution is not None:
            payload["no_show_execution"] = parsed_no_show_execution

    document = db.hotel_policies.find_one_and_update(
        filter_,
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    scope_parts: list[str] = []
    if clean_rate_plan:
        scope_parts.append(f"plan tarifario '{clean_rate_plan}'")
    elif clean_room_type:
        scope_parts.append(f"tipo de habitación '{clean_room_type}'")
    scope = f" para {' + '.join(scope_parts)}" if scope_parts else ""
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
