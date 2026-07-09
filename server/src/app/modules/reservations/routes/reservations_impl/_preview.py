"""Reservation preview — build input, validate, and calculate price."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.modules.reservations.service import build_reservation_input, validate_reservation_input
from src.app.modules.reservations.service.lifecycle.create import _check_availability, _calculate_total_price
from src.app.modules.reservations.service.lifecycle.create.core import _get_cancellation_policy_text


def preview_reservation(payload: dict) -> dict:
    """Validate reservation input and calculate the total price.

    Raises HTTPException on validation failure.
    """
    try:
        reservation_input = build_reservation_input(payload, source="staff")
        errors = validate_reservation_input(reservation_input)
        if errors:
            raise ValueError("; ".join(errors))
        avail_error = _check_availability(
            reservation_input.prop_id, reservation_input.check_in_date,
            reservation_input.check_out_date, reservation_input.rooms, reservation_input.room_type_id,
        )
        total_price, currency, total_nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
            reservation_input.prop_id, reservation_input.room_type_id,
            reservation_input.check_in_date, reservation_input.check_out_date, reservation_input.rooms,
            adults=reservation_input.adults, children=reservation_input.children,
            rate_plan_id=reservation_input.rate_plan_id or None,
        )
        cancellation_policy = _get_cancellation_policy_text(reservation_input.prop_id)
        return {
            "available": avail_error is None,
            "availability_message": avail_error,
            "total_price": total_price,
            "currency": currency,
            "total_nights": total_nights,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "tax_included": tax_included,
            "cancellation_policy": cancellation_policy,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
