from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import _resolve_country_label, clean_text, hotel_display_name
from src.database.connection import get_database


def ensure_hotel_profile_metadata(prop_id: int | None = None) -> int:
    db = get_database()
    filter_doc: dict[str, Any] = {"manual_override": {"$exists": False}}
    if prop_id is not None:
        filter_doc["prop_id"] = prop_id
    modified = 0
    for hotel in db.dim_hotels.find(
        filter_doc,
        {
            "_id": 1,
            "prop_id": 1,
            "display_name": 1,
            "hotel_name": 1,
            "hotel_label": 1,
            "demo_enriched": 1,
            "manual_override": 1,
            "name_source": 1,
            "updated_by": 1,
            "updated_at": 1,
            "original_generated_name": 1,
        },
    ):
        prop_id_value = int(hotel.get("prop_id") or 0)
        generated_name = clean_text(hotel.get("display_name"))
        if not generated_name:
            generated_name = hotel_display_name(hotel, prop_id_value)
        update_payload: dict[str, Any] = {
            "manual_override": bool(hotel.get("manual_override", False)),
            "name_source": hotel.get("name_source") or "generated_from_id",
        }
        if hotel.get("demo_enriched") and not clean_text(hotel.get("original_generated_name")):
            update_payload["original_generated_name"] = generated_name
        elif not clean_text(hotel.get("original_generated_name")):
            update_payload["original_generated_name"] = generated_name
        if update_payload:
            result = db.dim_hotels.update_one({"_id": hotel["_id"]}, {"$set": update_payload})
            modified += int(result.modified_count)
    return modified


def profile_badge(hotel: dict[str, Any]) -> str:
    return "Nombre editado manualmente" if bool(hotel.get("manual_override")) else "Nombre generado"


def profile_description(prop_id: int, hotel: dict[str, Any]) -> str:
    from src.app.modules.partner.services.content.queries import content_page_for_prop

    content_page = content_page_for_prop(prop_id)
    return clean_text(hotel.get("description")) or clean_text(content_page.get("description")) or ""


def profile_payload(hotel: dict[str, Any]) -> dict[str, Any]:
    prop_id = int(hotel.get("prop_id") or 0)
    return {
        "prop_id": prop_id,
        "hotel_name": clean_text(hotel.get("hotel_name")) or hotel_display_name(hotel, prop_id),
        "display_name": hotel_display_name(hotel, prop_id),
        "display_country_label": _resolve_country_label(hotel),
        "original_generated_name": hotel_generated_name(hotel, prop_id),
        "manual_override": bool(hotel.get("manual_override", False)),
        "name_source": hotel.get("name_source") or "generated_from_id",
        "profile_badge": profile_badge(hotel),
        "updated_by": hotel.get("updated_by"),
        "updated_at": hotel.get("updated_at").isoformat() if hasattr(hotel.get("updated_at"), "isoformat") else hotel.get("updated_at"),
        "currency": clean_text(hotel.get("currency") or "USD"),
        "accepted_currencies": hotel.get("accepted_currencies") or [hotel.get("currency") or "USD"],
    }


def hotel_generated_name(hotel: dict[str, Any], prop_id: int) -> str:
    return clean_text(hotel.get("original_generated_name")) or hotel_display_name(hotel, prop_id)
