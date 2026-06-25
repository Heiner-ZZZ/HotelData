"""Seasonal rules and calendar generation from base prices + rules."""

from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any

from src.app.modules.partner.services._common import clean_text, iso_label, now_utc, safe_bool, safe_positive_int, slugify
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def create_seasonal_rule(
    prop_id: int,
    *,
    rate_plan_id: str,
    name: str,
    start_date: str,
    end_date: str,
    price_override: Any,
) -> dict[str, Any] | None:
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
        "rule_id": rule_id, "prop_id": prop_id,
        "rate_plan_id": clean_plan_id, "name": clean_name,
        "start_date": clean_start, "end_date": clean_end,
        "price_override": override_value, "updated_at": now_utc(),
    }
    return db.rate_rules.find_one_and_update(
        {"rule_id": rule_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0},
    )


def delete_seasonal_rule(rule_id: str) -> dict[str, Any] | None:
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


def generate_calendar_from_rules(
    prop_id: int,
    *,
    rate_plan_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
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

    plan_query: dict[str, Any] = {"prop_id": prop_id}
    if rate_plan_id:
        plan_query["rate_plan_id"] = rate_plan_id
    plans = list(db.rate_plans.find(plan_query, {"_id": 0}))

    if not plans:
        return {"plans_processed": 0, "entries_generated": 0, "message": "No hay planes tarifarios para procesar."}

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
            continue
        plan_rules = rules_by_plan.get(plan_id, [])
        plan_count += 1

        cur = range_start
        while cur <= range_end:
            date_str = cur.isoformat()

            existing = db.hotel_rate_calendar.find_one(
                {"prop_id": prop_id, "rate_plan_id": plan_id, "date": date_str},
                {"_id": 0, "rate_amount": 1},
            )
            if existing is not None:
                cur += timedelta(days=1)
                continue

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
                        "prop_id": prop_id, "rate_plan_id": plan_id,
                        "date": date_str, "rate_amount": round(price, 2),
                        "source": "generated", "updated_at": now,
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
