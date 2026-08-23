from __future__ import annotations

import re
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, hotel_display_name, now_utc
from src.app.modules.partner.services.properties.builders import build_fact_backed_hotel
from src.app.modules.partner.services.properties.metadata import ensure_hotel_profile_metadata
from src.cache.cache_service import delete_cache
from src.database.connection import get_database


def save_partner_hotel_profile(
    prop_id: int,
    *,
    hotel_name: str,
    display_name: str,
    description: str,
    display_country_label: str,
    currency: str = "",
    accepted_currencies: list[str] | None = None,
    changed_by: str = "angular_api",
    reason: str = "Actualización manual de perfil hotelero",
) -> dict[str, Any] | None:
    from src.app.modules.partner.services.content.queries import content_page_for_prop
    from src.app.modules.partner.services.content.views import partner_hotel_profile

    ensure_hotel_profile_metadata(prop_id)
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    if hotel is None:
        fallback_hotel = build_fact_backed_hotel(prop_id)
        if fallback_hotel is None:
            return None
        hotel = db.dim_hotels.find_one_and_update(
            {"prop_id": prop_id},
            {
                "$setOnInsert": {
                    **fallback_hotel,
                    "created_at": now_utc(),
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if hotel is None:
            return None

    clean_hotel_name = clean_text(hotel_name) or hotel_display_name(hotel, prop_id)
    clean_display_name = clean_text(display_name) or clean_hotel_name or f"Hotel Partner {prop_id}"
    clean_description = clean_text(description)
    clean_country_label = clean_text(display_country_label) or (
        f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else ""
    )

    clean_currency = (clean_text(currency) or "USD").upper()
    clean_accepted = [c.upper() for c in (accepted_currencies or []) if clean_text(c)]
    if clean_currency not in clean_accepted:
        clean_accepted.insert(0, clean_currency)

    previous_values = {
        "hotel_name": clean_text(hotel.get("hotel_name")),
        "display_name": clean_text(hotel.get("display_name")) or hotel_display_name(hotel, prop_id),
        "description": clean_text(hotel.get("description")),
        "display_country_label": clean_text(hotel.get("display_country_label")),
        "currency": clean_text(hotel.get("currency") or "USD"),
        "accepted_currencies": hotel.get("accepted_currencies") or [hotel.get("currency") or "USD"],
    }
    new_values = {
        "hotel_name": clean_hotel_name,
        "display_name": clean_display_name,
        "description": clean_description,
        "display_country_label": clean_country_label,
        "currency": clean_currency,
        "accepted_currencies": clean_accepted,
    }

    generated_name = clean_text(hotel.get("original_generated_name"))
    if not generated_name:
        generated_name = clean_text(hotel.get("display_name")) if hotel.get("demo_enriched") else ""
    if not generated_name:
        generated_name = hotel_display_name(hotel, prop_id)

    # Re-resolve prop_country_id (→ dim_visitor_countries) cuando cambia el
    # país. Opción B: el país del hotel se resuelve SIEMPRE en la tabla del
    # dataset; geo_catalog ya no participa.
    country_set: dict[str, Any] = {}
    prev_label = clean_text(hotel.get("display_country_label"))
    if clean_country_label and clean_country_label != prev_label:
        visitor = db.dim_visitor_countries.find_one(
            {
                "$or": [
                    {"country_name": {"$regex": f"^{re.escape(clean_country_label.strip())}$", "$options": "i"}},
                    {"country_display_name": {"$regex": f"^{re.escape(clean_country_label.strip())}$", "$options": "i"}},
                    {"visitor_country_label": {"$regex": f"^{re.escape(clean_country_label.strip())}$", "$options": "i"}},
                ]
            },
            {"visitor_location_country_id": 1},
        )
        if visitor and visitor.get("visitor_location_country_id") is not None:
            country_set["prop_country_id"] = int(visitor["visitor_location_country_id"])
        else:
            country_set["prop_country_id"] = None

    db.dim_hotels.update_one(
        {"_id": hotel["_id"]},
        {
            "$set": {
                **new_values,
                **country_set,
                "manual_override": True,
                "name_source": "manual",
                "updated_by": changed_by,
                "updated_at": now_utc(),
                "verified_at": now_utc(),
                "original_generated_name": generated_name,
            }
        },
    )

    current_content = content_page_for_prop(prop_id)
    db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {
            "$set": {
                "prop_id": prop_id,
                "description": clean_description,
                "highlights": current_content.get("highlights") or "",
                "amenities_text": current_content.get("amenities_text") or "",
                "active_amenities": current_content.get("active_amenities", []),
                "amenities_catalog": current_content.get("amenities_catalog", []),
                "source": current_content.get("source") or "partner_manual",
                "updated_at": now_utc(),
            },
            "$setOnInsert": {"created_at": now_utc()},
        },
        upsert=True,
    )

    changes = []
    changed_at = now_utc()
    for field, old_value in previous_values.items():
        new_value = new_values[field]
        if old_value == new_value:
            continue
        changes.append(
            {
                "prop_id": prop_id,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by,
                "changed_at": changed_at,
                "reason": reason,
                "source": "manual_profile_edit",
            }
        )
    if changes:
        db.hotel_profile_changes.insert_many(changes)

    # Invalidate Redis caches for this property so fresh data loads next request
    delete_cache(f"partner:hotel:detail:{prop_id}")
    delete_cache("partner:hotels:list:default")

    return partner_hotel_profile(prop_id)
