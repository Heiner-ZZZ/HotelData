from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import (
    active_fact_collection,
    destination_display_name,
    hotel_display_name,
)
from src.app.modules.partner.services.dashboard.operations import _operational_dashboard_metrics
from src.app.modules.partner.services.properties import list_partner_hotels
from src.app.modules.partner.services.properties.metadata import profile_badge as _profile_badge
from src.app.security.hotel_filter import assigned_hotels_for_user
from src.database.connection import get_database


def management_property_options(limit: int = 100, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    results = list_partner_hotels("", page=1, page_size=min(max(limit, 1), 100), user=user)
    return [
        {
            "prop_id": item["prop_id"],
            "display_name": item.get("display_name") or f"Hotel {item['prop_id']}",
        }
        for item in results["items"]
    ]


def _reports_hotel_match(user: dict[str, Any] | None) -> dict[str, Any]:
    """Build a $match stage for aggregation pipelines that filters by assigned hotels."""
    ids = assigned_hotels_for_user(user)
    if ids:
        return {"$match": {"prop_id": {"$in": ids}}}
    return {}


def management_reports_summary(user: dict[str, Any] | None = None) -> dict[str, Any]:
    db = get_database()
    collection, source_collection = active_fact_collection()
    hotel_match = _reports_hotel_match(user)
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
    if hotel_match:
        totals_pipeline.insert(0, hotel_match)
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

    def _top_aggregate(pipeline_base: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pipeline = list(pipeline_base)
        if hotel_match:
            pipeline.insert(0, hotel_match)
        return list(collection.aggregate(pipeline, allowDiskUse=True))

    top_hotels = _top_aggregate([
        {"$group": {"_id": "$prop_id", "gross_revenue": {"$sum": "$reservas_brutas_usd"}, "events": {"$sum": 1}}},
        {"$sort": {"gross_revenue": -1}},
        {"$limit": 5},
    ])
    top_destinations = _top_aggregate([
        {"$group": {"_id": "$srch_destination_id", "events": {"$sum": 1}, "gross_revenue": {"$sum": "$reservas_brutas_usd"}}},
        {"$sort": {"events": -1}},
        {"$limit": 5},
    ])
    top_countries = _top_aggregate([
        {
            "$group": {
                "_id": "$visitor_location_country_id",
                "events": {"$sum": 1},
                "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": 5},
    ])

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
