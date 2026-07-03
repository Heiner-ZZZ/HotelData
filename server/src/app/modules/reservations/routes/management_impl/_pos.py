"""POS — add charges during active stay."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from src.app.modules.housekeeping.schemas import AdditionalChargeCreate
from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge

_logger = logging.getLogger(__name__)


def apply_pos_charge(
    booking_id: str,
    payload: dict,
    current_user: dict,
    db,
) -> dict:
    """Validate and apply a POS charge to an actively checked-in booking.

    Raises HTTPException on validation failure.
    """
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "stay_status": 1, "prop_id": 1, "guest_name": 1, "status": 1},
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if booking.get("stay_status") != "checked_in":
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se pueden agregar cargos POS a una reserva en estado "
                f"'{booking.get('stay_status', 'desconocido')}'. "
                f"Solo reservas con check-in activo (estancia en curso) pueden recibir cargos."
            ),
        )

    concept = str(payload.get("concept", "")).strip()
    amount = float(payload.get("amount", 0) or 0)
    if not concept or amount <= 0:
        raise HTTPException(status_code=400, detail="'concept' y 'amount' (>0) son requeridos")

    charge = AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=int(booking["prop_id"]),
        concept=concept,
        amount=amount,
        quantity=int(payload.get("quantity", 1)),
        category=str(payload.get("category", "")),
        note=str(payload.get("note", "")),
    )
    result = create_additional_charge(charge)
    if result is None:
        raise HTTPException(status_code=400, detail="No se pudo crear el cargo")

    _logger.info(
        "POS charge added to booking %s (guest: %s): $%.2f — %s",
        booking_id, booking.get("guest_name", ""), amount, concept,
    )
    return result
