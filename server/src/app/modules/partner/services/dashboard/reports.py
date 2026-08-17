from __future__ import annotations

import math
from typing import Any

from src.app.modules.partner.services._common import hotel_display_name
from src.app.modules.partner.services.dashboard.operations import (
    _operational_dashboard_metrics,
)
from src.app.modules.partner.services.properties.metadata import (
    profile_badge as _profile_badge,
)
from src.app.security.hotel_filter import assigned_hotels_for_user
from src.database.connection import get_database


def management_property_options(limit: int = 100, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    # Lightweight path: amenities/options only needs id+name. The enriched
    # listing (list_partner_hotels) runs per-hotel performance/operational
    # aggregates — 100 rows ≈ 5s of wasted work for a name dropdown.
    from src.app.modules.partner.services.properties.listing import (
        list_property_options,
    )

    results = list_property_options("", page=1, page_size=min(max(limit, 1), 100), user=user)
    return [
        {
            "prop_id": item["prop_id"],
            "display_name": item.get("display_name") or f"Hotel {item['prop_id']}",
        }
        for item in results["items"]
    ]


def _reports_hotel_match(user: dict[str, Any] | None) -> dict[str, Any]:
    """Build a $match stage for aggregation pipelines that filters by assigned hotels.

    ``None`` scope (unrestricted) → ``{}`` (no filter). A restricted role
    without hotels → a match-nothing stage (deny-by-default; previously
    ``{}`` meant "all hotels" and leaked the whole system to empty-scope users).
    """
    ids = assigned_hotels_for_user(user)
    if ids is None:
        return {}
    if not ids:
        return {"$match": {"prop_id": {"$in": []}}}
    return {"$match": {"prop_id": {"$in": ids}}}


_CONFIRMED_STATUSES = ("confirmed", "checked_in", "checked_out", "completed")


def _reports_monthly_series(
    collection,
    hotel_match: dict[str, Any],
) -> list[dict[str, Any]]:
    """Agrupa ``booking_orders`` (tabla operativa real) por mes de llegada
    (``check_in_date`` YYYY-MM-DD) y devuelve filas mensuales ``{month,
    events, reservations, gross_revenue}`` ordenadas desc por mes (contrato
    compuesto táctico).

    Reservas = órdenes confirmadas; revenue = suma de ``total_price`` de las
    confirmadas. Nunca toca la fact sintética GA03.
    """
    pipeline: list[dict[str, Any]] = [
        {
            "$set": {
                "_confirmed": {
                    "$in": [{"$toLower": {"$ifNull": ["$status", ""]}}, list(_CONFIRMED_STATUSES)]
                }
            }
        },
        {
            "$group": {
                "_id": {"$substr": ["$check_in_date", 0, 7]},
                "events": {"$sum": 1},
                "reservations": {"$sum": {"$cond": ["$_confirmed", 1, 0]}},
                "gross_revenue": {"$sum": {"$cond": ["$_confirmed", {"$ifNull": ["$total_price", 0]}, 0]}},
            }
        },
        {"$sort": {"_id": -1}},
    ]
    if hotel_match:
        pipeline.insert(0, hotel_match)
    return [
        {
            "month": str(item["_id"]),
            "events": int(item.get("events") or 0),
            "reservations": int(item.get("reservations") or 0),
            "gross_revenue": round(float(item.get("gross_revenue") or 0), 2),
        }
        for item in collection.aggregate(pipeline, allowDiskUse=True)
        if item.get("_id")
    ]


def _paginate_records(
    monthly: list[dict[str, Any]],
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pagina las filas mensuales (una por hotel×mes) y devuelve las de la
    página + metadatos de paginación (mismo contrato que kpi_reports)."""
    total = len(monthly)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    rows = monthly[start : start + page_size]
    return rows, {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def _monthly_series_shape(monthly: list[dict[str, Any]]) -> dict[str, Any]:
    """Convierte las filas mensuales (hotel×mes) en la serie compuesta
    (labels de mes + datasets de eventos/reservas/revenue) para el gráfico."""
    by_month: dict[str, dict[str, float]] = {}
    for row in monthly:
        bucket = by_month.setdefault(row["month"], {"events": 0.0, "reservations": 0.0, "gross_revenue": 0.0})
        bucket["events"] += row["events"]
        bucket["reservations"] += row["reservations"]
        bucket["gross_revenue"] += row["gross_revenue"]
    labels = sorted(by_month)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Eventos", "data": [int(by_month[m]["events"]) for m in labels]},
            {"label": "Reservas", "data": [int(by_month[m]["reservations"]) for m in labels]},
            {"label": "Revenue (USD)", "data": [round(by_month[m]["gross_revenue"], 2) for m in labels]},
        ],
    }


def management_reports_summary(
    user: dict[str, Any] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    db = get_database()
    collection = db.booking_orders
    source_collection = "booking_orders"
    hotel_match = _reports_hotel_match(user)
    confirmed = {"$in": [{"$toLower": {"$ifNull": ["$status", ""]}}, list(_CONFIRMED_STATUSES)]}
    totals_pipeline = [
        {
            "$set": {"_confirmed": confirmed},
        },
        {
            "$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "reservations_detected": {"$sum": {"$cond": ["$_confirmed", 1, 0]}},
                "gross_revenue": {"$sum": {"$cond": ["$_confirmed", {"$ifNull": ["$total_price", 0]}, 0]}},
            }
        }
    ]
    if hotel_match:
        totals_pipeline.insert(0, hotel_match)
    totals = next(collection.aggregate(totals_pipeline, allowDiskUse=True), None) or {}

    monthly = _reports_monthly_series(collection, hotel_match)
    rows, pagination = _paginate_records(monthly, page, page_size)

    # Labels de hoteles reales (dim_hotels filtrado a los props operativos).
    hotel_lookup = {
        item["prop_id"]: item
        for item in db.dim_hotels.find({}, {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1, "city": 1, "display_country_label": 1, "manual_override": 1})
        if item.get("prop_id") is not None
    }

    def _top_aggregate(pipeline_base: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pipeline = list(pipeline_base)
        if hotel_match:
            pipeline.insert(0, hotel_match)
        return list(collection.aggregate(pipeline, allowDiskUse=True))

    top_hotels = _top_aggregate([
        {
            "$set": {"_confirmed": confirmed},
        },
        {"$group": {"_id": "$prop_id", "gross_revenue": {"$sum": {"$cond": ["$_confirmed", {"$ifNull": ["$total_price", 0]}, 0]}}, "events": {"$sum": 1}}},
        {"$sort": {"gross_revenue": -1}},
        {"$limit": 5},
    ])
    # Destinos/países se derivan del hotel real (ciudad/país), no de la fact.
    top_by_prop = _top_aggregate([
        {
            "$set": {"_confirmed": confirmed},
        },
        {"$group": {"_id": "$prop_id", "events": {"$sum": 1}, "gross_revenue": {"$sum": {"$cond": ["$_confirmed", {"$ifNull": ["$total_price", 0]}, 0]}}, "reservations": {"$sum": {"$cond": ["$_confirmed", 1, 0]}}}},
        {"$sort": {"events": -1}},
        {"$limit": 5},
    ])

    operational_counts = _operational_dashboard_metrics()
    return {
        "source_collection": source_collection,
        "total_events": int(totals.get("total_events") or 0),
        "reservations_detected": int(totals.get("reservations_detected") or 0),
        "gross_revenue": round(float(totals.get("gross_revenue") or 0), 2),
        "series": _monthly_series_shape(monthly),
        "rows": rows,
        "total": pagination["total"],
        "page": pagination["page"],
        "page_size": pagination["page_size"],
        "total_pages": pagination["total_pages"],
        "has_next": pagination["has_next"],
        "has_prev": pagination["has_prev"],
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
                "label": (hotel_lookup.get(int(item["_id"]), {}).get("city")
                         or hotel_display_name(hotel_lookup.get(int(item["_id"]), {}), int(item["_id"]))),
                "events": int(item.get("events") or 0),
                "gross_revenue": round(float(item.get("gross_revenue") or 0), 2),
            }
            for item in top_by_prop
            if item.get("_id") is not None
        ],
        "top_visitor_countries": [
            {
                "visitor_location_country_id": int(hotel_lookup.get(int(item["_id"]), {}).get("prop_country_id") or 0),
                "label": (hotel_lookup.get(int(item["_id"]), {}).get("display_country_label")
                         or f"Mercado hotelero {int(item['_id'])}"),
                "events": int(item.get("events") or 0),
                "reservations": int(item.get("reservations") or 0),
            }
            for item in top_by_prop
            if item.get("_id") is not None
        ],
        "operational_counts": operational_counts,
    }
