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

    # ── Same-day check-in/out counts as 1 night ──
    if not dates:
        dates = [check_in_date]

    requested_nights = len(dates)

    # ── min_stay baseline from hotel_policies (hotel-wide or per-room-type) ──
    policy_filter: dict[str, object] = {"prop_id": prop_id}
    if room_type_id:
        policy_filter["room_type_id"] = room_type_id
    else:
        policy_filter["room_type_id"] = {"$in": ["", None]}
    hotel_policy = db.hotel_policies.find_one(
        policy_filter,
        {"_id": 0, "min_stay": 1, "max_stay": 1},
    )
    # Fallback: hotel-wide policy without room_type filter
    if not hotel_policy:
        hotel_policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}},
            {"_id": 0, "min_stay": 1, "max_stay": 1},
        )
    policy_min_stay = hotel_policy.get("min_stay") if hotel_policy else None
    policy_max_stay = hotel_policy.get("max_stay") if hotel_policy else None

    if policy_min_stay is not None and requested_nights < policy_min_stay:
        return (
            f"La estancia mínima para esta propiedad es de {policy_min_stay} noche(s). "
            f"Solicitaste {requested_nights} noche(s)."
        )
    if policy_max_stay is not None and requested_nights > policy_max_stay:
        return (
            f"La estancia máxima para esta propiedad es de {policy_max_stay} noche(s). "
            f"Solicitaste {requested_nights} noche(s)."
        )

    # ── min_stay / max_stay validation from hotel_rate_calendar ──
    # Only applies when hotel_policies did NOT define min_stay.
    # If the hotel configured min_stay in policies, THAT is the source of truth.
    if policy_min_stay is None:
        rate_match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}, "is_closed": {"$ne": True}}
        rate_records = list(
            db.hotel_rate_calendar.find(
                rate_match,
                {"_id": 0, "date": 1, "min_stay_nights": 1, "max_stay_nights": 1},
            )
        )
        if rate_records:
            max_min_stay = max(
                (r.get("min_stay_nights") or 1 for r in rate_records),
                default=1,
            )
            if max_min_stay > requested_nights:
                return (
                    f"La estancia mínima es de {max_min_stay} noche(s). "
                    f"Solicitaste {requested_nights} noche(s)."
                )

            non_null_max_stay = [r.get("max_stay_nights") for r in rate_records if r.get("max_stay_nights") is not None]
            if non_null_max_stay:
                min_max_stay = min(non_null_max_stay)
                if min_max_stay < requested_nights:
                    return (
                        f"La estancia máxima es de {min_max_stay} noche(s). "
                        f"Solicitaste {requested_nights} noche(s)."
                    )

    # ── Check if this is an ROH room type (pooled inventory) ──
    is_roh_booking = False
    if room_type_id:
        roh_check = db.room_types.find_one(
            {"room_type_id": room_type_id, "prop_id": prop_id},
            {"_id": 0, "is_roh": 1},
        )
        if roh_check and roh_check.get("is_roh", False):
            is_roh_booking = True

    # ── Inventory availability check ──
    if is_roh_booking:
        # ROH: sum available rooms across ALL non-ROH room types
        records = list(
            db.room_inventory_calendar.aggregate([
                {"$match": {"prop_id": prop_id, "date": {"$in": dates}, "is_roh": {"$ne": True}}},
                {"$group": {"_id": "$date", "total_available": {"$sum": "$available_rooms"}}},
                {"$sort": {"_id": 1}},
            ])
        )
        found_dates = {r["_id"]: r.get("total_available", 0) for r in records}
    else:
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
    adults: int = 2,
    children: int = 0,
    discount_percent: int | None = None,
) -> tuple[float | None, str, int, float, float, bool]:
    """Calculate booking price with occupancy and tax support.

    Returns (total_price, currency, total_nights, tax_rate, tax_amount, tax_included).
    """
    db = get_database()
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None, "USD", 0, 0.0, 0.0, False

    total_nights = max(1, (check_out - check_in).days)  # Same-day stays count as 1 night
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_nights)]
    match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}}
    if room_type_id:
        match["room_type_id"] = room_type_id

    records = list(
        db.hotel_rate_calendar.find(match, {"_id": 0, "date": 1, "rate_amount": 1, "currency": 1}).sort("date", 1)
    )
    if not records:
        return None, "USD", total_nights, 0.0, 0.0, False

    currency = records[0].get("currency", "USD")

    # ── Occupancy-based pricing ──
    rate_plan_id = records[0].get("rate_plan_id", "")
    base_occupancy = 2
    extra_adult_price = 0.0
    extra_child_price = 0.0
    tax_included = False
    tax_rate = 0.0
    if rate_plan_id:
        plan = db.rate_plans.find_one(
            {"rate_plan_id": rate_plan_id},
            {"_id": 0, "base_occupancy": 1, "extra_adult_price": 1, "extra_child_price": 1,
             "tax_included": 1, "tax_rate": 1},
        )
        if plan:
            base_occupancy = int(plan.get("base_occupancy") or 2)
            extra_adult_price = float(plan.get("extra_adult_price") or 0)
            extra_child_price = float(plan.get("extra_child_price") or 0)
            tax_included = bool(plan.get("tax_included", False))
            tax_rate = float(plan.get("tax_rate") or 0)

    # ── Per-date tax overrides from calendar ──
    # Use first record's tax override if present (all dates in same plan should have same values)
    first_record_tax = records[0].get("tax_included")
    first_record_tax_rate = records[0].get("tax_rate")
    if first_record_tax is not None:
        tax_included = bool(first_record_tax)
    if first_record_tax_rate is not None:
        tax_rate = float(first_record_tax_rate)

    total_extra_adults = max(0, adults - base_occupancy * rooms)
    total_extra_children = max(0, children)

    subtotal = 0.0
    for r in records:
        night_rate = float(r.get("rate_amount", 0))
        night_total = night_rate * rooms + total_extra_adults * extra_adult_price + total_extra_children * extra_child_price
        subtotal += night_total

    if discount_percent and discount_percent > 0:
        subtotal = round(subtotal * (1 - discount_percent / 100), 2)

    # ── Tax calculation ──
    tax_amount = 0.0
    if tax_rate > 0 and subtotal > 0:
        if tax_included:
            # Tax is already embedded in the rate: extract it
            # subtotal = final_price, tax = subtotal - subtotal/(1+tax_rate/100)
            tax_amount = round(subtotal - subtotal / (1 + tax_rate / 100), 2)
        else:
            tax_amount = round(subtotal * tax_rate / 100, 2)

    total_price = round(subtotal + tax_amount, 2) if not tax_included else round(subtotal, 2)
    if tax_included:
        # With tax inclusive, the subtotal IS the final price
        total_price = round(subtotal, 2)
        # Recalculate tax_amount from the inclusive price
        tax_amount = round(total_price - total_price / (1 + tax_rate / 100), 2) if tax_rate > 0 else 0.0

    return round(total_price, 2), currency, total_nights, round(tax_rate, 2), round(tax_amount, 2), tax_included


def _resolve_season_id(prop_id: int, check_in_date: str) -> str:
    """Determine the applicable season_id for a given check-in date.

    Scans the hotel's `rate_rules` (seasonal rules) and returns the
    name/slug of the first rule whose date range covers the check-in date.
    If no seasonal rule matches, returns ``""`` (default / general season).
    """
    if not prop_id or not check_in_date:
        return ""
    db = get_database()
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return ""
    rules = list(db.rate_rules.find(
        {"prop_id": prop_id},
        {"_id": 0, "name": 1, "start_date": 1, "end_date": 1},
    ).sort([("start_date", 1)]))
    for rule in rules:
        try:
            r_start = datetime.strptime(str(rule.get("start_date", "")), "%Y-%m-%d").date()
            r_end = datetime.strptime(str(rule.get("end_date", "")), "%Y-%m-%d").date()
            if r_start <= check_in <= r_end:
                slug = str(rule.get("name", "")).strip().lower().replace(" ", "_")
                return slug if slug else ""
        except (ValueError, TypeError):
            continue
    return ""


def _validate_deposit(
    prop_id: int,
    total_price: float | None,
    season_id: str = "",
    room_type_id: str = "",
    manual_reservation: bool = False,
) -> str | None:
    """Check if the hotel policy requires a minimum deposit.

    Respects seasonal policies by matching ``season_id``.
    Falls back to general (non-seasonal) policies if no seasonal match is found.

    Returns an error message if a deposit is required but not met,
    or None if the booking passes validation.
    """
    if manual_reservation:
        return None
    db = get_database()
    # Try to find a policy matching the season + room type first
    policy_filter: dict[str, object] = {"prop_id": prop_id}
    if room_type_id:
        policy_filter["room_type_id"] = room_type_id
    else:
        policy_filter["room_type_id"] = {"$in": ["", None]}
    if season_id:
        policy_filter["season_id"] = season_id
    else:
        policy_filter["season_id"] = {"$in": ["", None]}
    policy = db.hotel_policies.find_one(
        policy_filter,
        {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
    )
    # Fallback: try hotel-wide policy without season
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "season_id": {"$in": ["", None]}},
            {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
        )
    if not policy:
        return None
    deposit_required = policy.get("deposit_required", False)
    deposit_percent = int(policy.get("deposit_percent", 0) or 0)
    if not deposit_required or deposit_percent <= 0:
        return None
    if total_price is None or total_price <= 0:
        return "No se puede calcular el depósito mínimo: precio total no disponible."
    min_deposit = round(total_price * deposit_percent / 100, 2)
    return (
        f"Esta propiedad requiere un depósito mínimo del {deposit_percent}% "
        f"(${min_deposit:.2f}) para confirmar la reserva. "
        "Por favor, proporcione la garantía correspondiente."
    )


def _generate_amenity_charges(
    *,
    booking_id: str,
    prop_id: int,
    selected_amenities: list[str],
) -> list[dict[str, Any]]:
    """Automatically generate additional charges for paid amenities.

    Looks up the property's amenity prices from ``hotel_content_pages.amenity_prices``
    (with fallback to ``_amenity_unit_price`` defaults) and creates an additional
    charge for each selected amenity whose unit price > 0.

    Returns a list of the charge documents created.
    """
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
            continue  # Free amenity, no charge
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
    # Validate check-in/out times against hotel policies
    from ..validation import _validate_policy_times
    time_errors = _validate_policy_times(payload.prop_id, payload.check_in_time, payload.check_out_time)
    if time_errors:
        raise ValueError("; ".join(time_errors))

    avail_error = _check_availability(
        payload.prop_id, payload.check_in_date, payload.check_out_date,
        payload.rooms, payload.room_type_id,
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
    )

    # ── Corporate contract pricing ──
    contract_data = None
    contract_id = ""
    pricing_source = ""
    if payload.contract_code:
        from src.app.modules.partner.services.rates.contracts import validate_contract_code, apply_contract_pricing
        contract_error, contract_data = validate_contract_code(
            payload.contract_code,
            payload.prop_id,
            rate_plan_id="",
            room_type_id=payload.room_type_id,
        )
        if contract_error:
            raise ValueError(contract_error)
        if contract_data:
            contract_id = contract_data.get("contract_id", "")
            adjusted_price, pricing_source = apply_contract_pricing(
                total_price, total_nights, contract_data,
            )
            if pricing_source:
                total_price = adjusted_price

    # ── Resolve season_id from check-in date ──
    season_id = payload.season_id or _resolve_season_id(payload.prop_id, payload.check_in_date)

    # ── Minimum deposit validation (season-aware) ──
    deposit_error = _validate_deposit(
        payload.prop_id, total_price,
        season_id=season_id,
        room_type_id=payload.room_type_id,
        manual_reservation=manual_reservation,
    )
    if deposit_error:
        raise ValueError(deposit_error)

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
        "original_total_price": (total_price / (1 - discount_percent / 100)) if discount_percent and total_price else None,        "created_by": payload.created_by, "created_at": created_at, "updated_at": created_at,
        "is_test": payload.is_test,
        "selected_amenities": payload.selected_amenities,
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

        total_price, currency, total_nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
            int(booking.get("prop_id", 0)), new_room_type, new_check_in, new_check_out, new_rooms,
            adults=int(booking.get("adults", 2)), children=int(booking.get("children", 0)),
        )

        update_fields["total_price"] = total_price
        update_fields["currency"] = currency or booking.get("currency", "USD")
        update_fields["total_nights"] = total_nights
        update_fields["tax_included"] = tax_included
        update_fields["tax_rate"] = tax_rate
        update_fields["tax_amount"] = tax_amount

        # Re-resolve season_id if dates changed
        new_season_id = _resolve_season_id(
            int(booking.get("prop_id", 0)), new_check_in,
        )
        if new_season_id:
            update_fields["season_id"] = new_season_id

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": update_fields})

    # ── Amenity selection change ──
    if selected_amenities is not None:
        prop_id = int(booking.get("prop_id", 0))
        # Store new selection
        db.booking_orders.update_one(
            {"booking_id": booking_id},
            {"$set": {"selected_amenities": selected_amenities}},
        )
        # Remove existing amenity charges for this booking
        db.additional_charges.delete_many({
            "booking_id": booking_id,
            "concept": {"$regex": "^Amenidad:"},
        })
        # Regenerate charges for newly selected amenities
        _generate_amenity_charges(
            booking_id=booking_id, prop_id=prop_id,
            selected_amenities=selected_amenities,
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
