from __future__ import annotations

from typing import Any

from src.app.modules.revenue.services.common import (
    _active_fact_collection,
    _lookup_map,
    _money,
)


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
