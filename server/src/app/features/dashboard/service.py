from __future__ import annotations

from typing import Any

from src.database.connection import get_database


def _bool_true_condition(field_name: str) -> dict[str, Any]:
    return {"$or": [{"$eq": [f"${field_name}", 1]}, {"$eq": [f"${field_name}", True]}]}


def _fact_collection(db):
    collection = db.fact_hotel_reservations
    if collection.estimated_document_count() == 0:
        collection = db.fact_hotel_events
    return collection


def _fact_totals() -> dict[str, Any]:
    db = get_database()
    fact_collection = _fact_collection(db)
    booked = _bool_true_condition("reserva_bool")
    clicked = _bool_true_condition("click_bool")
    promoted = _bool_true_condition("promotion_flag")
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "total_reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "total_clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
                "promotions": {"$sum": {"$cond": [promoted, 1, 0]}},
                "avg_price": {"$avg": "$price_usd"},
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
            }
        }
    ]
    result = list(fact_collection.aggregate(pipeline))
    if not result:
        return {
            "total_events": 0,
            "total_reservations": 0,
            "total_clicks": 0,
            "promotions": 0,
            "avg_price": 0,
            "gross_revenue": 0,
        }
    summary = result[0]
    summary.pop("_id", None)
    summary["bookings"] = int(summary.get("total_reservations", 0) or 0)
    return summary


def _group_counts(field: str, limit: int = 5) -> list[dict[str, Any]]:
    db = get_database()
    fact_collection = _fact_collection(db)
    pipeline = [
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return [{"key": item["_id"], "count": item["count"]} for item in fact_collection.aggregate(pipeline)]


def _country_breakdown() -> list[dict[str, Any]]:
    db = get_database()
    grouped = _group_counts("visitor_location_country_id")
    ids = [item["key"] for item in grouped if item["key"] is not None]
    lookup = {
        item["visitor_location_country_id"]: item
        for item in db.dim_visitor_countries.find(
            {"visitor_location_country_id": {"$in": ids}},
            {"_id": 0, "visitor_location_country_id": 1, "country_name": 1},
        )
    }
    return [
        {
            "label": lookup.get(item["key"], {}).get("country_name")
            or f"Mercado visitante {item['key']}",
            "count": item["count"],
        }
        for item in grouped
    ]


def _category_breakdown(collection_name: str, id_field: str, label_field: str) -> list[dict[str, Any]]:
    db = get_database()
    grouped = _group_counts(id_field)
    ids = [item["key"] for item in grouped if item["key"] is not None]
    lookup = {
        item[id_field]: item
        for item in db[collection_name].find({id_field: {"$in": ids}}, {"_id": 0, id_field: 1, label_field: 1})
    }
    return [
        {
            "label": lookup.get(item["key"], {}).get(label_field)
            or lookup.get(item["key"], {}).get(label_field.replace("category_name", "category"))
            or str(item["key"]),
            "count": item["count"],
        }
        for item in grouped
    ]


def _reservation_breakdown() -> list[dict[str, Any]]:
    items = _group_counts("reserva_bool", limit=2)
    labels = {0: "Abandono / no reservó", 1: "Reserva completada"}
    return [{"label": labels.get(item["key"], str(item["key"])), "count": item["count"]} for item in items]


def dashboard_overview() -> dict[str, Any]:
    db = get_database()
    fact_collection = _fact_collection(db)
    totals = _fact_totals()
    latest_execution = db.etl_executions.find_one({}, {"_id": 0}, sort=[("executed_at", -1)])
    latest_quality = db.data_quality_reports.find_one({}, {"_id": 0}, sort=[("generated_at", -1)])
    distinct_hotels = fact_collection.distinct("prop_id")
    distinct_destinations = fact_collection.distinct("srch_destination_id")
    distinct_countries = fact_collection.distinct("visitor_location_country_id")

    total_events = int(totals.get("total_events", 0) or 0)
    total_reservations = int(totals.get("total_reservations", 0) or 0)
    total_clicks = int(totals.get("total_clicks", 0) or 0)
    promotions = int(totals.get("promotions", 0) or 0)
    rejected = int(db.rejected_records.count_documents({}))
    operational_metrics = {
        "configured_room_types": int(db.room_types.count_documents({})),
        "physical_rooms": int(db.hotel_rooms.count_documents({})),
        "inventory_days": int(db.room_inventory_calendar.count_documents({})),
        "rate_plans": int(db.rate_plans.count_documents({})),
        "rate_calendar": int(db.hotel_rate_calendar.count_documents({})),
        "configured_policies": int(db.hotel_policies.count_documents({})),
        "content_pages": int(db.hotel_content_pages.count_documents({})),
        "images": int(db.hotel_images.count_documents({})),
        "campaigns": int(db.promotion_campaigns.count_documents({})),
        "coupons": int(db.coupon_codes.count_documents({})),
    }
    booking_rate = round((total_reservations / total_events) * 100, 2) if total_events else 0
    click_rate = round((total_clicks / total_events) * 100, 2) if total_events else 0
    promotion_rate = round((promotions / total_events) * 100, 2) if total_events else 0
    completion_rate = round(float((latest_quality or {}).get("completeness_score", 0) or 0) * 100, 2)
    avg_price = round(float(totals.get("avg_price", 0) or 0), 2)
    gross_revenue = round(float(totals.get("gross_revenue", 0) or 0), 2)

    kpis = [
        {
            "label": "Eventos cargados",
            "value": f"{total_events}",
            "detail": f"Hoteles {len(distinct_hotels)} · destinos {len(distinct_destinations)} · países {len(distinct_countries)}",
            "trend": "Cobertura completa",
            "direction": "up",
            "icon": "icon-records",
        },
        {
            "label": "Reservas completadas",
            "value": f"{total_reservations}",
            "detail": f"Conversión {booking_rate}%",
            "trend": "Reserva sobre eventos",
            "direction": "up" if total_reservations > 0 else "down",
            "icon": "icon-booking",
        },
        {
            "label": "Clicks",
            "value": f"{total_clicks}",
            "detail": f"Click rate {click_rate}%",
            "trend": "Interacción sobre eventos",
            "direction": "up" if total_clicks > 0 else "down",
            "icon": "icon-records",
        },
        {
            "label": "Precio medio",
            "value": f"${avg_price}",
            "detail": f"Revenue bruto ${gross_revenue}",
            "trend": "Ingreso estimado",
            "direction": "up" if avg_price > 0 else "down",
            "icon": "icon-revenue",
        },
        {
            "label": "Promociones",
            "value": f"{promotions}",
            "detail": f"Tasa promoción {promotion_rate}%",
            "trend": "Campañas detectadas",
            "direction": "up" if promotions > 0 else "down",
            "icon": "icon-revenue",
        },
        {
            "label": "Completitud",
            "value": f"{completion_rate}%",
            "detail": "Calidad estructural",
            "trend": "Dataset validado",
            "direction": "up" if completion_rate >= 95 else "down",
            "icon": "icon-quality",
        },
        {
            "label": "Rechazados",
            "value": f"{rejected}",
            "detail": "Incidencias de calidad",
            "trend": "Sin rechazos" if rejected == 0 else "Revisar registros",
            "direction": "up" if rejected == 0 else "down",
            "icon": "icon-alert",
        },
        {
            "label": "Habitaciones configuradas",
            "value": f"{operational_metrics['configured_room_types']}",
            "detail": f"Físicas {operational_metrics['physical_rooms']} · inventario {operational_metrics['inventory_days']}",
            "trend": "Base operativa de alojamiento",
            "direction": "up" if operational_metrics["configured_room_types"] > 0 else "down",
            "icon": "icon-records",
        },
        {
            "label": "Tarifas y contenido",
            "value": f"{operational_metrics['rate_plans']}",
            "detail": f"Calendario {operational_metrics['rate_calendar']} · políticas {operational_metrics['configured_policies']}",
            "trend": "Preparación comercial",
            "direction": "up" if operational_metrics["rate_plans"] > 0 else "down",
            "icon": "icon-revenue",
        },
        {
            "label": "Contenido visual",
            "value": f"{operational_metrics['images']}",
            "detail": f"Páginas {operational_metrics['content_pages']} · campañas {operational_metrics['campaigns']}",
            "trend": f"Cupones {operational_metrics['coupons']}",
            "direction": "up" if operational_metrics["images"] > 0 else "down",
            "icon": "icon-quality",
        },
    ]

    return {
        "headline": {
            "total_events": total_events,
            "bookings": total_reservations,
            "total_reservations": total_reservations,
            "total_clicks": total_clicks,
            "booking_rate": booking_rate,
            "conversion_rate": booking_rate,
            "click_rate": click_rate,
            "promotions": promotions,
            "promotion_rate": promotion_rate,
            "avg_price": avg_price,
            "gross_revenue": gross_revenue,
            "distinct_hotels": len(distinct_hotels),
            "distinct_destinations": len(distinct_destinations),
            "distinct_countries": len(distinct_countries),
            "rejected_records": rejected,
            "completion_rate": completion_rate,
            **operational_metrics,
        },
        "kpis": kpis,
        "latest_execution": latest_execution,
        "latest_quality": latest_quality,
        "charts": {
            "reservation_breakdown": _reservation_breakdown(),
            "country_breakdown": _country_breakdown(),
            "price_breakdown": _category_breakdown("dim_price_category", "price_category_id", "price_category"),
            "stay_breakdown": _category_breakdown(
                "dim_stay_length_category", "stay_length_category_id", "stay_length_category"
            ),
        },
    }
