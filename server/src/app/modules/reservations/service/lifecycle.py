from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pymongo.errors import DuplicateKeyError

from src.database.connection import get_database

from ._helpers import ReservationInput, generate_prefixed_id, utc_now
from .collections import ensure_reservation_collections
from .validation import validate_reservation_input


def _check_availability(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str | None = None,
) -> str | None:
    """Verify room inventory availability. Returns error message or None if OK."""
    try:
        start = date.fromisoformat(check_in_date)
        end = date.fromisoformat(check_out_date)
    except (ValueError, TypeError):
        return "Invalid date format for availability check"

    nights = (end - start).days
    if nights < 1:
        return "Check-out must be after check-in"

    db = get_database()
    date_list = [(start + timedelta(days=i)).isoformat() for i in range(nights)]

    # If room_type_id is specified, check that specific type
    if room_type_id:
        match = {
            "prop_id": prop_id,
            "room_type_id": room_type_id,
            "date": {"$in": date_list},
            "available_rooms": {"$gte": rooms},
        }
        available_dates = db.room_inventory_calendar.count_documents(match)
        if available_dates < nights:
            return "The selected room type does not have enough availability for all requested dates"
        return None

    # Without room_type_id, find ANY room type with availability for ALL dates
    room_types = list(
        db.room_inventory_calendar.distinct(
            "room_type_id",
            {"prop_id": prop_id, "date": {"$in": date_list}, "available_rooms": {"$gte": rooms}},
        )
    )
    if not room_types:
        return "No room types available for the requested dates"
    return None


def _calculate_total_price(
    prop_id: int,
    room_type_id: str | None,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
) -> tuple[float | None, str, int]:
    """Calculate total estimated price from hotel_rate_calendar.

    Returns (total_price, currency, nights).
    """
    try:
        start = date.fromisoformat(check_in_date)
        end = date.fromisoformat(check_out_date)
    except (ValueError, TypeError):
        return None, "USD", 0

    nights = (end - start).days
    if nights < 1:
        return None, "USD", 0

    db = get_database()
    date_list = [(start + timedelta(days=i)).isoformat() for i in range(nights)]

    # Build match filter
    match: dict[str, Any] = {
        "prop_id": prop_id,
        "date": {"$in": date_list},
        "is_closed": {"$ne": True},
    }
    if room_type_id:
        match["room_type_id"] = room_type_id

    pipeline = [
        {"$match": match},
        {"$group": {"_id": None, "total": {"$sum": "$rate_amount"}, "currency": {"$first": "$currency"}}},
    ]
    result = list(db.hotel_rate_calendar.aggregate(pipeline))

    if not result or result[0].get("total") is None:
        return None, "USD", nights

    total_nightly = float(result[0]["total"])
    total_price = round(total_nightly * rooms, 2)
    currency = result[0].get("currency", "USD")
    return total_price, currency, nights


def create_booking(payload: ReservationInput, *, manual_reservation: bool = False) -> dict[str, Any]:
    ensure_reservation_collections()
    errors = validate_reservation_input(payload)
    if errors:
        raise ValueError("; ".join(errors))

    db = get_database()
    booking_id = generate_prefixed_id("BK")
    created_at = utc_now()

    # --- Availability check (GAP-036) ---
    avail_error = _check_availability(
        payload.prop_id,
        payload.check_in_date,
        payload.check_out_date,
        payload.rooms,
        room_type_id=payload.room_type_id or None,
    )
    if avail_error:
        raise ValueError(f"Cannot create booking: {avail_error}")

    # --- Rate calculation (GAP-034) ---
    total_price, currency, total_nights = _calculate_total_price(
        payload.prop_id,
        payload.room_type_id or None,
        payload.check_in_date,
        payload.check_out_date,
        payload.rooms,
    )

    booking_document: dict[str, Any] = {
        "booking_id": booking_id,
        "user_id": payload.user_id,
        "prop_id": payload.prop_id,
        "status": "pending",
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
        "created_by": payload.created_by,
        "total_price": total_price,
        "currency": currency,
        "total_nights": total_nights,
        "created_at": created_at,
        "updated_at": created_at,
        "is_test": payload.is_test,
    }

    try:
        db.booking_orders.insert_one(booking_document)
    except DuplicateKeyError:
        raise ValueError("booking_id already exists, retry")

    # --- Create guest record with phone (GAP-033) ---
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
            "status": "pending",
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
            "status": "pending",
            "is_test": payload.is_test,
        }
        db.manual_reservations.insert_one(manual_document)

    return {
        "booking_id": booking_id,
        "status": "pending",
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
        "total_price": total_price,
        "currency": currency,
        "total_nights": total_nights,
    }
