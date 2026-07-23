from __future__ import annotations

from typing import Any
from pymongo.collection import Collection
from src.app.modules.hotels.schemas import ModuleStatus
from src.database.connection import get_database


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="hotels",
        status="partial",
        description="Modulo cliente/viajero inicial con busqueda, detalle y comparacion analitica de hoteles.",
    )

def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None

def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

def _active_fact_collection() -> tuple[Collection, str]:
    db = get_database()
    if db.fact_hotel_reservations.estimated_document_count() > 0:
        return db.fact_hotel_reservations, "fact_hotel_reservations"
    return db.fact_hotel_events, "fact_hotel_events"

def _metric_projection() -> dict[str, Any]:
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    promoted = {"$or": [{"$eq": ["$promotion_flag", 1]}, {"$eq": ["$promotion_flag", True]}]}
    return {
        "events": {"$sum": 1},
        "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
        "clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
        "promotions": {"$sum": {"$cond": [promoted, 1, 0]}},
        "avg_price": {"$avg": "$price_usd"},
        "min_price": {"$min": "$price_usd"},
        "max_price": {"$max": "$price_usd"},
        "gross_revenue": {"$sum": "$reservas_brutas_usd"},
        "prop_starrating": {"$max": "$prop_starrating"},
        "prop_review_score": {"$avg": "$prop_review_score"},
        "prop_country_id": {"$first": "$prop_country_id"},
        "geo_country_code": {"$first": "$geo_country_code"},
        "destinations": {"$addToSet": "$srch_destination_id"},
    }

def _format_money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.2f}"


def _min_real_rate_for_prop(prop_id: int) -> str:
    """Return the minimum real rate from hotel_rate_calendar for today+.

    Falls back to 'Consultar' if no calendar entries exist.
    """
    from src.app.core.timezone import local_today
    from src.database.connection import get_database
    db = get_database()
    today = local_today()
    result = list(db.hotel_rate_calendar.aggregate([
        {"$match": {"prop_id": prop_id, "date": {"$gte": today}}},
        {"$group": {"_id": None, "min_rate": {"$min": "$rate_amount"}}},
    ]))
    if result and result[0].get("min_rate") is not None:
        return _format_money(result[0]["min_rate"])
    return "Consultar"

def _format_number(value: Any, decimals: int = 1) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.{decimals}f}"

def _hotel_display_name(hotel: dict[str, Any], prop_id: int) -> str:
    return hotel.get("display_name") or hotel.get("hotel_name") or hotel.get("hotel_label") or f"Hotel Partner {prop_id}"

def _destination_display_name(destination: dict[str, Any], destination_id: int) -> str:
    return destination.get("destination_display_name") or destination.get("destination_name") or destination.get("destination_label") or f"Destino {destination_id}"

def _country_display_name(country: dict[str, Any], country_id: Any) -> str:
    """Resolve country display name from dim_visitor_countries (int id) or geo_catalog (str code)."""
    return country.get("country_display_name") or country.get("country_name") or country.get("visitor_country_label") or country.get("name") or f"Mercado visitante {country_id}"

def _site_display_name(site: dict[str, Any], site_id: int) -> str:
    return site.get("site_display_name") or site.get("site_name") or site.get("site_label") or f"Canal Expedia {site_id}"

def _empty_search(filters: dict[str, Any], page_size: int, source_collection: str) -> dict[str, Any]:
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": page_size,
        "total_pages": 0,
        "has_prev": False,
        "has_next": False,
        "source_collection": source_collection,
        "filters": filters,
        "start_index": 0,
        "end_index": 0,
    }
