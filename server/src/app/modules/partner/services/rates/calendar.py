"""Rate calendar: hotel_rate_calendar single-entry and batch operations."""

from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc, safe_bool, safe_positive_int
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def save_rate_calendar_entry(
    prop_id: int,
    *,
    rate_plan_id: str,
    date: str,
    rate_amount: Any,
    min_stay_nights: Any,
    is_closed: Any = False,
    changed_by: str = "system",
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
    plan_doc = db.rate_plans.find_one({"prop_id": prop_id, "rate_plan_id": clean_rate_plan_id}, {"_id": 0, "name": 1})
    plan_name = plan_doc.get("name", clean_rate_plan_id) if plan_doc else clean_rate_plan_id
    register_action(
        prop_id=prop_id,
        entity_type="rate_calendar",
        entity_id=f"{clean_rate_plan_id}_{clean_date}",
        action="update",
        summary=f"Tarifa '{plan_name}' para {clean_date}: ${rate_amount_value:.2f}",
        changed_by=changed_by,
        metadata={"rate_plan_id": clean_rate_plan_id, "date": clean_date, "rate_amount": rate_amount_value},
    )
    return db.hotel_rate_calendar.find_one_and_update(
        {"prop_id": prop_id, "rate_plan_id": clean_rate_plan_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0},
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
    changed_by: str = "system",
) -> dict[str, Any]:
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

    try:
        rate_value = float(rate_amount or 0)
    except (TypeError, ValueError):
        raise ValueError("Debe indicar un valor de tarifa válido.") from None
    if rate_value <= 0:
        raise ValueError("La tarifa debe ser mayor que 0.")
    if rate_value > 99999.99:
        raise ValueError("La tarifa no puede superar 99999.99.")

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
        if only_weekends and cur.weekday() not in (5, 6):
            cur += timedelta(days=1)
            continue

        date_str = cur.isoformat()
        payload: dict[str, Any] = {
            "prop_id": prop_id, "rate_plan_id": clean_plan_id,
            "date": date_str, "rate_amount": round(rate_value, 2),
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

    plan_doc = db.rate_plans.find_one({"prop_id": prop_id, "rate_plan_id": clean_plan_id}, {"_id": 0, "name": 1})
    plan_name = plan_doc.get("name", clean_plan_id) if plan_doc else clean_plan_id
    register_action(
        prop_id=prop_id,
        entity_type="rate_calendar",
        entity_id=f"{clean_plan_id}_batch_{clean_start}_{clean_end}",
        action="batch_update",
        summary=f"Actualización masiva de tarifas '{plan_name}': {affected} días ({clean_start} → {clean_end})",
        changed_by=changed_by,
        metadata={"rate_plan_id": clean_plan_id, "start_date": clean_start, "end_date": clean_end, "affected_days": affected, "rate_amount": round(rate_value, 2)},
    )
    return {"affected_days": affected, "start_date": clean_start, "end_date": clean_end, "rate_plan_id": clean_plan_id}
