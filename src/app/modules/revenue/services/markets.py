from __future__ import annotations

from typing import Any

from src.app.modules.revenue.services.common import (
    _active_fact_collection,
    _lookup_map,
)


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
