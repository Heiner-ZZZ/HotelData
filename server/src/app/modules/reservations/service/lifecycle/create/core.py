"""Core booking creation and modification functions."""

from __future__ import annotations

import logging
from typing import Any

from pymongo.errors import DuplicateKeyError

from src.database.connection import get_database
from .._helpers import ReservationInput, generate_prefixed_id, utc_now
from ...collections import ensure_reservation_collections
from ...validation import validate_reservation_input
from src.app.modules.reservations.service.lifecycle.create._availability import _check_availability
from src.app.modules.reservations.service.lifecycle.create._pricing import _calculate_total_price, _resolve_season_id
from src.app.modules.reservations.service.lifecycle.create._validation import _validate_deposit, validate_coupon_code
from src.app.core.timezone import local_today
from src.app.modules.reservations.service.lifecycle.create._amenities import _generate_amenity_charges

logger = logging.getLogger(__name__)


def _get_cancellation_policy_text(prop_id: int) -> str | None:
    """Retrieve cancellation policy text from hotel_policies."""
    try:
        db = get_database()
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_policy": 1},
        )
        if policy and policy.get("cancellation_policy"):
            return policy["cancellation_policy"]
    except Exception:
        pass
    return None


def create_booking(payload: ReservationInput, *, manual_reservation: bool = False) -> dict[str, Any]:
    ensure_reservation_collections()
    errors = validate_reservation_input(payload)
    if errors:
        raise ValueError("; ".join(errors))
    from ...validation import _validate_policy_times
    time_errors = _validate_policy_times(payload.prop_id, payload.check_in_time, payload.check_out_time)
    if time_errors:
        raise ValueError("; ".join(time_errors))

    avail_error = _check_availability(
        payload.prop_id, payload.check_in_date, payload.check_out_date,
        payload.rooms, payload.room_type_id, rate_plan_id=payload.rate_plan_id,
    )
    if avail_error:
        raise ValueError(f"Cannot create booking: {avail_error}")

    coupon_error, discount_percent = validate_coupon_code(payload.coupon_code, payload.prop_id)
    if coupon_error:
        raise ValueError(coupon_error)

    total_price, currency, total_nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
        payload.prop_id, payload.room_type_id,
        payload.check_in_date, payload.check_out_date,
        payload.rooms,
        adults=payload.adults, children=payload.children,
        discount_percent=discount_percent,
        rate_plan_id=payload.rate_plan_id or None,
    )

    # ── Corporate contract pricing ──
    contract_id = ""
    pricing_source = ""
    if payload.contract_code:
        from src.app.modules.partner.services.rates.contracts import validate_contract_code, apply_contract_pricing
        contract_error, cdata = validate_contract_code(
            payload.contract_code, payload.prop_id,
            rate_plan_id="", room_type_id=payload.room_type_id,
        )
        if contract_error:
            raise ValueError(contract_error)
        if cdata:
            contract_id = cdata.get("contract_id", "")
            adjusted_price, pricing_source = apply_contract_pricing(total_price, total_nights, cdata)
            if pricing_source:
                total_price = adjusted_price

    # ── Resolve season_id ──
    season_id = payload.season_id or _resolve_season_id(payload.prop_id, payload.check_in_date)

    # ── Minimum deposit validation ──
    deposit_error = _validate_deposit(
        payload.prop_id, total_price,
        season_id=season_id, room_type_id=payload.room_type_id,
        rate_plan_id=payload.rate_plan_id,
        manual_reservation=manual_reservation,
    )
    if deposit_error:
        raise ValueError(deposit_error)

    db = get_database()
    booking_id = generate_prefixed_id("BK")
    transaction_id = generate_prefixed_id("TXN")
    created_at = utc_now()
    booking_status = "confirmed" if manual_reservation else "pending"
    payment_status = "pending"
    payment_method = payload.payment_method
    card_last4 = payload.card_last4
    if payment_method or card_last4:
        payment_status = "paid"
    booking_document = {
        "booking_id": booking_id, "user_id": payload.user_id,
        "prop_id": payload.prop_id, "status": booking_status,
        "booking_source": payload.source, "guest_name": payload.guest_name,
        "guest_email": payload.guest_email, "guest_phone": payload.guest_phone,
        "room_type_id": payload.room_type_id,
        "check_in_date": payload.check_in_date, "check_out_date": payload.check_out_date,
        "check_in_time": payload.check_in_time, "check_out_time": payload.check_out_time,
        "adults": payload.adults, "children": payload.children, "rooms": payload.rooms,
        "comment": payload.comment, "special_requests": payload.special_requests,
        "total_price": total_price, "currency": currency, "total_nights": total_nights,
        "coupon_code": payload.coupon_code.strip().upper() if payload.coupon_code else "",
        "discount_percent": discount_percent,
        "contract_code": payload.contract_code.strip().upper() if payload.contract_code else "",
        "contract_id": contract_id,
        "pricing_source": pricing_source,
        "season_id": season_id,
        "tax_included": tax_included,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "original_total_price": (total_price / (1 - discount_percent / 100)) if discount_percent and total_price else None,
        "created_by": payload.created_by, "created_at": created_at, "updated_at": created_at,
        "is_test": payload.is_test,
        "rate_plan_id": payload.rate_plan_id,
        "selected_amenities": payload.selected_amenities,
        # Payment / transaction fields (Phase 1)
        "transaction_id": transaction_id,
        "payment_method": payment_method,
        "card_last4": card_last4,
        "payment_status": payment_status,
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

    # ── Generate additional charges for paid amenities ──
    amenity_charges = _generate_amenity_charges(
        booking_id=booking_id, prop_id=payload.prop_id,
        selected_amenities=payload.selected_amenities,
        rate_plan_id=payload.rate_plan_id,
    )
    amenity_charges_summary = [
        {"concept": c.get("concept", ""), "amount": c.get("amount", 0), "total": c.get("total", c.get("amount", 0))}
        for c in amenity_charges
    ]

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

    # ── Cancellation policy ──
    cancellation_policy = _get_cancellation_policy_text(payload.prop_id)

    return {
        "booking_id": booking_id, "status": booking_status,
        "season_id": season_id,
        "total_price": total_price, "currency": currency, "total_nights": total_nights,
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
        "hotel_label": hotel_label, "hotel_prop_id": payload.prop_id,
        "room_type_name": room_type_name,
        "check_in_date": payload.check_in_date, "check_out_date": payload.check_out_date,
        "rooms": payload.rooms, "adults": payload.adults, "children": payload.children,
        "guest_name": payload.guest_name, "guest_email": payload.guest_email,
        "amenity_charges": amenity_charges_summary,
        # Payment / transaction (Phase 1)
        "transaction_id": transaction_id,
        "payment_method": payment_method,
        "card_last4": card_last4,
        "payment_status": payment_status,
        # Policies (Phase 4)
        "cancellation_policy": cancellation_policy,
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
    changed_by: str = "web",
    selected_amenities: list[str] | None = None,
) -> dict[str, Any]:
    from ...validation import validate_date_format

    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise ValueError("Booking not found")

    current_status = booking.get("status", "")
    current_stay_status = booking.get("stay_status", "")

    only_datetime = (
        check_in_date is not None or check_in_time is not None
    ) and all(x is None for x in (check_out_date, room_type_id, rooms, comment))

    if current_status in ("cancelled", "rejected"):
        raise ValueError(f"Cannot modify a booking with status '{current_status}'")
    if current_stay_status == "checked_out":
        raise ValueError("No se puede modificar una reserva que ya ha finalizado (Check-out completado).")

    today_str = local_today()
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

    now = utc_now()
    update_fields: dict[str, Any] = {
        "check_in_date": new_check_in,
        "check_out_date": new_check_out,
        "room_type_id": new_room_type,
        "rooms": new_rooms,
        "comment": new_comment,
        "updated_at": now,
    }
    if check_in_time is not None:
        update_fields["check_in_time"] = new_check_in_time

    if current_stay_status in ("checked_in", "checked_out"):
        total_price = booking.get("total_price")
        currency = booking.get("currency", "USD")
        total_nights = booking.get("total_nights", 0)
    else:
        avail_error = _check_availability(
            int(booking.get("prop_id", 0)), new_check_in, new_check_out, new_rooms, new_room_type,
            rate_plan_id=booking.get("rate_plan_id", ""),
        )
        if avail_error:
            raise ValueError(f"Cannot modify booking: {avail_error}")

        total_price, currency, total_nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
            int(booking.get("prop_id", 0)), new_room_type, new_check_in, new_check_out, new_rooms,
            adults=int(booking.get("adults", 2)), children=int(booking.get("children", 0)),
        )
        update_fields.update({
            "total_price": total_price,
            "currency": currency or booking.get("currency", "USD"),
            "total_nights": total_nights,
            "tax_included": tax_included,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
        })
        new_season_id = _resolve_season_id(int(booking.get("prop_id", 0)), new_check_in)
        if new_season_id:
            update_fields["season_id"] = new_season_id

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": update_fields})

    # ── Amenity selection change ──
    if selected_amenities is not None:
        prop_id = int(booking.get("prop_id", 0))
        db.booking_orders.update_one(
            {"booking_id": booking_id},
            {"$set": {"selected_amenities": selected_amenities}},
        )
        db.additional_charges.delete_many({
            "booking_id": booking_id,
            "concept": {"$regex": "^Amenidad:"},
        })
        _generate_amenity_charges(
            booking_id=booking_id, prop_id=prop_id,
            selected_amenities=selected_amenities,
            rate_plan_id=booking.get("rate_plan_id"),
        )

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
