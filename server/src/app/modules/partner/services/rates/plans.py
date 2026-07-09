"""Rate plans: CRUD for rate_plans and combined hotel rates data."""

from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.core.timezone import local_today
from src.app.modules.partner.services._common import (
    clean_text,
    iso_label,
    money,
    now_utc,
    safe_bool,
    safe_positive_int,
    slugify,
)
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.properties import partner_hotel_detail
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
        if "eligible_roles" not in item:
            item["eligible_roles"] = []
        if "included_amenities" not in item:
            item["included_amenities"] = []
    return items


def _validate_rate_plan(
    prop_id: int,
    name: str,
    base_rate: Any,
    rate_plan_id: str | None = None,
) -> str:
    clean_name = clean_text(name)
    if not clean_name:
        return "Debe ingresar el nombre del plan tarifario."
    if len(clean_name) > 100:
        return "El nombre no puede superar los 100 caracteres."
    try:
        rate = float(base_rate or 0)
        if rate <= 0:
            return "base_rate debe ser mayor que 0."
        if rate > 99999.99:
            return "base_rate no puede superar 99999.99."
    except (TypeError, ValueError):
        return "Debe indicar una tarifa base válida."
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
    base_occupancy: int = 2,
    extra_adult_price: float = 0.0,
    extra_child_price: float = 0.0,
    tax_included: Any = False,
    tax_rate: float = 0.0,
    is_active: Any = True,
    eligible_roles: list[str] | None = None,
    included_amenities: list[str] | None = None,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    error = _validate_rate_plan(prop_id, name, base_rate)
    if error:
        raise ValueError(error)

    db = get_database()
    clean_name = clean_text(name)
    rate_plan_id = f"RP-{prop_id}-{slugify(clean_name)}"
    base_rate_value = round(float(base_rate), 2)

    payload = {
        "rate_plan_id": rate_plan_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": clean_text(description),
        "room_type_id": clean_text(room_type_id),
        "base_rate": base_rate_value,
        "currency": clean_text(currency) or "USD",
        "base_occupancy": max(1, int(base_occupancy or 2)),
        "extra_adult_price": round(max(0.0, float(extra_adult_price or 0)), 2),
        "extra_child_price": round(max(0.0, float(extra_child_price or 0)), 2),
        "tax_included": safe_bool(tax_included),
        "tax_rate": round(max(0.0, min(100.0, float(tax_rate or 0))), 2),
        "is_active": safe_bool(is_active),
        "eligible_roles": eligible_roles or [],
        "included_amenities": included_amenities or [],
        "updated_at": now_utc(),
    }
    register_action(
        prop_id=prop_id,
        entity_type="rate_plan",
        entity_id=rate_plan_id,
        action="create",
        summary=f"Plan tarifario '{clean_name}' creado — ${base_rate_value:.2f} ({payload['base_occupancy']} huéspedes base)",
        changed_by=changed_by,
        metadata={"name": clean_name, "base_rate": base_rate_value, "currency": payload.get("currency", "USD"),
                  "base_occupancy": payload['base_occupancy'], "extra_adult_price": payload['extra_adult_price']},
    )
    return db.rate_plans.find_one_and_update(
        {"rate_plan_id": rate_plan_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0},
    )


def update_rate_plan(
    rate_plan_id: str,
    *,
    name: str,
    description: str,
    base_rate: Any,
    currency: str,
    room_type_id: str = "",
    base_occupancy: int = 2,
    extra_adult_price: float = 0.0,
    extra_child_price: float = 0.0,
    tax_included: Any = False,
    tax_rate: float = 0.0,
    is_active: Any = True,
    eligible_roles: list[str] | None = None,
    included_amenities: list[str] | None = None,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    db = get_database()
    existing = db.rate_plans.find_one({"rate_plan_id": rate_plan_id}, {"_id": 0, "prop_id": 1})
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    error = _validate_rate_plan(prop_id, name, base_rate, rate_plan_id=rate_plan_id)
    if error:
        raise ValueError(error)

    payload = {
        "name": clean_text(name),
        "description": clean_text(description),
        "room_type_id": clean_text(room_type_id),
        "base_rate": round(float(base_rate), 2),
        "currency": clean_text(currency) or "USD",
        "base_occupancy": max(1, int(base_occupancy or 2)),
        "extra_adult_price": round(max(0.0, float(extra_adult_price or 0)), 2),
        "extra_child_price": round(max(0.0, float(extra_child_price or 0)), 2),
        "tax_included": safe_bool(tax_included),
        "tax_rate": round(max(0.0, min(100.0, float(tax_rate or 0))), 2),
        "is_active": safe_bool(is_active),
        "eligible_roles": eligible_roles if eligible_roles is not None else [],
        "included_amenities": included_amenities or [],
        "updated_at": now_utc(),
    }
    register_action(
        prop_id=prop_id,
        entity_type="rate_plan",
        entity_id=rate_plan_id,
        action="update",
        summary=f"Plan tarifario '{clean_name}' actualizado — ${payload.get('base_rate', 0):.2f}",
        changed_by=changed_by,
        metadata={"name": clean_name},
    )
    return db.rate_plans.find_one_and_update(
        {"rate_plan_id": rate_plan_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER, projection={"_id": 0},
    )


def delete_rate_plan(rate_plan_id: str, changed_by: str = "system") -> dict[str, Any] | None:
    db = get_database()
    existing = db.rate_plans.find_one(
        {"rate_plan_id": rate_plan_id},
        {"_id": 0, "prop_id": 1, "name": 1},
    )
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    today = local_today()
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

    plan_name = existing.get("name", rate_plan_id)
    db.rate_plans.delete_one({"rate_plan_id": rate_plan_id})
    db.hotel_rate_calendar.delete_many({"rate_plan_id": rate_plan_id})
    db.rate_rules.delete_many({"rate_plan_id": rate_plan_id})
    register_action(
        prop_id=prop_id,
        entity_type="rate_plan",
        entity_id=rate_plan_id,
        action="delete",
        summary=f"Plan tarifario '{plan_name}' eliminado",
        changed_by=changed_by,
    )
    return {"rate_plan_id": rate_plan_id, "prop_id": prop_id, "deleted": True}


def list_rate_plans_for_prop(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    return _rate_plans_for_prop(prop_id, limit=limit)


def filter_eligible_plans(
    plans: list[dict[str, Any]],
    user_role: str | None = None,
) -> list[dict[str, Any]]:
    """Filter rate plans based on user role eligibility.

    - If a plan has eligible_roles=[], it's available to ALL users (no restriction).
    - If a plan has specific roles (e.g. ["corporate", "partner"]), only users
      with primary_role in that list can see it.
    - Super admin always sees everything.
    """
    if not user_role or user_role == "super_admin":
        return plans
    filtered: list[dict[str, Any]] = []
    for plan in plans:
        eligible = plan.get("eligible_roles") or []
        if not eligible:
            # No restriction → visible to everyone
            filtered.append(plan)
        elif user_role in eligible:
            filtered.append(plan)
    return filtered


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
    db = get_database()
    detail["room_types"] = list(
        db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
        .sort([("name", 1)])
    )
    return detail


def _promotion_campaigns_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.promotion_campaigns.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("end_date", 1)])
        .limit(limit)
    )


def _coupon_codes_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.coupon_codes.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("coupon_code", 1)])
        .limit(limit)
    )


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
