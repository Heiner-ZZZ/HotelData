"""Dashboard sub-domain: operational flags, management reports, properties dashboard.

Cross-cutting read layer that aggregates data from every other partner
sub-domain to feed the management UI and reports endpoints.
"""
from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import (
    active_fact_collection,
    destination_display_name,
    hotel_display_name,
    money,
    now_utc,
)
from src.app.modules.partner.services.properties.performance import (
    performance_for_prop as _performance_for_prop,
    property_yield_score as _property_yield_score,
)
from src.app.modules.partner.services.properties import list_partner_hotels
from src.database.connection import get_database


def _collection_count(collection_name: str, filters: dict[str, Any] | None = None) -> int:
    db = get_database()
    return int(db[collection_name].count_documents(filters or {}))


def _operational_flags(prop_id: int) -> dict[str, Any]:
    db = get_database()
    policies_count = int(db.hotel_policies.count_documents({"prop_id": prop_id}))
    room_types_count = int(db.room_types.count_documents({"prop_id": prop_id}))
    hotel_rooms_count = int(db.hotel_rooms.count_documents({"prop_id": prop_id}))
    rate_plans_count = int(db.rate_plans.count_documents({"prop_id": prop_id}))
    inventory_count = int(db.room_inventory_calendar.count_documents({"prop_id": prop_id}))
    content_count = int(db.hotel_content_pages.count_documents({"prop_id": prop_id}))
    image_count = int(db.hotel_images.count_documents({"prop_id": prop_id}))
    promotions_count = int(db.promotion_campaigns.count_documents({"prop_id": prop_id, "is_active": True}))
    coupon_count = int(db.coupon_codes.count_documents({"prop_id": prop_id, "is_active": True}))

    policies_ready = policies_count > 0
    rooms_ready = room_types_count > 0
    rates_ready = rate_plans_count > 0
    inventory_ready = inventory_count > 0
    content_ready = content_count > 0 or image_count > 0
    images_ready = image_count > 0
    promotions_ready = promotions_count > 0 or coupon_count > 0

    score = 0
    score += 20 if policies_ready else 0
    score += 20 if rooms_ready else 0
    score += 20 if rates_ready else 0
    score += 20 if inventory_ready else 0
    score += 20 if content_ready else 0

    return {
        "policies_configured": policies_ready,
        "rooms_configured": rooms_ready,
        "rates_configured": rates_ready,
        "inventory_configured": inventory_ready,
        "content_configured": content_ready,
        "images_configured": images_ready,
        "promotions_active": promotions_ready,
        "operational_score": score,
        "counts": {
            "hotel_policies": policies_count,
            "room_types": room_types_count,
            "hotel_rooms": hotel_rooms_count,
            "rate_plans": rate_plans_count,
            "room_inventory_calendar": inventory_count,
            "hotel_content_pages": content_count,
            "hotel_images": image_count,
            "promotion_campaigns": promotions_count,
            "coupon_codes": coupon_count,
        },
    }


def _operational_dashboard_metrics() -> list[dict[str, Any]]:
    metrics = [
        ("Habitaciones configuradas", "room_types"),
        ("Habitaciones físicas", "hotel_rooms"),
        ("Días de inventario", "room_inventory_calendar"),
        ("Planes tarifarios", "rate_plans"),
        ("Tarifas calendario", "hotel_rate_calendar"),
        ("Políticas configuradas", "hotel_policies"),
        ("Contenido hotelero", "hotel_content_pages"),
        ("Imágenes", "hotel_images"),
        ("Campañas", "promotion_campaigns"),
        ("Cupones", "coupon_codes"),
    ]
    return [{"label": label, "value": _collection_count(collection_name)} for label, collection_name in metrics]


def management_property_options(limit: int = 100) -> list[dict[str, Any]]:
    from src.app.modules.partner.services.properties.metadata import profile_badge as _profile_badge

    results = list_partner_hotels("", page=1, page_size=min(max(limit, 1), 100))
    return [
        {
            "prop_id": item["prop_id"],
            "display_name": item.get("display_name") or f"Hotel {item['prop_id']}",
        }
        for item in results["items"]
    ]


def management_reports_summary() -> dict[str, Any]:
    from src.app.modules.partner.services.properties.metadata import profile_badge as _profile_badge

    db = get_database()
    collection, source_collection = active_fact_collection()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    totals_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "reservations_detected": {"$sum": {"$cond": [booked, 1, 0]}},
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
            }
        }
    ]
    totals = next(collection.aggregate(totals_pipeline, allowDiskUse=True), None) or {}

    hotel_lookup = {
        item["prop_id"]: item
        for item in db.dim_hotels.find({}, {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1, "manual_override": 1})
        if item.get("prop_id") is not None
    }
    destination_lookup = {
        item["srch_destination_id"]: item
        for item in db.dim_destinations.find({}, {"_id": 0, "srch_destination_id": 1, "destination_display_name": 1, "destination_name": 1})
        if item.get("srch_destination_id") is not None
    }
    country_lookup = {
        item["visitor_location_country_id"]: item
        for item in db.dim_visitor_countries.find({}, {"_id": 0, "visitor_location_country_id": 1, "country_display_name": 1, "country_name": 1})
        if item.get("visitor_location_country_id") is not None
    }

    top_hotels = list(
        collection.aggregate(
            [
                {"$group": {"_id": "$prop_id", "gross_revenue": {"$sum": "$reservas_brutas_usd"}, "events": {"$sum": 1}}},
                {"$sort": {"gross_revenue": -1}},
                {"$limit": 5},
            ],
            allowDiskUse=True,
        )
    )
    top_destinations = list(
        collection.aggregate(
            [
                {"$group": {"_id": "$srch_destination_id", "events": {"$sum": 1}, "gross_revenue": {"$sum": "$reservas_brutas_usd"}}},
                {"$sort": {"events": -1}},
                {"$limit": 5},
            ],
            allowDiskUse=True,
        )
    )
    top_countries = list(
        collection.aggregate(
            [
                {
                    "$group": {
                        "_id": "$visitor_location_country_id",
                        "events": {"$sum": 1},
                        "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                    }
                },
                {"$sort": {"events": -1}},
                {"$limit": 5},
            ],
            allowDiskUse=True,
        )
    )

    operational_counts = _operational_dashboard_metrics()
    return {
        "source_collection": source_collection,
        "total_events": int(totals.get("total_events") or 0),
        "reservations_detected": int(totals.get("reservations_detected") or 0),
        "gross_revenue": round(float(totals.get("gross_revenue") or 0), 2),
        "top_hotels_by_revenue": [
            {
                "prop_id": int(item["_id"]),
                "display_name": hotel_display_name(hotel_lookup.get(int(item["_id"]), {}), int(item["_id"])),
                "manual_override": bool(hotel_lookup.get(int(item["_id"]), {}).get("manual_override", False)),
                "profile_badge": _profile_badge(hotel_lookup.get(int(item["_id"]), {})),
                "gross_revenue": round(float(item.get("gross_revenue") or 0), 2),
                "events": int(item.get("events") or 0),
            }
            for item in top_hotels
            if item.get("_id") is not None
        ],
        "top_destinations": [
            {
                "srch_destination_id": int(item["_id"]),
                "label": destination_display_name(destination_lookup.get(int(item["_id"]), {}), int(item["_id"])),
                "events": int(item.get("events") or 0),
                "gross_revenue": round(float(item.get("gross_revenue") or 0), 2),
            }
            for item in top_destinations
            if item.get("_id") is not None
        ],
        "top_visitor_countries": [
            {
                "visitor_location_country_id": int(item["_id"]),
                "label": country_lookup.get(int(item["_id"]), {}).get("country_display_name")
                or country_lookup.get(int(item["_id"]), {}).get("country_name")
                or f"Mercado visitante {int(item['_id'])}",
                "events": int(item.get("events") or 0),
                "reservations": int(item.get("reservations") or 0),
            }
            for item in top_countries
            if item.get("_id") is not None
        ],
        "operational_counts": operational_counts,
    }


def _dashboard_quick_stats(db) -> dict[str, Any]:
    collection, _ = active_fact_collection()
    now = now_utc()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_searches": {"$sum": 1},
                "total_reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "total_revenue": {"$sum": "$reservas_brutas_usd"},
            }
        },
    ]
    stats = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    total_searches = int(stats["total_searches"]) if stats else 0
    total_reservations = int(stats["total_reservations"]) if stats else 0
    occupancy_rate = round((total_reservations / total_searches) * 100, 1) if total_searches else 0.0
    year, month = now.year, now.month
    date_key_start = int(f"{year}{month:02d}01")
    next_m = month + 1
    next_y = year
    if next_m > 12:
        next_m = 1
        next_y += 1
    date_key_end = int(f"{next_y}{next_m:02d}01")
    mtd = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": date_key_start, "$lt": date_key_end}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$reservas_brutas_usd"}}},
    ], allowDiskUse=True), None)
    revenue_mtd = float(mtd["revenue"]) if mtd else 0.0
    prev_m = month - 1
    prev_y = year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    prev_start = int(f"{prev_y}{prev_m:02d}01")
    prev = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": prev_start, "$lt": date_key_start}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$reservas_brutas_usd"}}},
    ], allowDiskUse=True), None)
    revenue_prev = float(prev["revenue"]) if prev else 0.0
    revenue_trend = round(((revenue_mtd - revenue_prev) / revenue_prev * 100), 1) if revenue_prev else 0.0

    # Real occupancy trend: compare current month occupancy vs previous month
    occ_current = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": date_key_start, "$lt": date_key_end}}},
        {"$group": {"_id": None, "reservations": {"$sum": {"$cond": [booked, 1, 0]}}, "searches": {"$sum": 1}}},
    ], allowDiskUse=True), None)
    occ_prev = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": prev_start, "$lt": date_key_start}}},
        {"$group": {"_id": None, "reservations": {"$sum": {"$cond": [booked, 1, 0]}}, "searches": {"$sum": 1}}},
    ], allowDiskUse=True), None)
    cur_rate = round((occ_current["reservations"] / occ_current["searches"]) * 100, 1) if occ_current and occ_current["searches"] else None
    prev_rate = round((occ_prev["reservations"] / occ_prev["searches"]) * 100, 1) if occ_prev and occ_prev["searches"] else None
    if cur_rate is not None and prev_rate is not None and prev_rate != 0:
        occupancy_trend = round(((cur_rate - prev_rate) / prev_rate) * 100, 1)
    elif cur_rate is not None and prev_rate is None:
        occupancy_trend = None
    else:
        occupancy_trend = 0.0

    pending = 0
    try:
        pending = db.booking_orders.count_documents({
            "check_in_date": now.strftime("%Y-%m-%d"),
            "status": {"$in": ["confirmed", "pending"]},
        })
    except Exception:
        pass
    health = None
    try:
        last = db.data_quality_reports.find_one(sort=[("executed_at", -1)], projection={"overall_score": 1, "_id": 0})
        if last and "overall_score" in last:
            health = int(last["overall_score"])
    except Exception:
        pass
    return {
        "occupancy_rate": occupancy_rate,
        "occupancy_trend": occupancy_trend,
        "total_revenue_mtd": round(revenue_mtd, 2),
        "revenue_trend": revenue_trend,
        "pending_checkins": pending,
        "data_health_score": health,
    }


def _dashboard_revenue_chart(db) -> list[dict[str, Any]]:
    collection, _ = active_fact_collection()
    results = list(collection.aggregate([
        {"$match": {"reserva_bool": True}},
        {"$group": {"_id": {"$floor": {"$divide": ["$date_key", 100]}}, "revenue": {"$sum": "$reservas_brutas_usd"}}},
        {"$sort": {"_id": 1}},
        {"$limit": 8},
    ], allowDiskUse=True))
    return [{"period": str(r["_id"]), "revenue": round(float(r["revenue"]), 2)} for r in results]


def _dashboard_arrivals_today(db) -> list[dict[str, Any]]:
    try:
        today = now_utc().strftime("%Y-%m-%d")
        rows = list(db.booking_orders.find({"check_in_date": today, "status": {"$in": ["confirmed", "pending"]}}, {"_id": 0}).limit(20))
        out = []
        for r in rows:
            name = r.get("guest_name", "Invitado")
            parts = name.strip().split()
            initials = "".join(p[0].upper() for p in parts[:2] if p) or "??"
            out.append({
                "guest_name": name,
                "initials": initials,
                "room_type": r.get("room_type", "Standard"),
                "nights": int(r.get("nights", 1) or 1),
                "arrival_time": r.get("arrival_time", "15:00"),
                "status_tag": r.get("booking_source", "standard"),
            })
        return out
    except Exception:
        return []


def properties_dashboard(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    quick_stats = _dashboard_quick_stats(db)
    revenue_chart = _dashboard_revenue_chart(db)
    arrivals = _dashboard_arrivals_today(db)
    props_list = list_partner_hotels(query, page=page, page_size=page_size)
    return {
        "quick_stats": quick_stats,
        "revenue_chart": revenue_chart,
        "arrivals_today": arrivals,
        "properties": props_list,
    }
