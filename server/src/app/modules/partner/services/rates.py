"""Rates sub-domain: rate plans, calendar, rules, promotions and coupons.

Owns reads and writes for the partner's rate-management UI.
"""
from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import (
    clean_text,
    iso_label,
    money,
    now_utc,
    safe_bool,
    safe_positive_int,
    slugify,
)
from src.app.modules.partner.services.properties import partner_hotel_detail  # type: ignore[assignment]
from src.database.connection import get_database


def _rate_plans_for_prop(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.rate_plans.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )
    for item in items:
        item["base_rate_label"] = money(item.get("base_rate"))
        item["updated_at_label"] = iso_label(item.get("updated_at"))
    return items


def _rate_calendar_for_prop(prop_id: int, limit: int = 90) -> list[dict[str, Any]]:
    db = get_database()
    plan_lookup = {
        item["rate_plan_id"]: item.get("name") or item["rate_plan_id"]
        for item in db.rate_plans.find({"prop_id": prop_id}, {"_id": 0, "rate_plan_id": 1, "name": 1})
    }
    items = list(
        db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("rate_plan_id", 1)])
        .limit(limit)
    )
    for item in items:
        item["plan_name"] = plan_lookup.get(item.get("rate_plan_id"), item.get("rate_plan_id"))
        item["rate_amount_label"] = money(item.get("rate_amount"))
    return items


def _rate_rules_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.rate_rules.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("updated_at", -1)])
        .limit(limit)
    )
    for item in items:
        item["updated_at_label"] = iso_label(item.get("updated_at"))
    return items


def _promotion_campaigns_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.promotion_campaigns.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("end_date", 1)])
        .limit(limit)
    )
    return items


def _coupon_codes_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.coupon_codes.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("coupon_code", 1)])
        .limit(limit)
    )
    return items


def partner_hotel_rates(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    rate_plans = _rate_plans_for_prop(prop_id)
    detail["rate_plans"] = rate_plans
    detail["calendar"] = _rate_calendar_for_prop(prop_id)
    detail["rate_rules"] = _rate_rules_for_prop(prop_id)
    detail["promotions"] = _promotion_campaigns_for_prop(prop_id)
    detail["coupon_codes"] = _coupon_codes_for_prop(prop_id)
    # Include room types for form selectors
    db = get_database()
    detail["room_types"] = list(
        db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
        .sort([("name", 1)])
    )
    return detail


def _validate_rate_plan(
    prop_id: int,
    name: str,
    base_rate: Any,
    rate_plan_id: str | None = None,
) -> str:
    """Validate rate plan business rules. Returns error message or empty string."""
    clean_name = clean_text(name)
    if not clean_name:
        return "Debe ingresar el nombre del plan tarifario."
    if len(clean_name) > 100:
        return "El nombre no puede superar los 100 caracteres."
    # RF-007: base_price > 0
    try:
        rate = float(base_rate or 0)
        if rate <= 0:
            return "base_rate debe ser mayor que 0."
        if rate > 99999.99:
            return "base_rate no puede superar 99999.99."
    except (TypeError, ValueError):
        return "Debe indicar una tarifa base válida."
    # Unique name per property
    db = get_database()
    query: dict[str, Any] = {"prop_id": prop_id, "name": clean_name}
    if rate_plan_id:
        query["rate_plan_id"] = {"$ne": rate_plan_id}
    existing = db.rate_plans.find_one(query, {"_id": 1})
    if existing is not None:
        return "Ya existe un plan tarifario con ese nombre en esta propiedad."
    return ""


def create_rate_plan(
    prop_id: int,
    *,
    name: str,
    description: str,
    base_rate: Any,
    currency: str,
    room_type_id: str = "",
    is_active: Any = True,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    error = _validate_rate_plan(prop_id, name, base_rate)
    if error:
        raise ValueError(error)

    db = get_database()
    clean_name = clean_text(name)
    clean_room_type_id = clean_text(room_type_id)
    rate_plan_id = f"RP-{prop_id}-{slugify(clean_name)}"
    base_rate_value = round(float(base_rate), 2)

    payload = {
        "rate_plan_id": rate_plan_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": clean_text(description),
        "room_type_id": clean_room_type_id,
        "base_rate": base_rate_value,
        "currency": clean_text(currency) or "USD",
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    return db.rate_plans.find_one_and_update(
        {"rate_plan_id": rate_plan_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def update_rate_plan(
    rate_plan_id: str,
    *,
    name: str,
    description: str,
    base_rate: Any,
    currency: str,
    room_type_id: str = "",
    is_active: Any = True,
) -> dict[str, Any] | None:
    """Update an existing rate plan. Returns None if not found."""
    db = get_database()
    existing = db.rate_plans.find_one({"rate_plan_id": rate_plan_id}, {"_id": 0, "prop_id": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    error = _validate_rate_plan(prop_id, name, base_rate, rate_plan_id=rate_plan_id)
    if error:
        raise ValueError(error)

    clean_name = clean_text(name)
    base_rate_value = round(float(base_rate), 2)
    payload = {
        "name": clean_name,
        "description": clean_text(description),
        "room_type_id": clean_text(room_type_id),
        "base_rate": base_rate_value,
        "currency": clean_text(currency) or "USD",
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    return db.rate_plans.find_one_and_update(
        {"rate_plan_id": rate_plan_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def delete_rate_plan(rate_plan_id: str) -> dict[str, Any] | None:
    """Delete a rate plan if it has no active or future bookings.

    Returns the deleted data or None if not found.
    Raises ValueError if the plan has active bookings.
    """
    db = get_database()
    existing = db.rate_plans.find_one(
        {"rate_plan_id": rate_plan_id},
        {"_id": 0, "prop_id": 1, "name": 1},
    )
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    from datetime import date
    today = date.today().isoformat()
    active_bookings = db.booking_orders.count_documents({
        "prop_id": prop_id,
        "rate_plan_id": rate_plan_id,
        "status": {"$nin": ["cancelled", "rejected"]},
        "check_out_date": {"$gte": today},
    })
    if active_bookings > 0:
        raise ValueError(
            f"No se puede eliminar el plan '{existing.get('name', rate_plan_id)}' porque "
            f"tiene {active_bookings} reserva(s) activa(s) o futura(s)."
        )

    db.rate_plans.delete_one({"rate_plan_id": rate_plan_id})
    db.hotel_rate_calendar.delete_many({"rate_plan_id": rate_plan_id})
    db.rate_rules.delete_many({"rate_plan_id": rate_plan_id})
    return {"rate_plan_id": rate_plan_id, "prop_id": prop_id, "deleted": True}


def list_rate_plans_for_prop(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """List all rate plans for a property."""
    return _rate_plans_for_prop(prop_id, limit=limit)


def create_seasonal_rule(
    prop_id: int,
    *,
    rate_plan_id: str,
    name: str,
    start_date: str,
    end_date: str,
    price_override: Any,
) -> dict[str, Any] | None:
    """Create a seasonal rule (temporada) that overrides the base price for a date range."""
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_name = clean_text(name)
    clean_start = clean_text(start_date)
    clean_end = clean_text(end_date)
    clean_plan_id = clean_text(rate_plan_id)

    if not clean_name or not clean_start or not clean_end or not clean_plan_id:
        raise ValueError("Debe indicar nombre, fechas y plan tarifario.")
    if db.rate_plans.find_one({"prop_id": prop_id, "rate_plan_id": clean_plan_id}, {"_id": 1}) is None:
        raise ValueError("El rate_plan_id no existe para este hotel.")
    try:
        override_value = round(float(price_override or 0), 2)
        if override_value <= 0:
            raise ValueError("price_override debe ser mayor que 0.")
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc) if "price_override" in str(exc) else "Debe indicar un precio override válido.") from None

    rule_id = f"SR-{prop_id}-{slugify(clean_name)}-{clean_start}"
    payload = {
        "rule_id": rule_id,
        "prop_id": prop_id,
        "rate_plan_id": clean_plan_id,
        "name": clean_name,
        "start_date": clean_start,
        "end_date": clean_end,
        "price_override": override_value,
        "updated_at": now_utc(),
    }
    return db.rate_rules.find_one_and_update(
        {"rule_id": rule_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def delete_seasonal_rule(rule_id: str) -> dict[str, Any] | None:
    """Delete a seasonal rule."""
    db = get_database()
    existing = db.rate_rules.find_one({"rule_id": rule_id}, {"_id": 0, "rule_id": 1})
    if existing is None:
        return None
    db.rate_rules.delete_one({"rule_id": rule_id})
    return {"rule_id": rule_id, "deleted": True}


def list_seasonal_rules(
    prop_id: int | None = None,
    rate_plan_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List seasonal rules, optionally filtered by prop_id or rate_plan_id."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id is not None:
        query["prop_id"] = prop_id
    if rate_plan_id:
        query["rate_plan_id"] = rate_plan_id
    items = list(
        db.rate_rules.find(query, {"_id": 0})
        .sort([("start_date", 1)])
        .limit(limit)
    )
    for item in items:
        item["updated_at_label"] = iso_label(item.get("updated_at"))
        item["range_label"] = f"{item.get('start_date')} -> {item.get('end_date')}"
    return items


def save_rate_calendar_entry(
    prop_id: int,
    *,
    rate_plan_id: str,
    date: str,
    rate_amount: Any,
    min_stay_nights: Any,
    is_closed: Any = False,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_rate_plan_id = clean_text(rate_plan_id)
    clean_date = clean_text(date)
    if not clean_rate_plan_id or not clean_date:
        raise ValueError("Debe indicar rate_plan_id y fecha.")
    if db.rate_plans.find_one({"prop_id": prop_id, "rate_plan_id": clean_rate_plan_id}, {"_id": 1}) is None:
        raise ValueError("El rate_plan_id no existe para este hotel.")
    # RF-004: Validate rate_amount > 0
    try:
        rate_amount_value = float(rate_amount or 0)
    except (TypeError, ValueError):
        raise ValueError("Debe indicar un valor de tarifa válido.") from None
    if rate_amount_value <= 0:
        raise ValueError("La tarifa debe ser mayor que 0.")
    if rate_amount_value > 99999.99:
        raise ValueError("La tarifa no puede superar 99999.99.")















    min_stay_value = max(safe_positive_int(min_stay_nights, 1), 1)
    payload = {
        "prop_id": prop_id,
        "rate_plan_id": clean_rate_plan_id,
        "date": clean_date,
        "rate_amount": round(rate_amount_value, 2),
        "min_stay_nights": min_stay_value,
        "is_closed": safe_bool(is_closed),
        "updated_at": now_utc(),
    }
    return db.hotel_rate_calendar.find_one_and_update(
        {"prop_id": prop_id, "rate_plan_id": clean_rate_plan_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def batch_update_rate_calendar(
    prop_id: int,
    *,
    rate_plan_id: str,
    start_date: str,
    end_date: str,
    rate_amount: Any,
    min_stay_nights: Any | None = None,
    is_closed: Any | None = None,
    only_weekends: bool = False,
) -> dict[str, Any]:
    """Update rate calendar entries for a date range in batch.

    RF-003: Batch update by date range.
    If only_weekends=True, only updates Saturday/Sunday dates.
    Returns count of affected entries.
    """
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        raise ValueError("Propiedad no encontrada.")
    db = get_database()
    clean_plan_id = clean_text(rate_plan_id)
    clean_start = clean_text(start_date)
    clean_end = clean_text(end_date)

    if not clean_plan_id or not clean_start or not clean_end:
        raise ValueError("Debe indicar rate_plan_id, fecha inicio y fecha fin.")
    if db.rate_plans.find_one({"prop_id": prop_id, "rate_plan_id": clean_plan_id}, {"_id": 1}) is None:
        raise ValueError("El rate_plan_id no existe para este hotel.")

    # Validate rate_amount > 0
    try:
        rate_value = float(rate_amount or 0)
    except (TypeError, ValueError):
        raise ValueError("Debe indicar un valor de tarifa válido.") from None
    if rate_value <= 0:
        raise ValueError("La tarifa debe ser mayor que 0.")
    if rate_value > 99999.99:
        raise ValueError("La tarifa no puede superar 99999.99.")







    from datetime import date as date_type, timedelta
    try:
        cur = date_type.fromisoformat(clean_start)
        end = date_type.fromisoformat(clean_end)
    except (ValueError, TypeError):
        raise ValueError("Fechas inválidas.") from None

    if cur > end:
        raise ValueError("La fecha inicio debe ser anterior o igual a la fecha fin.")

    min_stay_value = safe_positive_int(min_stay_nights, 0) if min_stay_nights is not None else None
    now = now_utc()
    affected = 0

    while cur <= end:
        if only_weekends and cur.weekday() not in (5, 6):  # Sat=5, Sun=6
            cur += timedelta(days=1)
            continue

        date_str = cur.isoformat()
        payload: dict[str, Any] = {
            "prop_id": prop_id,
            "rate_plan_id": clean_plan_id,
            "date": date_str,
            "rate_amount": round(rate_value, 2),
            "updated_at": now,
        }
        if min_stay_value is not None and min_stay_value > 0:
            payload["min_stay_nights"] = min_stay_value
        if is_closed is not None:
            payload["is_closed"] = safe_bool(is_closed)

        db.hotel_rate_calendar.update_one(
            {"prop_id": prop_id, "rate_plan_id": clean_plan_id, "date": date_str},
            {"$set": payload, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        affected += 1
        cur += timedelta(days=1)

    return {"affected_days": affected, "start_date": clean_start, "end_date": clean_end, "rate_plan_id": clean_plan_id}


def generate_calendar_from_rules(
    prop_id: int,
    *,
    rate_plan_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Generate rate calendar entries from base_price + seasonal rules.

    RF-005: For each rate plan, if no manual override exists for a date,
    generate entries based on the plan's base_price and any seasonal
    rules that apply.

    If rate_plan_id is None, processes all plans for the property.
    Date range defaults to next 90 days.
    """
    from datetime import date as date_type, timedelta

    detail = partner_hotel_detail(prop_id)
    if detail is None:
        raise ValueError("Propiedad no encontrada.")
    db = get_database()

    today = date_type.today()
    if start_date:
        try:
            range_start = date_type.fromisoformat(clean_text(start_date))
        except (ValueError, TypeError):
            raise ValueError(f"Fecha inicio inválida: {start_date}") from None
    else:
        range_start = today

    if end_date:
        try:
            range_end = date_type.fromisoformat(clean_text(end_date))
        except (ValueError, TypeError):
            raise ValueError(f"Fecha fin inválida: {end_date}") from None
    else:
        range_end = today + timedelta(days=90)

    if range_start > range_end:
        raise ValueError("La fecha inicio debe ser anterior a la fecha fin.")

    # Get plans to process
    plan_query: dict[str, Any] = {"prop_id": prop_id}
    if rate_plan_id:
        plan_query["rate_plan_id"] = rate_plan_id
    plans = list(db.rate_plans.find(plan_query, {"_id": 0}))

    if not plans:
        return {"plans_processed": 0, "entries_generated": 0, "message": "No hay planes tarifarios para procesar."}

    # Get all seasonal rules for this property, indexed by rate_plan_id
    all_rules = list(db.rate_rules.find({"prop_id": prop_id}, {"_id": 0}))
    rules_by_plan: dict[str, list[dict[str, Any]]] = {}
    for rule in all_rules:
        rp_id = rule.get("rate_plan_id", "")
        if rp_id:
            rules_by_plan.setdefault(rp_id, []).append(rule)

    total_generated = 0
    plan_count = 0
    now = now_utc()

    for plan in plans:
        plan_id = plan["rate_plan_id"]
        base_rate = plan.get("base_rate", 0) or 0
        if base_rate <= 0:
            continue  # skip plans without a valid base rate
        plan_rules = rules_by_plan.get(plan_id, [])
        plan_count += 1

        cur = range_start
        while cur <= range_end:
            date_str = cur.isoformat()

            # Skip dates that already have a manual entry
            existing = db.hotel_rate_calendar.find_one(
                {"prop_id": prop_id, "rate_plan_id": plan_id, "date": date_str},
                {"_id": 0, "rate_amount": 1},
            )
            if existing is not None:
                cur += timedelta(days=1)
                continue

            # Find matching seasonal rule
            price = base_rate
            for rule in plan_rules:
                try:
                    r_start = date_type.fromisoformat(rule.get("start_date", ""))
                    r_end = date_type.fromisoformat(rule.get("end_date", ""))
                    if r_start <= cur <= r_end:
                        override = rule.get("price_override", 0)
                        if override > 0:
                            price = override
                            break
                except (ValueError, TypeError):
                    continue

            db.hotel_rate_calendar.find_one_and_update(
                {"prop_id": prop_id, "rate_plan_id": plan_id, "date": date_str},
                {
                    "$set": {
                        "prop_id": prop_id,
                        "rate_plan_id": plan_id,
                        "date": date_str,
                        "rate_amount": round(price, 2),
                        "source": "generated",
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
            total_generated += 1
            cur += timedelta(days=1)

    return {
        "plans_processed": plan_count,
        "entries_generated": total_generated,
        "start_date": range_start.isoformat(),
        "end_date": range_end.isoformat(),
    }
