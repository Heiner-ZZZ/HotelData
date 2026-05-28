from __future__ import annotations

from typing import Any

from src.app.features.collections.service import collection_counts
from src.app.features.quality.service import quality_summary
from src.database.connection import get_database


def _fact_collection(db):
    collection = db.fact_hotel_reservations
    if collection.estimated_document_count() == 0:
        collection = db.fact_hotel_events
    return collection


def _fact_totals() -> dict[str, Any]:
    db = get_database()
    fact_collection = _fact_collection(db)
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "bookings": {"$sum": {"$cond": [{"$eq": ["$reserva_bool", 1]}, 1, 0]}},
                "promotions": {"$sum": {"$cond": [{"$eq": ["$promotion_flag", 1]}, 1, 0]}},
                "avg_price": {"$avg": "$price_usd"},
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
            }
        }
    ]
    result = list(fact_collection.aggregate(pipeline))
    if not result:
        return {
            "total_events": 0,
            "bookings": 0,
            "promotions": 0,
            "avg_price": 0,
            "gross_revenue": 0,
        }
    summary = result[0]
    summary.pop("_id", None)
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
            "label": lookup.get(item["key"], {}).get("country_name") or f"País {item['key']}",
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
    bookings = int(totals.get("bookings", 0) or 0)
    promotions = int(totals.get("promotions", 0) or 0)
    rejected = int((latest_quality or {}).get("rejected_records", 0) or 0)

    return {
        "headline": {
            "total_events": total_events,
            "bookings": bookings,
            "booking_rate": round((bookings / total_events) * 100, 2) if total_events else 0,
            "promotions": promotions,
            "promotion_rate": round((promotions / total_events) * 100, 2) if total_events else 0,
            "avg_price": round(float(totals.get("avg_price", 0) or 0), 2),
            "gross_revenue": round(float(totals.get("gross_revenue", 0) or 0), 2),
            "distinct_hotels": len(distinct_hotels),
            "distinct_destinations": len(distinct_destinations),
            "distinct_countries": len(distinct_countries),
            "rejected_records": rejected,
            "completion_rate": round(float((latest_quality or {}).get("completeness_score", 0) or 0) * 100, 2),
        },
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
