from __future__ import annotations

from typing import Any

import secrets
import string

from pymongo import ReturnDocument

from src.app.modules.revenue.services.common import (
    _active_fact_collection,
    _clean_text,
    _hotel_label,
    _money,
    _now,
    _safe_bool,
    _safe_int,
    _slugify,
)
from src.database.connection import get_database


def promotions_overview() -> dict[str, Any]:
    collection, source_collection = _active_fact_collection()
    pipeline = [
        {
            "$group": {
                "_id": {
                    "$cond": [
                        {"$or": [{"$eq": ["$promotion_flag", 1]}, {"$eq": ["$promotion_flag", True]}]},
                        "with_promotion",
                        "without_promotion",
                    ]
                },
                "events": {"$sum": 1},
                "clicks": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
                "reservations": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
                "avg_price": {"$avg": "$price_usd"},
            }
        }
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    items = []
    for row in rows:
        events = int(row.get("events") or 0)
        clicks = int(row.get("clicks") or 0)
        reservations = int(row.get("reservations") or 0)
        items.append(
            {
                "segment": "Con promoción" if row["_id"] == "with_promotion" else "Sin promoción",
                "events": events,
                "clicks": clicks,
                "reservations": reservations,
                "click_rate": round((clicks / events) * 100, 2) if events else 0.0,
                "reservation_rate": round((reservations / events) * 100, 2) if events else 0.0,
                "gross_revenue_label": _money(row.get("gross_revenue") or 0.0),
                "avg_price_label": _money(row.get("avg_price")) if row.get("avg_price") is not None else "N/D",
            }
        )
    items.sort(key=lambda item: item["segment"])
    return {"source_collection": source_collection, "items": items}


def promotions_management_overview(limit: int = 60) -> dict[str, Any]:
    db = get_database()
    campaigns = list(db.promotion_campaigns.find({}, {"_id": 0}).sort([("updated_at", -1)]).limit(limit))
    coupons = list(db.coupon_codes.find({}, {"_id": 0}).sort([("updated_at", -1)]).limit(limit))
    coupon_lookup: dict[str, list[dict[str, Any]]] = {}
    for coupon in coupons:
        coupon_lookup.setdefault(coupon["campaign_id"], []).append(coupon)
    for campaign in campaigns:
        campaign["hotel_label"] = _hotel_label(campaign["prop_id"])
        campaign["discount_percent_label"] = f"{campaign.get('discount_percent', 0)}%"
        campaign["coupons"] = coupon_lookup.get(campaign["campaign_id"], [])
    return {
        "campaigns": campaigns,
        "total_campaigns": db.promotion_campaigns.count_documents({}),
        "impact": promotions_overview(),
    }


def _generate_coupon_codes(
    db: Any,
    campaign_id: str,
    prop_id: int,
    discount_percent: int,
    is_active: bool,
    count: int,
) -> list[str]:
    """Generate N unique coupon codes for a campaign."""
    alphabet = string.ascii_uppercase + string.digits
    codes: list[str] = []
    existing = {doc["coupon_code"] for doc in db.coupon_codes.find({}, {"coupon_code": 1})}
    now_val = _now()
    attempts = 0
    while len(codes) < count and attempts < count * 10:
        length = 8 + (len(codes) % 5)  # 8-12 chars alternating
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        if code not in existing:
            existing.add(code)
            codes.append(code)
            db.coupon_codes.insert_one(
                {
                    "coupon_code": code,
                    "campaign_id": campaign_id,
                    "prop_id": prop_id,
                    "discount_percent": discount_percent,
                    "is_active": is_active,
                    "used": False,
                    "used_at": None,
                    "created_at": now_val,
                    "updated_at": now_val,
                }
            )
        attempts += 1
    return codes


def update_promotion_campaign(
    campaign_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    discount_percent: Any = None,
    start_date: str | None = None,
    end_date: str | None = None,
    is_active: Any = None,
) -> dict[str, Any]:
    """RF-006: Editar campaña promocional."""
    db = get_database()
    existing = db.promotion_campaigns.find_one({"campaign_id": campaign_id}, {"_id": 0})
    if not existing:
        raise ValueError(f"Campaña {campaign_id} no encontrada.")

    update: dict[str, Any] = {"updated_at": _now()}

    if name is not None:
        clean_name = _clean_text(name)
        if not clean_name:
            raise ValueError("Debe indicar el nombre de la promoción.")
        update["name"] = clean_name

    if description is not None:
        update["description"] = _clean_text(description)

    if discount_percent is not None:
        discount_value = _safe_int(discount_percent, 0)
        if discount_value < 1 or discount_value > 100:
            raise ValueError("El descuento debe ser entre 1% y 100%.")
        update["discount_percent"] = discount_value

    if start_date is not None:
        update["start_date"] = _clean_text(start_date)

    if end_date is not None:
        update["end_date"] = _clean_text(end_date)

    if is_active is not None:
        active = _safe_bool(is_active)
        update["is_active"] = active
        # Sincronizar cupones con el estado de la campaña
        db.coupon_codes.update_many(
            {"campaign_id": campaign_id},
            {"$set": {"is_active": active, "updated_at": _now()}},
        )

    db.promotion_campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$set": update},
    )
    return db.promotion_campaigns.find_one(
        {"campaign_id": campaign_id},
        {"_id": 0},
    )


def toggle_promotion_campaign(campaign_id: str) -> dict[str, Any]:
    """RF-003: Activar/desactivar campaña."""
    db = get_database()
    existing = db.promotion_campaigns.find_one({"campaign_id": campaign_id}, {"_id": 0, "is_active": 1})
    if not existing:
        raise ValueError(f"Campaña {campaign_id} no encontrada.")
    new_active = not existing.get("is_active", False)
    db.promotion_campaigns.update_one(
        {"campaign_id": campaign_id},
        {"$set": {"is_active": new_active, "updated_at": _now()}},
    )
    # Sincronizar cupones
    db.coupon_codes.update_many(
        {"campaign_id": campaign_id},
        {"$set": {"is_active": new_active, "updated_at": _now()}},
    )
    return {
        "campaign_id": campaign_id,
        "is_active": new_active,
    }


def list_property_campaigns(prop_id: int) -> dict[str, Any]:
    """RF-004: Listar campañas por propiedad con conteo de cupones."""
    db = get_database()
    campaigns = list(
        db.promotion_campaigns.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("updated_at", -1)])
    )
    # Agregar conteo de cupones por campaña
    for campaign in campaigns:
        cid = campaign["campaign_id"]
        total = db.coupon_codes.count_documents({"campaign_id": cid})
        used = db.coupon_codes.count_documents({"campaign_id": cid, "used": True})
        campaign["coupon_total"] = total
        campaign["coupon_used"] = used
        campaign["coupon_available"] = total - used
        campaign["discount_percent_label"] = f"{campaign.get('discount_percent', 0)}%"
        campaign["hotel_label"] = _hotel_label(prop_id)
    return {
        "campaigns": campaigns,
        "total": len(campaigns),
    }


def create_promotion_campaign(
    *,
    prop_id: Any,
    name: str,
    description: str,
    discount_percent: Any,
    start_date: str,
    end_date: str,
    coupon_count: int = 10,
    coupon_code: str = "",
    is_active: Any = True,
) -> dict[str, Any]:
    db = get_database()
    prop_id_value = _safe_int(prop_id, 0)
    if prop_id_value <= 0:
        raise ValueError("Debe indicar un prop_id válido.")
    clean_name = _clean_text(name)
    if not clean_name:
        raise ValueError("Debe indicar el nombre de la promoción.")

    # RF-005: Validar descuento 1-100%
    discount_value = _safe_int(discount_percent, 0)
    if discount_value < 1 or discount_value > 100:
        raise ValueError("El descuento debe ser entre 1% y 100%.")

    # RF-002: Limitar coupon_count máximo 1000
    coupon_count_value = max(1, min(int(coupon_count or 10), 1000))

    campaign_id = f"PC-{prop_id_value}-{_slugify(clean_name)}"
    payload = {
        "campaign_id": campaign_id,
        "prop_id": prop_id_value,
        "name": clean_name,
        "description": _clean_text(description),
        "discount_percent": discount_value,
        "start_date": _clean_text(start_date),
        "end_date": _clean_text(end_date),
        "coupon_count": coupon_count_value,
        "coupons_used": 0,
        "is_active": _safe_bool(is_active),
        "updated_at": _now(),
    }
    document = db.promotion_campaigns.find_one_and_update(
        {"campaign_id": campaign_id},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )

    # RF-002: Generar N códigos de cupón únicos
    _generate_coupon_codes(db, campaign_id, prop_id_value, discount_value, _safe_bool(is_active), coupon_count_value)

    # Compatibilidad: si se pasa coupon_code individual, también se crea
    clean_coupon = _clean_text(coupon_code)
    if clean_coupon:
        db.coupon_codes.find_one_and_update(
            {"coupon_code": clean_coupon.upper()},
            {
                "$set": {
                    "coupon_code": clean_coupon.upper(),
                    "campaign_id": campaign_id,
                    "prop_id": prop_id_value,
                    "discount_percent": discount_value,
                    "is_active": _safe_bool(is_active),
                    "updated_at": _now(),
                },
                "$setOnInsert": {"created_at": _now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    return {**document, "coupons_generated": coupon_count_value}
