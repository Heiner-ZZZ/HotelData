"""Rate plans: CRUD for rate_plans and combined hotel rates data."""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta
from typing import Any

from pymongo import ReturnDocument

from src.app.core.timezone import local_today
from src.app.modules.partner.services._common import (
    clean_text,
    iso_label,
    money,
    now_utc,
    safe_bool,
    slugify,
)
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


# ── Tarifa base mínima (configurable en system_config) ─────────────────────
DEFAULT_MIN_BASE_RATE = 10.0


def get_min_base_rate() -> float:
    """Umbral mínimo de tarifa base de un plan tarifario.

    Configurable por plataforma en ``system_config._id='global'.min_base_rate``
    (doc singleton del módulo global_settings). Si el campo no existe o el
    valor no es numérico, cae al default de $10 — nunca bloquea con un valor
    inválido.
    """
    db = get_database()
    config = db.system_config.find_one({"_id": "global"}, {"min_base_rate": 1, "_id": 0})
    try:
        value = float((config or {}).get("min_base_rate") or DEFAULT_MIN_BASE_RATE)
    except (TypeError, ValueError):
        value = DEFAULT_MIN_BASE_RATE
    return value if value > 0 else DEFAULT_MIN_BASE_RATE


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
        # Backfill applicable_room_types for legacy documents (Gap 1 migration)
        if "applicable_room_types" not in item:
            rt = item.get("room_type_id", "")
            item["applicable_room_types"] = [rt] if rt else []
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
        min_rate = get_min_base_rate()
        if rate < min_rate:
            return f"base_rate debe ser mayor o igual a {min_rate:g}."
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
    applicable_room_types: list[str] | None = None,
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

    # Resolve applicable_room_types: new field takes priority, fall back to legacy room_type_id
    resolved_room_types: list[str] = []
    if applicable_room_types:
        resolved_room_types = [clean_text(rt) for rt in applicable_room_types if clean_text(rt)]
    elif room_type_id:
        resolved_room_types = [clean_text(room_type_id)]
    # Backfill room_type_id for backward compat (first applicable type, or empty)
    backfill_room_type_id = resolved_room_types[0] if resolved_room_types else ""

    payload = {
        "rate_plan_id": rate_plan_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": clean_text(description),
        "room_type_id": backfill_room_type_id,
        "applicable_room_types": resolved_room_types,
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
    applicable_room_types: list[str] | None = None,
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

    clean_name = clean_text(name)

    # Resolve applicable_room_types: new field takes priority, fall back to legacy room_type_id
    resolved_room_types: list[str] = []
    if applicable_room_types:
        resolved_room_types = [clean_text(rt) for rt in applicable_room_types if clean_text(rt)]
    elif room_type_id:
        resolved_room_types = [clean_text(room_type_id)]
    backfill_room_type_id = resolved_room_types[0] if resolved_room_types else ""

    payload = {
        "name": clean_name,
        "description": clean_text(description),
        "room_type_id": backfill_room_type_id,
        "applicable_room_types": resolved_room_types,
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
    detail["min_base_rate"] = get_min_base_rate()
    detail["calendar"] = _rate_calendar_for_prop(prop_id)
    detail["rate_rules"] = _rate_rules_for_prop(prop_id)
    detail["promotions"] = _promotion_campaigns_for_prop(prop_id)
    detail["coupon_codes"] = _coupon_codes_for_prop(prop_id)
    db = get_database()
    detail["room_types"] = list(
        db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
        .sort([("name", 1)])
    )
    detail["rate_coverage"] = _rate_coverage_gap(prop_id)
    return detail


def _rate_coverage_gap(prop_id: int) -> dict[str, Any] | None:
    """Hueco tarifas-vs-inventario para el banner del overview.

    Las noches con habitaciones disponibles pero SIN tarifa abierta no se
    pueden vender en el search público (exige inventario Y tarifa por noche).
    Devuelve el rango faltante (conteo exacto + fechas para pre-cargar
    "Generar calendario") o ``None`` si no hay hueco accionable.

    - ``rate_last_date``: última fecha con tarifa ABIERTA (is_closed != True).
    - ``inventory_last_date``: última fecha con inventario.
    - ``gap_nights``: noches desde el día siguiente a la última tarifa (o hoy
      si no hay tarifas) hasta el último inventario, con disponible > 0.
    """
    db = get_database()
    today = local_today()
    rate_last = db.hotel_rate_calendar.find_one(
        {"prop_id": prop_id, "is_closed": {"$ne": True}},
        sort=[("date", -1)],
    )
    inv_last = db.room_inventory_calendar.find_one(
        {"prop_id": prop_id, "is_deleted": {"$ne": True}},
        sort=[("date", -1)],
    )
    if inv_last is None or not inv_last.get("date"):
        return None
    inv_last_date = str(inv_last["date"])
    if rate_last and rate_last.get("date"):
        rate_last_date = str(rate_last["date"])
        start = max((date_type.fromisoformat(rate_last_date) + timedelta(days=1)).isoformat(), today)
    else:
        rate_last_date = None
        start = today
    if start > inv_last_date:
        return None
    avail_dates = sorted(
        db.room_inventory_calendar.distinct(
            "date",
            {
                "prop_id": prop_id,
                "is_deleted": {"$ne": True},
                "available_rooms": {"$gt": 0},
                "date": {"$gte": start, "$lte": inv_last_date},
            },
        )
    )
    if not avail_dates:
        return None
    return {
        "rate_last_date": rate_last_date,
        "inventory_last_date": inv_last_date,
        "gap_nights": len(avail_dates),
        "gap_start": avail_dates[0],
        "gap_end": avail_dates[-1],
    }


def _promotion_campaigns_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.promotion_campaigns.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("end_date", 1)])
        .limit(limit)
    )


def _coupon_codes_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    # Solo códigos activos: los retirados (is_deleted) son trazabilidad, no
    # se ofrecen a los hoteles.
    return list(
        db.coupon_codes.find({"prop_id": prop_id, "is_deleted": {"$ne": True}}, {"_id": 0})
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
