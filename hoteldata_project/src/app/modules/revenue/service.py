from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid

from src.database.connection import get_database
from src.app.modules.revenue.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="revenue",
        status="partial",
        description="Modulo de analytics y revenue con consulta analitica y operacion basica de tarifas y promociones.",
    )


def ensure_revenue_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    for name in ("rate_plans", "hotel_rate_calendar", "rate_rules", "promotion_campaigns", "coupon_codes"):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs = {
        "rate_plans": [
            ("rate_plan_id_1", db.rate_plans.create_index([("rate_plan_id", 1)], unique=True)),
            ("prop_id_1", db.rate_plans.create_index("prop_id")),
            ("is_active_1", db.rate_plans.create_index("is_active")),
        ],
        "hotel_rate_calendar": [
            ("prop_plan_date", db.hotel_rate_calendar.create_index([("prop_id", 1), ("rate_plan_id", 1), ("date", 1)], unique=True)),
            ("date_1", db.hotel_rate_calendar.create_index("date")),
        ],
        "rate_rules": [
            ("rule_id_1", db.rate_rules.create_index([("rule_id", 1)], unique=True)),
            ("rate_plan_id_1", db.rate_rules.create_index("rate_plan_id")),
            ("prop_id_1", db.rate_rules.create_index("prop_id")),
        ],
        "promotion_campaigns": [
            ("campaign_id_1", db.promotion_campaigns.create_index([("campaign_id", 1)], unique=True)),
            ("prop_id_1", db.promotion_campaigns.create_index("prop_id")),
            ("is_active_1", db.promotion_campaigns.create_index("is_active")),
        ],
        "coupon_codes": [
            ("coupon_code_1", db.coupon_codes.create_index([("coupon_code", 1)], unique=True)),
            ("campaign_id_1", db.coupon_codes.create_index("campaign_id")),
        ],
    }
    for indexes in index_specs.values():
        for label, name in indexes:
            created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}


def _active_fact_collection() -> tuple[Collection, str]:
    db = get_database()
    if db.fact_hotel_reservations.estimated_document_count() > 0:
        return db.fact_hotel_reservations, "fact_hotel_reservations"
    return db.fact_hotel_events, "fact_hotel_events"


def _money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.2f}"


def _number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.{decimals}f}"


def _now() -> datetime:
    return datetime.now(UTC)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    text = _clean_text(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    text = _clean_text(value)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _safe_bool(value: Any) -> bool:
    return _clean_text(value).lower() in {"1", "true", "on", "yes", "si"}


def _slugify(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "item"


def _hotel_label(prop_id: int) -> str:
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0, "display_name": 1, "hotel_name": 1, "hotel_label": 1})
    if not hotel:
        return f"Hotel Partner {prop_id}"
    return hotel.get("display_name") or hotel.get("hotel_name") or hotel.get("hotel_label") or f"Hotel Partner {prop_id}"


def _lookup_map(collection_name: str, id_field: str, label_fields: list[str], ids: list[Any]) -> dict[Any, str]:
    if not ids:
        return {}
    db = get_database()
    projection = {"_id": 0, id_field: 1}
    for field in label_fields:
        projection[field] = 1
    lookup = {}
    for item in db[collection_name].find({id_field: {"$in": ids}}, projection):
        label = None
        for field in label_fields:
            label = item.get(field)
            if label:
                break
        lookup[item.get(id_field)] = label or str(item.get(id_field))
    return lookup


def reservations_overview() -> dict[str, Any]:
    collection, source_collection = _active_fact_collection()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
                "avg_price": {"$avg": "$price_usd"},
            }
        }
    ]
    totals = next(collection.aggregate(pipeline), None) or {}
    return {
        "source_collection": source_collection,
        "total_events": int(totals.get("total_events") or 0),
        "reservations": int(totals.get("reservations") or 0),
        "clicks": int(totals.get("clicks") or 0),
        "gross_revenue": float(totals.get("gross_revenue") or 0.0),
        "gross_revenue_label": _money(totals.get("gross_revenue") or 0.0),
        "avg_price": totals.get("avg_price"),
        "avg_price_label": _money(totals.get("avg_price")) if totals.get("avg_price") is not None else "N/D",
    }


def conversion_overview() -> dict[str, Any]:
    summary = reservations_overview()
    total_events = summary["total_events"]
    clicks = summary["clicks"]
    reservations = summary["reservations"]
    click_rate = round((clicks / total_events) * 100, 2) if total_events else 0.0
    reservation_rate = round((reservations / total_events) * 100, 2) if total_events else 0.0
    abandonment = round(((total_events - reservations) / total_events) * 100, 2) if total_events else 0.0
    post_click_conversion = round((reservations / clicks) * 100, 2) if clicks else 0.0
    return {
        **summary,
        "click_rate": click_rate,
        "reservation_rate": reservation_rate,
        "abandonment_rate": abandonment,
        "post_click_conversion": post_click_conversion,
    }


def revenue_overview(limit: int = 12) -> dict[str, Any]:
    collection, source_collection = _active_fact_collection()
    hotel_pipeline = [
        {
            "$group": {
                "_id": "$prop_id",
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
                "avg_price": {"$avg": "$price_usd"},
                "reservations": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
        {"$sort": {"gross_revenue": -1, "reservations": -1}},
        {"$limit": limit},
    ]
    destination_pipeline = [
        {
            "$group": {
                "_id": "$srch_destination_id",
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
                "avg_price": {"$avg": "$price_usd"},
                "reservations": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
        {"$sort": {"gross_revenue": -1, "reservations": -1}},
        {"$limit": limit},
    ]
    hotels = list(collection.aggregate(hotel_pipeline, allowDiskUse=True))
    destinations = list(collection.aggregate(destination_pipeline, allowDiskUse=True))
    hotel_labels = _lookup_map("dim_hotels", "prop_id", ["display_name", "hotel_name", "hotel_label"], [row["_id"] for row in hotels if row.get("_id") is not None])
    destination_labels = _lookup_map("dim_destinations", "srch_destination_id", ["destination_display_name", "destination_name", "destination_label"], [row["_id"] for row in destinations if row.get("_id") is not None])
    return {
        "source_collection": source_collection,
        "hotels": [
            {
                "label": hotel_labels.get(row["_id"], f"Hotel Partner {row['_id']}"),
                "prop_id": row["_id"],
                "gross_revenue": float(row.get("gross_revenue") or 0.0),
                "gross_revenue_label": _money(row.get("gross_revenue") or 0.0),
                "avg_price_label": _money(row.get("avg_price")) if row.get("avg_price") is not None else "N/D",
                "reservations": int(row.get("reservations") or 0),
            }
            for row in hotels if row.get("_id") is not None
        ],
        "destinations": [
            {
                "label": destination_labels.get(row["_id"], f"Destino {row['_id']}"),
                "srch_destination_id": row["_id"],
                "gross_revenue": float(row.get("gross_revenue") or 0.0),
                "gross_revenue_label": _money(row.get("gross_revenue") or 0.0),
                "avg_price_label": _money(row.get("avg_price")) if row.get("avg_price") is not None else "N/D",
                "reservations": int(row.get("reservations") or 0),
            }
            for row in destinations if row.get("_id") is not None
        ],
        "summary": reservations_overview(),
    }


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


def rate_plans_overview(limit: int = 60) -> dict[str, Any]:
    ensure_revenue_collections()
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
    ensure_revenue_collections()
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


def hotel_rates_overview(prop_id: int, limit: int = 90) -> dict[str, Any]:
    ensure_revenue_collections()
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
    ensure_revenue_collections()
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


def promotions_management_overview(limit: int = 60) -> dict[str, Any]:
    ensure_revenue_collections()
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
    ensure_revenue_collections()
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


def visitor_markets_overview(limit: int = 12) -> dict[str, Any]:
    collection, source_collection = _active_fact_collection()
    country_pipeline = [
        {
            "$group": {
                "_id": "$visitor_location_country_id",
                "events": {"$sum": 1},
                "reservations": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    site_pipeline = [
        {
            "$group": {
                "_id": "$site_id",
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
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    countries = list(collection.aggregate(country_pipeline, allowDiskUse=True))
    sites = list(collection.aggregate(site_pipeline, allowDiskUse=True))
    country_labels = _lookup_map(
        "dim_visitor_countries",
        "visitor_location_country_id",
        ["country_display_name", "country_name", "visitor_country_label"],
        [row["_id"] for row in countries if row.get("_id") is not None],
    )
    site_labels = _lookup_map(
        "dim_sites",
        "site_id",
        ["site_display_name", "site_name", "site_label"],
        [row["_id"] for row in sites if row.get("_id") is not None],
    )
    return {
        "source_collection": source_collection,
        "countries": [
            {
                "label": country_labels.get(row["_id"], f"Mercado visitante {row['_id']}"),
                "technical_id": row["_id"],
                "events": int(row.get("events") or 0),
                "reservations": int(row.get("reservations") or 0),
            }
            for row in countries if row.get("_id") is not None
        ],
        "sites": [
            {
                "label": site_labels.get(row["_id"], f"Canal Expedia {row['_id']}"),
                "technical_id": row["_id"],
                "events": int(row.get("events") or 0),
                "clicks": int(row.get("clicks") or 0),
                "reservations": int(row.get("reservations") or 0),
            }
            for row in sites if row.get("_id") is not None
        ],
    }
