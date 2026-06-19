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
    _slugify,
)
from src.database.connection import get_database


def rate_plans_overview(limit: int = 60) -> dict[str, Any]:
    db = get_database()
    items = list(db.rate_plans.find({}, {"_id": 0}).sort([("updated_at", -1)]).limit(limit))
    for item in items:
        item["hotel_label"] = _hotel_label(item["prop_id"])
        item["base_rate_label"] = _money(item.get("base_rate"))
        updated_at = item.get("updated_at")
        item["updated_at_label"] = updated_at.isoformat() if hasattr(updated_at, "isoformat") else "N/D"
    return {"items": items, "total": db.rate_plans.count_documents({})}


def create_rate_plan(
    *,
    prop_id: Any,
    name: str,
    description: str,
    base_rate: Any,
    currency: str,
    is_active: Any = True,
) -> dict[str, Any]:
    db = get_database()
    prop_id_value = _safe_int(prop_id, 0)
    if prop_id_value <= 0:
        raise ValueError("Debe indicar un prop_id válido.")
    clean_name = _clean_text(name)
    if not clean_name:
        raise ValueError("Debe indicar el nombre del plan tarifario.")
    rate_plan_id = f"RP-{prop_id_value}-{_slugify(clean_name)}"
    payload = {
        "rate_plan_id": rate_plan_id,
        "prop_id": prop_id_value,
        "name": clean_name,
        "description": _clean_text(description),
        "base_rate": max(_safe_float(base_rate, 0.0), 0.0),
        "currency": (_clean_text(currency) or "USD").upper(),
        "is_active": _safe_bool(is_active),
        "updated_at": _now(),
    }
    document = db.rate_plans.find_one_and_update(
        {"rate_plan_id": rate_plan_id},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    db.rate_rules.find_one_and_update(
        {"rule_id": f"RR-{rate_plan_id}"},
        {
            "$set": {
                "rule_id": f"RR-{rate_plan_id}",
                "rate_plan_id": rate_plan_id,
                "prop_id": prop_id_value,
                "rule_name": "standard",
                "description": "Regla base creada automáticamente con el plan tarifario.",
                "is_active": payload["is_active"],
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return document
