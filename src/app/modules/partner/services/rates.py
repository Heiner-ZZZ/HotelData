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
    return detail


def create_rate_plan(
    prop_id: int,
    *,
    name: str,
    description: str,
    base_rate: Any,
    currency: str,
    is_active: Any = True,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_name = clean_text(name)
    if not clean_name:
        raise ValueError("Debe ingresar el nombre del plan tarifario.")
    rate_plan_id = f"RP-{prop_id}-{slugify(clean_name)}"
    try:
        base_rate_value = max(float(base_rate or 0), 0.0)
    except (TypeError, ValueError):
        raise ValueError("Debe indicar una tarifa base válida.") from None
    payload = {
        "rate_plan_id": rate_plan_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": clean_text(description),
        "base_rate": round(base_rate_value, 2),
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
    try:
        rate_amount_value = max(float(rate_amount or 0), 0.0)
    except (TypeError, ValueError):
        raise ValueError("Debe indicar un valor de tarifa válido.") from None
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
