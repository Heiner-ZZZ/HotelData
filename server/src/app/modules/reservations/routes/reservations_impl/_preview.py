"""Reservation preview — build input, validate, and calculate price with amenity breakdown."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status

from src.app.modules.partner.services.content.amenities import _amenity_unit_price
from src.app.modules.reservations.service import (
    build_reservation_input,
    validate_booking_form_requirements,
    validate_reservation_input,
)
from src.app.modules.reservations.service.lifecycle.create import (
    _calculate_total_price,
    _check_availability,
)
from src.app.modules.reservations.service.lifecycle.create._availability import (
    validate_requested_room,
)
from src.app.modules.reservations.service.lifecycle.create._special_requests import (
    validate_special_requests,
)
from src.app.modules.reservations.service.lifecycle.create.core import (
    _get_cancellation_policy_text,
)
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _compute_amenity_breakdown(
    prop_id: int,
    rate_plan_id: str | None,
    selected_amenities: list[str] | None,
) -> dict[str, Any]:
    """Compute the price breakdown for amenities.

    Returns:
        {
            "included_amenities": [{"label": str, "unit_price": float, "total": float}],
            "selected_extras": [{"label": str, "unit_price": float, "total": float}],
            "amenity_total": float,
            "rate_plan_name": str | None,
        }
    """
    db = get_database()

    # Load amenity prices from hotel_content_pages
    page = db.hotel_content_pages.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "amenity_prices": 1},
    )
    stored_prices: dict[str, float] = {}
    if page and page.get("amenity_prices"):
        stored_prices = {k.lower(): float(v) for k, v in page["amenity_prices"].items()}

    def _price(label: str) -> float:
        return stored_prices.get(label.lower(), _amenity_unit_price(label))

    included: list[dict[str, float]] = []
    selected_extras: list[dict[str, float]] = []
    seen: set[str] = set()
    rate_plan_name: str | None = None

    # 1. Included amenities from the rate plan
    if rate_plan_id:
        plan = db.rate_plans.find_one(
            {"rate_plan_id": rate_plan_id},
            {"_id": 0, "name": 1, "included_amenities": 1},
        )
        if plan:
            rate_plan_name = plan.get("name")
            for label in plan.get("included_amenities", []):
                label = label.strip()
                if label:
                    key = label.lower()
                    seen.add(key)
                    unit = _price(label)
                    included.append({"label": label, "unit_price": unit})

    # 2. Extra selected amenities (not already included in the plan)
    if selected_amenities:
        for label in selected_amenities:
            label = label.strip()
            if label and label.lower() not in seen:
                unit = _price(label)
                selected_extras.append({"label": label, "unit_price": unit})
                seen.add(label.lower())

    amenity_total = sum(item["unit_price"] for item in included) + sum(item["unit_price"] for item in selected_extras)

    return {
        "included_amenities": included,
        "selected_extras": selected_extras,
        "amenity_total": round(amenity_total, 2),
        "rate_plan_name": rate_plan_name,
    }


def preview_reservation(payload: dict) -> dict:
    """Validate reservation input and calculate the total price with amenity breakdown.

    Raises HTTPException on validation failure.
    """
    try:
        reservation_input = build_reservation_input(payload, source="staff")
        errors = validate_reservation_input(reservation_input)
        errors.extend(validate_booking_form_requirements(reservation_input))
        if errors:
            raise ValueError("; ".join(dict.fromkeys(errors)))
        _, room_error = validate_requested_room(
            reservation_input.prop_id,
            reservation_input.hotel_room_id,
            reservation_input.room_type_id,
            reservation_input.check_in_date,
            reservation_input.check_out_date,
            reservation_input.rooms,
        )
        request_error = validate_special_requests(
            reservation_input.prop_id,
            reservation_input.hotel_room_id,
            reservation_input.special_requests,
        )
        avail_error = _check_availability(
            reservation_input.prop_id, reservation_input.check_in_date,
            reservation_input.check_out_date, reservation_input.rooms, reservation_input.room_type_id,
            rate_plan_id=reservation_input.rate_plan_id or "",
        )
        availability_error = room_error or request_error or avail_error
        total_price, currency, total_nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
            reservation_input.prop_id, reservation_input.room_type_id,
            reservation_input.check_in_date, reservation_input.check_out_date, reservation_input.rooms,
            adults=reservation_input.adults, children=reservation_input.children,
            rate_plan_id=reservation_input.rate_plan_id or None,
        )
        cancellation_policy = _get_cancellation_policy_text(reservation_input.prop_id)

        # ── Deposit policy check ──
        deposit_required = False
        deposit_percent = 0
        min_deposit_amount = 0.0
        try:
            db = get_database()
            dep_policy = None
            # Hierarchy: rate_plan > room_type > hotel-wide
            rp_id = reservation_input.rate_plan_id or ""
            rt_id = reservation_input.room_type_id or ""
            if rp_id:
                dep_policy = db.hotel_policies.find_one(
                    {"prop_id": reservation_input.prop_id, "rate_plan_id": rp_id},
                    {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
                )
            if not dep_policy and rt_id:
                dep_policy = db.hotel_policies.find_one(
                    {"prop_id": reservation_input.prop_id, "room_type_id": rt_id, "rate_plan_id": {"$in": ["", None]}},
                    {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
                )
            if not dep_policy:
                dep_policy = db.hotel_policies.find_one(
                    {"prop_id": reservation_input.prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
                    {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
                )
            if dep_policy:
                deposit_required = bool(dep_policy.get("deposit_required", False))
                deposit_percent = int(dep_policy.get("deposit_percent", 0) or 0)
                if deposit_required and deposit_percent > 0 and total_price:
                    min_deposit_amount = round(total_price * deposit_percent / 100, 2)
        except Exception:
            logger.warning(
                "Failed to resolve deposit policy for prop_id=%s rate_plan=%s room_type=%s — assuming deposit required as fail-safe",
                reservation_input.prop_id, rp_id, rt_id, exc_info=True,
            )
            deposit_required = True

        # ── Amenity price breakdown ──
        amenity_breakdown = _compute_amenity_breakdown(
            prop_id=reservation_input.prop_id,
            rate_plan_id=reservation_input.rate_plan_id or None,
            selected_amenities=reservation_input.selected_amenities or [],
        )

        return {
            "available": availability_error is None,
            "availability_message": availability_error,
            "total_price": total_price,
            "currency": currency,
            "total_nights": total_nights,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "tax_included": tax_included,
            "cancellation_policy": cancellation_policy,
            "deposit_required": deposit_required,
            "deposit_percent": deposit_percent,
            "min_deposit_amount": min_deposit_amount,
            # Price breakdown with amenities
            "price_breakdown": {
                "base_nightly_rate": round(total_price / total_nights, 2) if total_price and total_nights else None,
                "nights": total_nights,
                "base_total": total_price,
                "included_amenities": amenity_breakdown["included_amenities"],
                "selected_extras": amenity_breakdown["selected_extras"],
                "amenity_total": amenity_breakdown["amenity_total"],
                "rate_plan_name": amenity_breakdown["rate_plan_name"],
                "subtotal": round((total_price or 0) - tax_amount, 2) if total_price and tax_amount else None,
                "tax_amount": tax_amount,
                "tax_rate": tax_rate,
                "tax_included": tax_included,
                "total": total_price,
                "grand_total": round((total_price or 0) + amenity_breakdown["amenity_total"], 2),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
