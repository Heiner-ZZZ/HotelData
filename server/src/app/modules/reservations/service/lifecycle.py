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

# ═══════════════════════════════════════════════
# Room Guests (per-room passenger manifest)
# ═══════════════════════════════════════════════

ROOM_GUESTS = "booking_room_guests"


def get_room_guests(booking_id: str) -> list[dict[str, Any]]:
    """Get per-room guest data for a booking."""
    db = get_database()
    items = list(db[ROOM_GUESTS].find({"booking_id": booking_id}, {"_id": 0}).sort("room_index", 1))
    return items


def save_room_guests(booking_id: str, room_guests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace all per-room guest data for a booking.

    Each room entry: {room_index, guests: [{guest_name, guest_email, guest_phone, age, is_child, is_primary_for_room}]}
    """
    db = get_database()
    ensure_reservation_collections()
    now = utc_now()

    # Validate booking exists
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise ValueError("Booking not found")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError("Cannot modify room guests for cancelled/rejected booking")

    max_rooms = int(booking.get("rooms", 1))
    for entry in room_guests:
        ri = int(entry.get("room_index", 0))
        if ri < 0 or ri >= max_rooms:
            raise ValueError(f"room_index {ri} out of range (0-{max_rooms - 1})")

    # Replace all room guests for this booking
    db[ROOM_GUESTS].delete_many({"booking_id": booking_id})
    docs = []
    for entry in room_guests:
        doc = {
            "booking_id": booking_id,
            "room_index": int(entry.get("room_index", 0)),
            "guests": [
                {
                    "guest_name": g.get("guest_name", "").strip(),
                    "guest_email": g.get("guest_email", "").strip(),
                    "guest_phone": g.get("guest_phone", "").strip(),
                    "age": int(g["age"]) if g.get("age") is not None else None,
                    "is_child": bool(g.get("is_child", False)),
                    "is_primary_for_room": bool(g.get("is_primary_for_room", False)),
                }
                for g in entry.get("guests", [])
            ],
            "created_at": now,
            "updated_at": now,
            "is_test": bool(booking.get("is_test")),
        }
        docs.append(doc)
    if docs:
        db[ROOM_GUESTS].insert_many(docs)

    return get_room_guests(booking_id)


def get_check_in_status(booking_id: str) -> dict[str, Any]:
    """Get check-in readiness status for a booking."""
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        return {"status": "unknown", "message": "Booking not found"}

    total_rooms = int(booking.get("rooms", 1))
    room_guests = list(db[ROOM_GUESTS].find({"booking_id": booking_id}).sort("room_index", 1))

    rooms_with_data = len(room_guests)
    all_complete = True
    per_room = []
    for ri in range(total_rooms):
        room_doc = next((r for r in room_guests if r.get("room_index") == ri), None)
        if room_doc:
            guest_count = len(room_doc.get("guests", []))
            per_room.append({"room_index": ri, "guest_count": guest_count, "complete": guest_count > 0})
            if guest_count == 0:
                all_complete = False
        else:
            per_room.append({"room_index": ri, "guest_count": 0, "complete": False})
            all_complete = False

    return {
        "booking_id": booking_id,
        "total_rooms": total_rooms,
        "rooms_with_data": rooms_with_data,
        "all_complete": all_complete,
        "per_room": per_room,
    }


# ═══════════════════════════════════════════════
# Booking Modification (dates, rooms, etc.)
# ═══════════════════════════════════════════════


def modify_booking(
    booking_id: str,
    *,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
    room_type_id: str | None = None,
    rooms: int | None = None,
    comment: str | None = None,
    changed_by: str = "angular_api",
) -> dict[str, Any]:
    """Modify a booking's dates, room type, room count, or comment.

    Only allowed for pending or confirmed bookings.
    Re-checks availability and re-calculates price for changed fields.
    Records a status history entry.
    """
    from .validation import validate_date_format

    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise ValueError("Booking not found")

    current_status = booking.get("status", "")
    if current_status in ("cancelled", "rejected", "checked_in", "checked_out"):
        raise ValueError(f"Cannot modify a booking with status '{current_status}'")

    # Start with current values
    new_check_in = check_in_date if check_in_date is not None else booking.get("check_in_date", "")
    new_check_out = check_out_date if check_out_date is not None else booking.get("check_out_date", "")
    new_room_type = room_type_id if room_type_id is not None else booking.get("room_type_id", "")
    new_rooms = rooms if rooms is not None else int(booking.get("rooms", 1))
    new_comment = comment if comment is not None else booking.get("comment", "")

    # Validate dates if changed
    if check_in_date or check_out_date:
        errors = validate_date_format(new_check_in, new_check_out)
        if errors:
            raise ValueError("; ".join(errors))

    # Check availability for the new configuration
    avail_error = _check_availability(
        int(booking.get("prop_id", 0)),
        new_check_in,
        new_check_out,
        new_rooms,
        new_room_type,
    )
    if avail_error:
        raise ValueError(f"Cannot modify booking: {avail_error}")

    # Recalculate price
    total_price, currency, total_nights = _calculate_total_price(
        int(booking.get("prop_id", 0)),
        new_room_type,
        new_check_in,
        new_check_out,
        new_rooms,
    )

    now = utc_now()
    update_fields = {
        "check_in_date": new_check_in,
        "check_out_date": new_check_out,
        "room_type_id": new_room_type,
        "rooms": new_rooms,
        "comment": new_comment,
        "total_price": total_price,
        "currency": currency or booking.get("currency", "USD"),
        "total_nights": total_nights,
        "updated_at": now,
    }

    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": update_fields},
    )

    # Record modification in status history
    changed_fields = []
    if check_in_date:
        changed_fields.append("fechas")
    if room_type_id:
        changed_fields.append("tipo habitacion")
    if rooms:
        changed_fields.append("habitaciones")
    if comment:
        changed_fields.append("comentario")
    reason = f"modificado: {', '.join(changed_fields)}" if changed_fields else "modificado"

    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": current_status,
        "changed_at": now,
        "reason": reason,
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test")),
    })

    if not booking.get("is_test") and booking.get("guest_email"):
        from src.app.modules.reservations.notifications import notify_guest_status_change
        try:
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=booking.get("guest_email", ""),
                new_status="modified",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=new_check_in,
                check_out_date=new_check_out,
                total_price=total_price,
                currency=currency or booking.get("currency", "USD"),
                total_nights=total_nights,
            )
        except Exception:
            pass

    return {
        "booking_id": booking_id,
        "status": current_status,
        "total_price": total_price,
        "currency": currency or booking.get("currency", "USD"),
        "total_nights": total_nights,
    }


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
    discount_percent: int | None = None,
) -> tuple[float | None, str, int]:
    """Calculate total price from hotel_rate_calendar.

    Optionally applies a percentage discount.
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
    # Apply discount if applicable
    if discount_percent and discount_percent > 0:
        total = round(total * (1 - discount_percent / 100), 2)
    return total, currency, total_nights


def validate_coupon_code(coupon_code: str, prop_id: int) -> tuple[str | None, int | None]:
    """Validate a coupon code against the coupon_codes collection.

    Returns (error_message, discount_percent).
    If valid, error_message is None and discount_percent is the discount.
    """
    if not coupon_code:
        return None, None
    db = get_database()
    code = coupon_code.strip().upper()
    coupon = db.coupon_codes.find_one({"coupon_code": code, "prop_id": prop_id, "is_active": True})
    if not coupon:
        # Try without prop_id filter (global coupon)
        coupon = db.coupon_codes.find_one({"coupon_code": code, "is_active": True})
        if not coupon:
            return f"Código promocional '{coupon_code}' no válido.", None
        # Check if the coupon's campaign is for this property or global
        campaign = db.promotion_campaigns.find_one({"campaign_id": coupon.get("campaign_id")})
        if campaign:
            campaign_prop = campaign.get("prop_id")
            if campaign_prop and int(campaign_prop) != prop_id:
                return f"Este código no aplica para este hotel.", None

    discount_percent = coupon.get("discount_percent", 0)
    if not discount_percent or discount_percent <= 0:
        return "El código promocional no tiene un descuento válido.", None

    return None, int(discount_percent)


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

    # Validate coupon code if provided
    coupon_error, discount_percent = validate_coupon_code(payload.coupon_code, payload.prop_id)
    if coupon_error:
        raise ValueError(coupon_error)

    total_price, currency, total_nights = _calculate_total_price(
        payload.prop_id,
        payload.room_type_id,
        payload.check_in_date,
        payload.check_out_date,
        payload.rooms,
        discount_percent=discount_percent,
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
        "special_requests": payload.special_requests,
        "total_price": total_price,
        "currency": currency,
        "total_nights": total_nights,
        "coupon_code": payload.coupon_code.strip().upper() if payload.coupon_code else "",
        "discount_percent": discount_percent,
        "original_total_price": (total_price / (1 - discount_percent / 100)) if discount_percent and total_price else None,
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

    # Enrich response with context for confirmation page
    hotel_label = f"Hotel {payload.prop_id}"
    room_type_name = None
    try:
        rt = db.room_types.find_one({"room_type_id": payload.room_type_id}, {"_id": 0, "name": 1})
        if rt:
            room_type_name = rt.get("name")
        hc = db.dim_hotels.find_one({"prop_id": payload.prop_id}, {"_id": 0, "display_name": 1})
        if hc and hc.get("display_name"):
            hotel_label = hc["display_name"]
    except Exception:
        pass

    return {
        "booking_id": booking_id,
        "status": booking_status,
        "total_price": total_price,
        "currency": currency,
        "total_nights": total_nights,
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
        "hotel_label": hotel_label,
        "hotel_prop_id": payload.prop_id,
        "room_type_name": room_type_name,
        "check_in_date": payload.check_in_date,
        "check_out_date": payload.check_out_date,
        "rooms": payload.rooms,
        "adults": payload.adults,
        "children": payload.children,
        "guest_name": payload.guest_name,
        "guest_email": payload.guest_email,
    }
