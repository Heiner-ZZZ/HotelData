from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.revenue.services.common import (
    _clean_text,
    _hotel_label,
    _money,
    _now,
    _safe_bool,
    _safe_float,
    _safe_int,
)
from src.database.connection import get_database


def hotel_rates_overview(prop_id: int, limit: int = 90) -> dict[str, Any]:
    db = get_database()
    rate_plans = list(db.rate_plans.find({"prop_id": prop_id}, {"_id": 0}).sort([("name", 1)]).limit(50))
    calendar = list(
        db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("rate_plan_id", 1)])
        .limit(limit)
    )
    plan_lookup = {item["rate_plan_id"]: item for item in rate_plans}
    for item in rate_plans:
        item["base_rate_label"] = _money(item.get("base_rate"))
    for item in calendar:
        item["plan_name"] = plan_lookup.get(item["rate_plan_id"], {}).get("name", item["rate_plan_id"])
        item["rate_amount_label"] = _money(item.get("rate_amount"))
    return {
        "prop_id": prop_id,
        "hotel_label": _hotel_label(prop_id),
        "rate_plans": rate_plans,
        "calendar": calendar,
    }


def save_hotel_rate(
    *,
    prop_id: int,
    rate_plan_id: str,
    date: str,
    rate_amount: Any,
    min_stay_nights: Any,
    is_closed: Any = False,
) -> dict[str, Any]:
    db = get_database()
    clean_rate_plan_id = _clean_text(rate_plan_id)
    clean_date = _clean_text(date)
    if not clean_rate_plan_id or not clean_date:
        raise ValueError("Debe indicar rate_plan_id y fecha.")
    if db.rate_plans.find_one({"prop_id": prop_id, "rate_plan_id": clean_rate_plan_id}, {"_id": 1}) is None:
        raise ValueError("El rate_plan_id no existe para este hotel.")
    payload = {
        "prop_id": prop_id,
        "rate_plan_id": clean_rate_plan_id,
        "date": clean_date,
        "rate_amount": max(_safe_float(rate_amount, 0.0), 0.0),
        "min_stay_nights": max(_safe_int(min_stay_nights, 1), 1),
        "is_closed": _safe_bool(is_closed),
        "updated_at": _now(),
    }
    return db.hotel_rate_calendar.find_one_and_update(
        {"prop_id": prop_id, "rate_plan_id": clean_rate_plan_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
