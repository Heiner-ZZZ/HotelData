from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import (
    active_fact_collection,
    destination_display_name,
    hotel_display_name,
    number,
)
from src.app.modules.partner.services.properties.builders import build_fact_backed_hotel
from src.app.modules.partner.services.properties.metadata import (
    ensure_hotel_profile_metadata,
    hotel_generated_name,
    profile_badge,
)
from src.app.modules.partner.services.properties.performance import performance_for_prop
from src.database.connection import get_database


def partner_hotel_detail(prop_id: int) -> dict[str, Any] | None:
    ensure_hotel_profile_metadata(prop_id)
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0})
    if hotel is None:
        hotel = build_fact_backed_hotel(prop_id)
    if hotel is None:
        return None
    master_hotel = db.hotels.find_one({"hotel_code": {"$exists": True}}, {"_id": 0}) or {}
    perf = performance_for_prop(prop_id)
    from src.app.modules.partner.services.dashboard.operations import _operational_flags

    operational = _operational_flags(prop_id)
    return {
        "hotel": {
            **hotel,
            "prop_id": prop_id,
            "display_name": hotel_display_name(hotel, prop_id),
            "country_display_name": hotel.get("display_country_label") or (f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else "N/D"),
            "review_score_label": number(hotel.get("prop_review_score")),
            "manual_override": bool(hotel.get("manual_override", False)),
            "name_source": hotel.get("name_source") or "generated_from_id",
            "original_generated_name": hotel_generated_name(hotel, prop_id),
            "profile_badge": profile_badge(hotel),
            "operational": operational,
        },
        "performance": perf,
        "master_hotel": master_hotel,
    }


def partner_hotel_performance(prop_id: int) -> dict[str, Any] | None:
    from src.app.modules.partner.services._common import money as _money

    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    collection, _ = active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$srch_destination_id",
                "searches": {"$sum": 1},
                "reservations": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
                "avg_price": {"$avg": "$price_usd"},
            }
        },
        {"$sort": {"searches": -1}},
        {"$limit": 6},
    ]
    top_destinations = list(collection.aggregate(pipeline, allowDiskUse=True))
    destination_ids = [row["_id"] for row in top_destinations if row.get("_id") is not None]
    destination_lookup = {
        int(item["srch_destination_id"]): item
        for item in db.dim_destinations.find({"srch_destination_id": {"$in": destination_ids}}, {"_id": 0})
        if item.get("srch_destination_id") is not None
    }
    detail["top_destinations"] = [
        {
            "destination_label": destination_display_name(destination_lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "searches": int(row.get("searches") or 0),
            "reservations": int(row.get("reservations") or 0),
            "avg_price_label": _money(row.get("avg_price")),
        }
        for row in top_destinations
        if row.get("_id") is not None
    ]
    return detail
