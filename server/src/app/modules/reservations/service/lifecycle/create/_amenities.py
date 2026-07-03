"""Amenity charge generation for booking creation."""

from __future__ import annotations

import logging
from typing import Any

from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _generate_amenity_charges(
    *,
    booking_id: str,
    prop_id: int,
    selected_amenities: list[str],
) -> list[dict[str, Any]]:
    """Automatically generate additional charges for paid amenities."""
    if not selected_amenities:
        return []

    db = get_database()
    page = db.hotel_content_pages.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "amenity_prices": 1},
    )
    stored_prices: dict[str, float] = {}
    if page and page.get("amenity_prices"):
        stored_prices = {k.lower(): float(v) for k, v in page["amenity_prices"].items()}

    from src.app.modules.partner.services.content.amenities import _amenity_unit_price
    from src.app.modules.housekeeping.schemas import AdditionalChargeCreate
    from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge

    created: list[dict[str, Any]] = []
    for amenity_label in selected_amenities:
        label_clean = amenity_label.strip()
        if not label_clean:
            continue
        unit_price = stored_prices.get(label_clean.lower(), _amenity_unit_price(label_clean))
        if unit_price <= 0:
            continue
        try:
            charge_payload = AdditionalChargeCreate(
                booking_id=booking_id,
                prop_id=prop_id,
                concept=f"Amenidad: {label_clean}",
                amount=unit_price,
                quantity=1,
                note="Generado automáticamente al crear la reserva.",
            )
            charge_result = create_additional_charge(charge_payload)
            if charge_result:
                created.append(charge_result)
        except Exception:
            logger.exception("Failed to generate amenity charge for %s on booking %s", label_clean, booking_id)

    return created
