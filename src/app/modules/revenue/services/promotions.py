from __future__ import annotations

from typing import Any

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


def create_promotion_campaign(
    *,
    prop_id: Any,
    name: str,
    description: str,
    discount_percent: Any,
    start_date: str,
    end_date: str,
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
    campaign_id = f"PC-{prop_id_value}-{_slugify(clean_name)}"
    payload = {
        "campaign_id": campaign_id,
        "prop_id": prop_id_value,
        "name": clean_name,
        "description": _clean_text(description),
        "discount_percent": max(min(_safe_int(discount_percent, 0), 100), 0),
        "start_date": _clean_text(start_date),
        "end_date": _clean_text(end_date),
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
    clean_coupon = _clean_text(coupon_code)
    if clean_coupon:
        db.coupon_codes.find_one_and_update(
            {"coupon_code": clean_coupon.upper()},
            {
                "$set": {
                    "coupon_code": clean_coupon.upper(),
                    "campaign_id": campaign_id,
                    "prop_id": prop_id_value,
                    "discount_percent": payload["discount_percent"],
                    "is_active": payload["is_active"],
                    "updated_at": _now(),
                },
                "$setOnInsert": {"created_at": _now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    return document
