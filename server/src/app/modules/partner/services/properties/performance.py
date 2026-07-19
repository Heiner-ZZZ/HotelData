from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.app.modules.partner.services._common import active_fact_collection, number
from src.database.connection import get_database
from src.app.modules.hotels.service._helpers import _min_real_rate_for_prop


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
        metrics = {
            "searches": 0,
            "clicks": 0,
            "reservations": 0,
            "gross_revenue": 0.0,
            "avg_price": None,
            "review_score": None,
            "starrating": None,
        }

    searches = int(metrics.get("searches") or 0)
    clicks = int(metrics.get("clicks") or 0)

    # Also count real-time clicks tracked by the web app (anonymous + authenticated).
    # We limit to the last 30 days so the metric stays aligned with the active
    # searches window and doesn't grow unbounded.
    db = get_database()
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    click_events_count = db.click_events.count_documents({
        "prop_id": prop_id,
        "clicked_at": {"$gte": thirty_days_ago},
    })
    clicks += int(click_events_count)

    fact_reservations = int(metrics.get("reservations") or 0)
    fact_revenue = float(metrics.get("gross_revenue") or 0.0)

    # Also count confirmed operational booking_orders for this hotel
    booking_pipeline = [
        {"$match": {"prop_id": prop_id, "status": "confirmed"}},
        {
            "$group": {
                "_id": None,
                "booking_count": {"$sum": 1},
                "booking_revenue": {"$sum": {"$ifNull": ["$total_price", 0]}},
            }
        },
    ]
    booking_agg = next(db.booking_orders.aggregate(booking_pipeline, allowDiskUse=True), None)

    if booking_agg:
        operational_reservations = int(booking_agg.get("booking_count", 0))
        operational_revenue = float(booking_agg.get("booking_revenue", 0.0))
    else:
        operational_reservations = 0
        operational_revenue = 0.0

    # Keep both sources separate: historical (fact) vs operational (booking_orders)
    total_revenue = fact_revenue + operational_revenue
    includes_operational = operational_reservations > 0
    conversion_rate = round((fact_reservations / searches) * 100, 2) if searches else 0.0
    click_rate = round((clicks / searches) * 100, 2) if searches else 0.0

    # Real min rate from hotel_rate_calendar (today+)
    min_rate_label = _min_real_rate_for_prop(prop_id)

    return {
        "source_collection": source_collection,
        "searches": searches,
        "clicks": clicks,
        "reservations": fact_reservations,
        "gross_revenue": total_revenue,
        "avg_price": metrics.get("avg_price"),
        "review_score": metrics.get("review_score"),
        "starrating": metrics.get("starrating"),
        "conversion_rate": conversion_rate,
        "click_rate": click_rate,
        "gross_revenue_label": _money(total_revenue),
        "avg_price_label": _money(metrics.get("avg_price")) if metrics.get("avg_price") is not None else "N/D",
        "min_rate_label": min_rate_label,
        "review_score_label": number(metrics.get("review_score")),
        "includes_operational_bookings": includes_operational,
        "historical_reservations": fact_reservations,
        "operational_reservations": operational_reservations,
    }


def property_yield_score(performance: dict[str, Any]) -> int:
    searches = int(performance.get("searches", 0))
    reservations = int(performance.get("reservations", 0))
    conv = (reservations / searches * 100) if searches else 0
    review = float(performance.get("review_score") or 0)
    return min(round(60 + conv * 3.5 + review * 0.2), 100)
