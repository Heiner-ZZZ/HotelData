from __future__ import annotations

from typing import Any

from src.database.connection import get_database

from ._helpers import ReservationInput, generate_prefixed_id, utc_now
from .collections import ensure_reservation_collections
from .validation import validate_reservation_input


def create_booking(payload: ReservationInput, *, manual_reservation: bool = False) -> dict[str, Any]:
    ensure_reservation_collections()
    errors = validate_reservation_input(payload)
    if errors:
        raise ValueError("; ".join(errors))

    db = get_database()
    booking_id = generate_prefixed_id("BK")
    created_at = utc_now()
    booking_document = {
        "booking_id": booking_id,
        "user_id": payload.user_id,
        "prop_id": payload.prop_id,
        "status": "requested",
        "booking_source": payload.source,
        "guest_name": payload.guest_name,
        "guest_email": payload.guest_email,
        "check_in_date": payload.check_in_date,
        "check_out_date": payload.check_out_date,
        "adults": payload.adults,
        "children": payload.children,
        "rooms": payload.rooms,
        "comment": payload.comment,
        "created_by": payload.created_by,
        "created_at": created_at,
        "updated_at": created_at,
        "is_test": payload.is_test,
    }
    db.booking_orders.insert_one(booking_document)
    db.booking_guests.insert_one(
        {
            "booking_id": booking_id,
            "guest_name": payload.guest_name,
            "guest_email": payload.guest_email,
            "is_primary": True,
            "created_at": created_at,
            "is_test": payload.is_test,
        }
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "requested",
            "changed_at": created_at,
            "reason": "initial_request",
            "changed_by": payload.created_by or payload.source,
            "is_test": payload.is_test,
        }
    )

    manual_document = None
    if manual_reservation:
        manual_reservation_id = generate_prefixed_id("MR")
        manual_document = {
            "manual_reservation_id": manual_reservation_id,
            "booking_id": booking_id,
            "prop_id": payload.prop_id,
            "created_at": created_at,
            "created_by": payload.created_by or "partner_manual",
            "note": payload.comment,
            "status": "requested",
            "is_test": payload.is_test,
        }
        db.manual_reservations.insert_one(manual_document)

    return {
        "booking_id": booking_id,
        "status": "requested",
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
    }
