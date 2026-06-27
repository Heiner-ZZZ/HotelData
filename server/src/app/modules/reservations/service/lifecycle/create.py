"""Booking creation, modification, availability checks and price calculation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from src.database.connection import get_database
from .._helpers import ReservationInput, generate_prefixed_id, utc_now
from ..collections import ensure_reservation_collections
from ..validation import validate_reservation_input

logger = logging.getLogger(__name__)


def _check_availability(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str = "",
) -> str | None:
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "Invalid date format; expected YYYY-MM-DD"

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    if not dates:
        return "check_out_date must be after check_in_date"

    match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}}
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
    match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}}
    if room_type_id:
        match["room_type_id"] = room_type_id

    records = list(
        db.hotel_rate_calendar.find(match, {"_id": 0, "date": 1, "rate_amount": 1, "currency": 1}).sort("date", 1)
    )
    if not records:
        return None, "USD", total_nights

    currency = records[0].get("currency", "USD")
    total = sum(r.get("rate_amount", 0) for r in records) * rooms
    if discount_percent and discount_percent > 0:
        total = round(total * (1 - discount_percent / 100), 2)
    return total, currency, total_nights


def validate_coupon_code(coupon_code: str, prop_id: int) -> tuple[str | None, int | None]:
    if not coupon_code:
        return None, None
    db = get_database()
    code = coupon_code.strip().upper()
    coupon = db.coupon_codes.find_one({"coupon_code": code, "prop_id": prop_id, "is_active": True})
    if not coupon:
        coupon = db.coupon_codes.find_one({"coupon_code": code, "is_active": True})
        if not coupon:
            return f"Código promocional '{coupon_code}' no válido.", None
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
        payload.prop_id, payload.check_in_date, payload.check_out_date,
        payload.rooms, payload.room_type_id,
    )
    if avail_error:
        raise ValueError(f"Cannot create booking: {avail_error}")

    coupon_error, discount_percent = validate_coupon_code(payload.coupon_code, payload.prop_id)
    if coupon_error:
        raise ValueError(coupon_error)

    total_price, currency, total_nights = _calculate_total_price(
        payload.prop_id, payload.room_type_id,
        payload.check_in_date, payload.check_out_date,
        payload.rooms, discount_percent=discount_percent,
    )

    db = get_database()
    booking_id = generate_prefixed_id("BK")
    created_at = utc_now()
    booking_status = "confirmed" if manual_reservation else "pending"
    booking_document = {
        "booking_id": booking_id, "user_id": payload.user_id,
        "prop_id": payload.prop_id, "status": booking_status,
        "booking_source": payload.source, "guest_name": payload.guest_name,
        "guest_email": payload.guest_email, "guest_phone": payload.guest_phone,
        "room_type_id": payload.room_type_id,
        "check_in_date": payload.check_in_date, "check_out_date": payload.check_out_date,
        "adults": payload.adults, "children": payload.children, "rooms": payload.rooms,
        "comment": payload.comment, "special_requests": payload.special_requests,
        "total_price": total_price, "currency": currency, "total_nights": total_nights,
        "coupon_code": payload.coupon_code.strip().upper() if payload.coupon_code else "",
        "discount_percent": discount_percent,
        "original_total_price": (total_price / (1 - discount_percent / 100)) if discount_percent and total_price else None,
        "created_by": payload.created_by, "created_at": created_at, "updated_at": created_at,
        "is_test": payload.is_test,
    }
    try:
        db.booking_orders.insert_one(booking_document)
    except DuplicateKeyError:
        raise ValueError("booking_id already exists, retry")

    db.booking_guests.insert_one({
        "booking_id": booking_id, "guest_name": payload.guest_name,
        "guest_email": payload.guest_email, "guest_phone": payload.guest_phone,
        "cedula": payload.cedula,
        "is_primary": True, "created_at": created_at, "is_test": payload.is_test,
    })
    db.booking_status_history.insert_one({
        "booking_id": booking_id, "status": booking_status,
        "changed_at": created_at, "reason": "manual_reservation" if manual_reservation else "initial_request",
        "changed_by": payload.created_by or payload.source, "is_test": payload.is_test,
    })

    manual_document = None
    if manual_reservation:
        manual_reservation_id = generate_prefixed_id("MR")
        manual_document = {
            "manual_reservation_id": manual_reservation_id, "booking_id": booking_id,
            "prop_id": payload.prop_id, "created_at": created_at,
            "created_by": payload.created_by or "partner_manual",
            "note": payload.comment, "status": "pending", "is_test": payload.is_test,
        }
        db.manual_reservations.insert_one(manual_document)

    try:
        from src.app.modules.reservations.notifications import notify_staff_new_booking
        notify_staff_new_booking(
            prop_id=payload.prop_id, booking_id=booking_id,
            guest_name=payload.guest_name, guest_email=payload.guest_email,
            check_in_date=payload.check_in_date, check_out_date=payload.check_out_date,
            adults=payload.adults, children=payload.children, rooms=payload.rooms,
            total_price=total_price, currency=currency, total_nights=total_nights,
            comment=payload.comment,
        )
    except Exception:
        logger.exception("Failed to notify staff for booking %s", booking_id)

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
        "booking_id": booking_id, "status": booking_status,
        "total_price": total_price, "currency": currency, "total_nights": total_nights,
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
        "hotel_label": hotel_label, "hotel_prop_id": payload.prop_id,
        "room_type_name": room_type_name,
        "check_in_date": payload.check_in_date, "check_out_date": payload.check_out_date,
        "rooms": payload.rooms, "adults": payload.adults, "children": payload.children,
        "guest_name": payload.guest_name, "guest_email": payload.guest_email,
    }


def modify_booking(
    booking_id: str,
    *,
    check_in_date: str | None = None,
    check_in_time: str | None = None,
    check_out_date: str | None = None,
    room_type_id: str | None = None,
    rooms: int | None = None,
    comment: str | None = None,
    changed_by: str = "angular_api",
) -> dict[str, Any]:
    from ..validation import validate_date_format

    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise ValueError("Booking not found")

    current_status = booking.get("status", "")
    current_stay_status = booking.get("stay_status", "")

    # Determine what's changing
    only_datetime = (
        check_in_date is not None or check_in_time is not None
    ) and all(x is None for x in (check_out_date, room_type_id, rooms, comment))

    # Blocked statuses
    if current_status in ("cancelled", "rejected"):
        raise ValueError(f"Cannot modify a booking with status '{current_status}'")
    if current_stay_status == "checked_out":
        raise ValueError("No se puede modificar una reserva que ya ha finalizado (Check-out completado).")
    
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today_str >= booking.get("check_out_date", ""):
        raise ValueError("No se puede modificar una reserva cuyas fechas de estancia ya han pasado o finalizado.")

    if current_stay_status == "checked_in" and not only_datetime:
        raise ValueError(f"Cannot modify booking '{booking_id}' — stay status is 'checked_in'. Only date/time can be edited.")

    new_check_in = check_in_date if check_in_date is not None else booking.get("check_in_date", "")
    new_check_out = check_out_date if check_out_date is not None else booking.get("check_out_date", "")
    new_room_type = room_type_id if room_type_id is not None else booking.get("room_type_id", "")
    new_rooms = rooms if rooms is not None else int(booking.get("rooms", 1))
    new_comment = comment if comment is not None else booking.get("comment", "")
    new_check_in_time = booking.get("check_in_time", "")
    if check_in_time is not None:
        new_check_in_time = check_in_time

    if check_in_date or check_out_date:
        errors = validate_date_format(new_check_in, new_check_out)
        if errors:
            raise ValueError("; ".join(errors))

    # For checked-in/checked-out bookings that only change date/time, skip availability check
    if current_stay_status in ("checked_in", "checked_out"):
        # Guest is already in-house — no need to re-check availability or recalc price
        total_price = booking.get("total_price")
        currency = booking.get("currency", "USD")
        total_nights = booking.get("total_nights", 0)
    else:
        avail_error = _check_availability(
            int(booking.get("prop_id", 0)), new_check_in, new_check_out, new_rooms, new_room_type,
        )
        if avail_error:
            raise ValueError(f"Cannot modify booking: {avail_error}")

        total_price, currency, total_nights = _calculate_total_price(
            int(booking.get("prop_id", 0)), new_room_type, new_check_in, new_check_out, new_rooms,
        )

    now = utc_now()
    update_fields: dict[str, Any] = {
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
    if check_in_time is not None:
        update_fields["check_in_time"] = new_check_in_time

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": update_fields})

    changed_fields = []
    if check_in_date:
        changed_fields.append("fechas")
    if check_in_time is not None:
        changed_fields.append("hora check-in")
    if room_type_id:
        changed_fields.append("tipo habitacion")
    if rooms:
        changed_fields.append("habitaciones")
    if comment:
        changed_fields.append("comentario")
    reason = f"modificado: {', '.join(changed_fields)}" if changed_fields else "modificado"

    db.booking_status_history.insert_one({
        "booking_id": booking_id, "status": current_status,
        "changed_at": now, "reason": reason, "changed_by": changed_by,
        "is_test": bool(booking.get("is_test")),
    })

    if not booking.get("is_test") and booking.get("guest_email"):
        try:
            from src.app.modules.reservations.notifications import notify_guest_status_change
            notify_guest_status_change(
                booking_id=booking_id, guest_name=booking.get("guest_name", ""),
                guest_email=booking.get("guest_email", ""), new_status="modified",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=new_check_in, check_out_date=new_check_out,
                total_price=total_price, currency=currency or booking.get("currency", "USD"),
                total_nights=total_nights,
            )
        except Exception:
            pass

    return {
        "booking_id": booking_id, "status": current_status,
        "total_price": total_price, "currency": currency or booking.get("currency", "USD"),
        "total_nights": total_nights,
    }
