from __future__ import annotations

from typing import Any

import pandas as pd


DIMENSION_KEY_FIELDS = {
    "dim_hotels": "prop_id",
    "dim_destinations": "srch_destination_id",
    "dim_visitor_countries": "visitor_location_country_id",
    "dim_sites": "site_id",
    "dim_dates": "date_key",
    "dim_promotions": "promotion_flag",
    "dim_click_status": "click_bool",
    "dim_reservation_status": "reserva_bool",
    "dim_occupancy_profile": "occupancy_profile_id",
    "dim_stay_length_category": "stay_length_category_id",
    "dim_booking_window_category": "booking_window_category_id",
    "dim_price_category": "price_category_id",
}


def _first_not_null(series: pd.Series) -> Any:
    values = series.dropna()
    return values.iloc[0] if not values.empty else None


def _dedupe(documents: list[dict[str, Any]], key_field: str) -> list[dict[str, Any]]:
    deduped: dict[Any, dict[str, Any]] = {}
    for document in documents:
        key = document.get(key_field)
        if key is not None and key not in deduped:
            deduped[key] = document
    return list(deduped.values())


def _static_categories() -> dict[str, list[dict[str, Any]]]:
    return {
        "dim_stay_length_category": [
            {"stay_length_category_id": "SHORT_STAY", "stay_length_category": "Estancia corta", "min_nights": 0, "max_nights": 2},
            {"stay_length_category_id": "MEDIUM_STAY", "stay_length_category": "Estancia media", "min_nights": 3, "max_nights": 7},
            {"stay_length_category_id": "LONG_STAY", "stay_length_category": "Estancia larga", "min_nights": 8, "max_nights": None},
        ],
        "dim_booking_window_category": [
            {"booking_window_category_id": "LAST_MINUTE", "booking_window_category": "Ultimo minuto", "min_days": 0, "max_days": 3},
            {"booking_window_category_id": "SHORT_TERM", "booking_window_category": "Corto plazo", "min_days": 4, "max_days": 14},
            {"booking_window_category_id": "MEDIUM_TERM", "booking_window_category": "Mediano plazo", "min_days": 15, "max_days": 30},
            {"booking_window_category_id": "LONG_TERM", "booking_window_category": "Largo plazo", "min_days": 31, "max_days": None},
        ],
        "dim_price_category": [
            {"price_category_id": "LOW_PRICE", "price_category": "Precio bajo", "min_price_usd": 0, "max_price_usd": 99.99},
            {"price_category_id": "MEDIUM_PRICE", "price_category": "Precio medio", "min_price_usd": 100, "max_price_usd": 249.99},
            {"price_category_id": "HIGH_PRICE", "price_category": "Precio alto", "min_price_usd": 250, "max_price_usd": 499.99},
            {"price_category_id": "PREMIUM_PRICE", "price_category": "Precio premium", "min_price_usd": 500, "max_price_usd": None},
        ],
        "dim_promotions": [
            {"promotion_flag": False, "promotion_label": "Sin promocion"},
            {"promotion_flag": True, "promotion_label": "Con promocion"},
        ],
        "dim_click_status": [
            {"click_bool": False, "click_status": "Sin click"},
            {"click_bool": True, "click_status": "Con click"},
        ],
        "dim_reservation_status": [
            {"reserva_bool": False, "reservation_status": "No reservada"},
            {"reserva_bool": True, "reservation_status": "Reservada"},
        ],
    }


def build_ta02_dimensions(valid_facts: pd.DataFrame, loaded_at: str) -> dict[str, list[dict[str, Any]]]:
    dimensions = _static_categories()

    if valid_facts.empty:
        for name in DIMENSION_KEY_FIELDS:
            dimensions.setdefault(name, [])
        return dimensions

    hotels = []
    for prop_id, group in valid_facts.groupby("prop_id", dropna=True):
        hotels.append(
            {
                "prop_id": int(prop_id),
                "prop_country_id": int(_first_not_null(group["prop_country_id"])),
                "prop_starrating": int(_first_not_null(group["prop_starrating"])) if _first_not_null(group["prop_starrating"]) is not None else None,
                "prop_review_score": _first_not_null(group["prop_review_score"]),
                "prop_brand_bool": bool(_first_not_null(group["prop_brand_bool"])) if _first_not_null(group["prop_brand_bool"]) is not None else None,
                "prop_location_score1": _first_not_null(group["prop_location_score1"]),
                "hotel_label": f"Hotel {int(prop_id)}",
                "loaded_at": loaded_at,
            }
        )

    destinations = [
        {
            "srch_destination_id": int(value),
            "destination_label": f"Destino {int(value)}",
            "loaded_at": loaded_at,
        }
        for value in sorted(valid_facts["srch_destination_id"].dropna().unique())
    ]

    countries = [
        {
            "visitor_location_country_id": int(value),
            "visitor_country_label": f"Pais visitante {int(value)}",
            "loaded_at": loaded_at,
        }
        for value in sorted(valid_facts["visitor_location_country_id"].dropna().unique())
    ]

    sites = [
        {
            "site_id": int(value),
            "site_label": f"Sitio {int(value)}",
            "loaded_at": loaded_at,
        }
        for value in sorted(valid_facts["site_id"].dropna().unique())
    ]

    dates = []
    for date_key, group in valid_facts.groupby("date_key", dropna=True):
        parsed = pd.to_datetime(_first_not_null(group["date_time"]), errors="coerce", utc=True)
        dates.append(
            {
                "date_key": int(date_key),
                "date": parsed.strftime("%Y-%m-%d") if not pd.isna(parsed) else None,
                "year": int(parsed.year) if not pd.isna(parsed) else None,
                "month": int(parsed.month) if not pd.isna(parsed) else None,
                "day": int(parsed.day) if not pd.isna(parsed) else None,
                "day_of_week": int(parsed.dayofweek) if not pd.isna(parsed) else None,
                "loaded_at": loaded_at,
            }
        )

    occupancy_profiles = []
    for profile_id, group in valid_facts.groupby("occupancy_profile_id", dropna=True):
        occupancy_profiles.append(
            {
                "occupancy_profile_id": profile_id,
                "srch_adults_count": int(_first_not_null(group["srch_adults_count"])),
                "srch_children_count": int(_first_not_null(group["srch_children_count"])),
                "srch_room_count": int(_first_not_null(group["srch_room_count"])),
                "occupancy_label": f"{int(_first_not_null(group['srch_adults_count']))} adultos, {int(_first_not_null(group['srch_children_count']))} ninos, {int(_first_not_null(group['srch_room_count']))} habitaciones",
                "loaded_at": loaded_at,
            }
        )

    dimensions["dim_hotels"] = _dedupe(hotels, "prop_id")
    dimensions["dim_destinations"] = _dedupe(destinations, "srch_destination_id")
    dimensions["dim_visitor_countries"] = _dedupe(countries, "visitor_location_country_id")
    dimensions["dim_sites"] = _dedupe(sites, "site_id")
    dimensions["dim_dates"] = _dedupe(dates, "date_key")
    dimensions["dim_occupancy_profile"] = _dedupe(occupancy_profiles, "occupancy_profile_id")

    for name in DIMENSION_KEY_FIELDS:
        dimensions.setdefault(name, [])

    return dimensions
