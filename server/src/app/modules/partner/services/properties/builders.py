from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import hotel_display_name, number
from src.app.modules.partner.services.properties.metadata import profile_badge
from src.app.modules.partner.services.properties.performance import performance_for_prop, property_yield_score
from src.database.connection import get_database


def build_fact_backed_hotel(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    sample = db.fact_hotel_reservations.find_one(
        {"prop_id": prop_id},
        {
            "_id": 0,
            "prop_id": 1,
            "prop_country_id": 1,
            "prop_starrating": 1,
            "prop_review_score": 1,
            "prop_brand_bool": 1,
            "prop_location_score1": 1,
        },
    )
    if sample is None:
        return None
    generated_name = f"Hotel Partner {prop_id}"
    return {
        "prop_id": prop_id,
        "hotel_name": "Hotel no especificado",
        "display_name": generated_name,
        "hotel_label": generated_name,
        "display_country_label": (
            f"Mercado hotelero {sample.get('prop_country_id')}"
            if sample.get("prop_country_id") is not None
            else ""
        ),
        "prop_country_id": sample.get("prop_country_id"),
        "prop_starrating": sample.get("prop_starrating"),
        "prop_review_score": sample.get("prop_review_score"),
        "prop_brand_bool": sample.get("prop_brand_bool"),
        "prop_location_score1": sample.get("prop_location_score1"),
        "manual_override": False,
        "name_source": "generated_from_id",
        "original_generated_name": generated_name,
        "description": "",
    }


def synthetic_hotel(prop_id: int) -> dict[str, Any]:
    db = get_database()
    perf = performance_for_prop(prop_id)
    country = "N/D"
    sample = db.fact_hotel_reservations.find_one({"prop_id": prop_id}, {"_id": 0, "prop_country_id": 1})
    if sample and sample.get("prop_country_id") is not None:
        country = f"Mercado hotelero {sample['prop_country_id']}"
    yield_score = property_yield_score(perf)
    return {
        "prop_id": prop_id,
        "display_name": f"Hotel {prop_id}",
        "country_display_name": country,
        "location": country,
        "review_score_label": None,
        "prop_starrating": None,
        "status": "Operational" if yield_score >= 70 else ("Under Review" if yield_score >= 40 else "Maintenance"),
        "sync_status": "SYNC_ACTIVE",
        "sync_latency_ms": max(round(100 - yield_score * 0.8), 5),
        "yield_score": yield_score,
        "unit_count": 0,
        "performance": perf,
    }


def enriched_property_row(hotel: dict[str, Any] | None, prop_id: int) -> dict[str, Any]:
    base_hotel = hotel or build_fact_backed_hotel(prop_id) or synthetic_hotel(prop_id)
    perf = performance_for_prop(prop_id)
    from src.app.modules.partner.services.dashboard.operations import _operational_flags

    operational = _operational_flags(prop_id)
    country = base_hotel.get("display_country_label") or (
        f"Mercado hotelero {base_hotel.get('prop_country_id')}"
        if base_hotel.get("prop_country_id") is not None
        else "N/D"
    )
    yield_score = property_yield_score(perf)
    status = "Operational" if yield_score >= 70 else ("Under Review" if yield_score >= 40 else "Maintenance")
    sync_status = "SYNC_ACTIVE"
    sync_latency = max(round(100 - yield_score * 0.8), 5)
    return {
        **base_hotel,
        "prop_id": prop_id,
        "display_name": hotel_display_name(base_hotel, prop_id),
        "country_display_name": country,
        "location": country,
        "review_score_label": number(base_hotel.get("prop_review_score")),
        "prop_starrating": base_hotel.get("prop_starrating"),
        "manual_override": bool(base_hotel.get("manual_override", False)),
        "profile_badge": profile_badge(base_hotel),
        "status": status,
        "sync_status": sync_status,
        "sync_latency_ms": sync_latency,
        "yield_score": yield_score,
        "unit_count": operational["counts"]["hotel_rooms"],
        "performance": perf,
        "operational": operational,
    }
