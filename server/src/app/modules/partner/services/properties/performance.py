from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import active_fact_collection, number


def performance_for_prop(prop_id: int) -> dict[str, Any]:
    from src.app.modules.partner.services._common import money as _money

    collection, source_collection = active_fact_collection()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$prop_id",
                "searches": {"$sum": 1},
                "clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
                "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
                "avg_price": {"$avg": "$price_usd"},
                "review_score": {"$avg": "$prop_review_score"},
                "starrating": {"$max": "$prop_starrating"},
            }
        },
    ]
    metrics = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    if not metrics:
        return {
            "source_collection": source_collection,
            "searches": 0,
            "clicks": 0,
            "reservations": 0,
            "gross_revenue": 0.0,
            "avg_price": None,
            "review_score": None,
            "starrating": None,
            "conversion_rate": 0.0,
            "click_rate": 0.0,
            "gross_revenue_label": "0.00",
            "avg_price_label": "N/D",
            "review_score_label": "N/D",
        }
    searches = int(metrics.get("searches") or 0)
    clicks = int(metrics.get("clicks") or 0)
    reservations = int(metrics.get("reservations") or 0)
    conversion_rate = round((reservations / searches) * 100, 2) if searches else 0.0
    click_rate = round((clicks / searches) * 100, 2) if searches else 0.0
    return {
        "source_collection": source_collection,
        "searches": searches,
        "clicks": clicks,
        "reservations": reservations,
        "gross_revenue": float(metrics.get("gross_revenue") or 0.0),
        "avg_price": metrics.get("avg_price"),
        "review_score": metrics.get("review_score"),
        "starrating": metrics.get("starrating"),
        "conversion_rate": conversion_rate,
        "click_rate": click_rate,
        "gross_revenue_label": _money(metrics.get("gross_revenue") or 0.0),
        "avg_price_label": _money(metrics.get("avg_price")) if metrics.get("avg_price") is not None else "N/D",
        "review_score_label": number(metrics.get("review_score")),
    }


def property_yield_score(performance: dict[str, Any]) -> int:
    searches = int(performance.get("searches", 0))
    reservations = int(performance.get("reservations", 0))
    conv = (reservations / searches * 100) if searches else 0
    review = float(performance.get("review_score") or 0)
    return min(round(60 + conv * 3.5 + review * 0.2), 100)
