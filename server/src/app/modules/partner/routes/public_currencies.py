from __future__ import annotations

from fastapi import APIRouter, Query

from src.app.modules.partner.services.currencies import list_currencies
from src.database.connection import get_database

public_router = APIRouter(prefix="/api/public", tags=["public"])


@public_router.get("/currencies")
def public_list_currencies_api(
    active_only: bool = Query(default=True),
) -> dict:
    """Return active system currencies for public landing surfaces.

    Public — no auth required. Currencies are non-sensitive reference data
    used by the B2C landing page (welcome) to drive the lang/currency chip
    and price formatting across the Booking-flow preview.
    """
    currencies = list_currencies(active_only=active_only)
    return {"currencies": currencies}


@public_router.get("/countries")
def public_list_countries_api(
    active_only: bool = Query(default=True),
) -> dict:
    """Return the geo-catalog countries for the onboarding wizard.

    Public — no auth required. Countries are non-sensitive reference data
    used by /onboarding/alojamiento to power the country dropdown. Falls
    back to a small curated LATAM subset if the catalog is empty so the
    wizard never blocks a host who's mid-flow on a flaky network.
    """
    db = get_database()
    query: dict = {}
    if active_only:
        query["active"] = {"$ne": False}
    raw = list(
        db.dim_visitor_countries.find(
            query,
            {
                "_id": 0,
                "visitor_location_country_id": 1,
                "country_name": 1,
            },
        ).sort("country_name", 1)
    )

    if not raw:
        # Self-heal fallback so the wizard dropdown never renders empty.
        fallback = [
            {"visitor_location_country_id": 1, "country_name": "México"},
            {"visitor_location_country_id": 2, "country_name": "Colombia"},
            {"visitor_location_country_id": 3, "country_name": "Argentina"},
            {"visitor_location_country_id": 4, "country_name": "Perú"},
            {"visitor_location_country_id": 5, "country_name": "Chile"},
            {"visitor_location_country_id": 6, "country_name": "Brasil"},
            {"visitor_location_country_id": 7, "country_name": "España"},
        ]
        return {"countries": fallback, "fallback": True}

    countries = [
        {
            "visitor_location_country_id": row["visitor_location_country_id"],
            "country_name": (
                row.get("country_name")
                or f"País {row['visitor_location_country_id']}"
            ),
        }
        for row in raw
        if row.get("visitor_location_country_id") is not None
    ]
    return {"countries": countries, "fallback": False}


@public_router.get("/hotels/{prop_id}/images")
def public_hotel_images_api(prop_id: int):
    """Public endpoint — return hotel custom images ordered by sort_order.
    Used by the hotel card to show real hotel photos before loremflickr placeholders."""
    db = get_database()
    images = list(
        db.hotel_images.find(
            {"prop_id": prop_id},
            {"_id": 0, "image_url": 1, "title": 1, "sort_order": 1},
        ).sort([("sort_order", 1)])
    )
    return {"ok": True, "images": images}


@public_router.get("/hotels/{prop_id}/room-images")
def public_room_type_images_api(prop_id: int):
    """Public endpoint — return room-type images ordered by sort_order.
    Used by the hotel card gallery between hotel images and loremflickr placeholders."""
    db = get_database()
    images = list(
        db.room_type_images.find(
            {"prop_id": prop_id},
            {"_id": 0, "image_url": 1, "title": 1, "room_type_id": 1, "sort_order": 1},
        ).sort([("sort_order", 1)])
    )
    return {"ok": True, "images": images}
