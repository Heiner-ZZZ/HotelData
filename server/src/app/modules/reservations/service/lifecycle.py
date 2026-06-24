from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from pymongo.errors import DuplicateKeyError

from src.database.connection import get_database

from ..notifications import notify_staff_new_booking
from ._helpers import ReservationInput, generate_prefixed_id, utc_now
from .collections import ensure_reservation_collections
from .validation import validate_reservation_input


logger = logging.getLogger(__name__)


def _check_availability(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str = "",
) -> str | None:
    """Check if the requested inventory is available.

    Returns None if available, or an error message string if not.
    """
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "Invalid date format; expected YYYY-MM-DD"

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    if not dates:
        return "check_out_date must be after check_in_date"

    match: dict[str, Any] = {
        "prop_id": prop_id,
        "date": {"$in": dates},
    }
    if room_type_id:
        match["room_type_id"] = room_type_id

    records = list(
        db.room_inventory_calendar.find(match, {"_id": 0, "date": 1, "available_rooms": 1}).sort("date", 1)
    )
    found_dates = {r["date"]: r.get("available_rooms", 0) for r in records}

    for d in dates:
        avail = found_dates.get(d, 0)
        if avail < rooms:
            if d not in found_dates:
                return f"No inventory data for date {d}"
            return f"Only {avail} room(s) available on {d}, requested {rooms}"

    return None


def _calculate_total_price(
    prop_id: int,
    room_type_id: str,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
) -> tuple[float | None, str, int]:
    """Calculate total price from hotel_rate_calendar.

    Returns (total_price, currency, total_nights).
    Returns (None, "USD", nights) if no rate records found.
    """
    db = get_database()
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None, "USD", 0

    total_nights = max(0, (check_out - check_in).days)
    if total_nights == 0:
        return None, "USD", 0

    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_nights)]

    match: dict[str, Any] = {
        "prop_id": prop_id,
        "date": {"$in": dates},
    }
    if room_type_id:
        match["room_type_id"] = room_type_id

    records = list(
        db.hotel_rate_calendar.find(match, {"_id": 0, "date": 1, "rate_amount": 1, "currency": 1}).sort("date", 1)
    )
    if not records:
        return None, "USD", total_nights

    currency = records[0].get("currency", "USD")
    total = sum(r.get("rate_amount", 0) for r in records) * rooms
    return total, currency, total_nights


def create_booking(payload: ReservationInput, *, manual_reservation: bool = False) -> dict[str, Any]:
    ensure_reservation_collections()
    errors = validate_reservation_input(payload)
    if errors:
        raise ValueError("; ".join(errors))

    avail_error = _check_availability(
        payload.prop_id,
        payload.check_in_date,
        payload.check_out_date,
        payload.rooms,
        payload.room_type_id,
    )
    if avail_error:
        raise ValueError(f"Cannot create booking: {avail_error}")

    total_price, currency, total_nights = _calculate_total_price(
        payload.prop_id,
        payload.room_type_id,
        payload.check_in_date,
        payload.check_out_date,
        payload.rooms,
    )

    db = get_database()
    booking_id = generate_prefixed_id("BK")
    created_at = utc_now()
    booking_status = "confirmed" if manual_reservation else "pending"
    booking_document = {
        "booking_id": booking_id,
        "user_id": payload.user_id,
        "prop_id": payload.prop_id,
        "status": booking_status,
        "booking_source": payload.source,
        "guest_name": payload.guest_name,
        "guest_email": payload.guest_email,
        "guest_phone": payload.guest_phone,
        "room_type_id": payload.room_type_id,
        "check_in_date": payload.check_in_date,
        "check_out_date": payload.check_out_date,
        "adults": payload.adults,
        "children": payload.children,
        "rooms": payload.rooms,
        "comment": payload.comment,
        "total_price": total_price,
        "currency": currency,
        "total_nights": total_nights,
        "created_by": payload.created_by,
        "created_at": created_at,
        "updated_at": created_at,
        "is_test": payload.is_test,
    }
    try:
        db.booking_orders.insert_one(booking_document)
    except DuplicateKeyError:
        raise ValueError("booking_id already exists, retry")

    db.booking_guests.insert_one(
        {
            "booking_id": booking_id,
            "guest_name": payload.guest_name,
            "guest_email": payload.guest_email,
            "guest_phone": payload.guest_phone,
            "is_primary": True,
            "created_at": created_at,
            "is_test": payload.is_test,
        }
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": booking_status,
            "changed_at": created_at,
            "reason": "manual_reservation" if manual_reservation else "initial_request",
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
            "status": "pending",
            "is_test": payload.is_test,
        }
        db.manual_reservations.insert_one(manual_document)

    # ── Notify staff about the new pending booking ──
    try:
        notify_staff_new_booking(
            prop_id=payload.prop_id,
            booking_id=booking_id,
            guest_name=payload.guest_name,
            guest_email=payload.guest_email,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
            adults=payload.adults,
            children=payload.children,
            rooms=payload.rooms,
            total_price=total_price,
            currency=currency,
            total_nights=total_nights,
            comment=payload.comment,
        )
    except Exception:
        # Notification failure must never block the booking creation
        logger.exception("Failed to notify staff for booking %s", booking_id)

    return {
        "booking_id": booking_id,
        "status": booking_status,
        "total_price": total_price,
        "currency": currency,
        "total_nights": total_nights,
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
    }
