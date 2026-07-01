"""Management operations routes — check-in and check-out endpoints."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from pymongo import ASCENDING

from src.app.modules.reservations.service import (
    list_check_ins, list_check_outs, list_check_in_dates,
    list_check_out_dates, complete_check_in, complete_check_out,
    get_check_in_detail, save_check_in_detail,
    get_check_out_detail, save_check_out_detail,
)
from src.app.modules.reservations.service._helpers import utc_now
from src.app.modules.reservations.service._checkinout import update_check_in_datetime
from src.app.modules.housekeeping.schemas import AdditionalChargeCreate
from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge
from src.app.security.dependencies import require_login
from src.database.connection import get_database

_logger = logging.getLogger(__name__)

management_api_router = APIRouter(prefix="/api/management", tags=["management-operations-api"])


@management_api_router.get("/check-ins/dates")
def check_in_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_check_in_dates(prop_id=prop_id)


@management_api_router.get("/check-ins")
def check_ins_api(
    operation_date: str = Query(..., alias="date"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_check_ins(operation_date=operation_date, prop_id=prop_id, user=current_user)


@management_api_router.patch("/check-ins/{booking_id}/update-datetime")
def check_in_update_datetime_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    try:
        return update_check_in_datetime(
            booking_id,
            check_in_date=str(payload["check_in_date"]) if payload.get("check_in_date") else None,
            check_in_time=str(payload["check_in_time"]) if payload.get("check_in_time") else None,
            changed_by=current_user.get("username", "web"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@management_api_router.get("/check-ins/{booking_id}/detail")
def check_in_detail_api(
    booking_id: str,
    current_user: dict = Depends(require_login),
):
    """Return all check-in detail data for the booking page."""
    try:
        return get_check_in_detail(booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@management_api_router.patch("/check-ins/{booking_id}/detail")
def check_in_save_detail_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Save check-in detail fields incrementally (draft)."""
    try:
        return save_check_in_detail(
            booking_id,
            check_in_arrival_time=payload.get("check_in_arrival_time"),
            check_in_has_companions=payload.get("check_in_has_companions"),
            check_in_companions_count=payload.get("check_in_companions_count"),
            check_in_document_verified=payload.get("check_in_document_verified"),
            check_in_keys_delivered=payload.get("check_in_keys_delivered"),
            check_in_payment_pending=payload.get("check_in_payment_pending"),
            check_in_deposit_received=payload.get("check_in_deposit_received"),
            check_in_privacy_signed=payload.get("check_in_privacy_signed"),
            check_in_observations=payload.get("check_in_observations"),
            changed_by=current_user.get("username", "web"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@management_api_router.post("/check-ins/{booking_id}/complete")
def check_in_complete_api(
    booking_id: str,
    payload: dict = Body(default={}),
    request: Request = None,
    current_user: dict = Depends(require_login),
):
    try:
        # Save all check-in fields first, then complete
        observations = str(payload.get("check_in_observations") or "")
        save_check_in_detail(
            booking_id,
            check_in_arrival_time=payload.get("check_in_arrival_time"),
            check_in_has_companions=payload.get("check_in_has_companions"),
            check_in_companions_count=payload.get("check_in_companions_count"),
            check_in_document_verified=payload.get("check_in_document_verified"),
            check_in_keys_delivered=payload.get("check_in_keys_delivered"),
            check_in_payment_pending=payload.get("check_in_payment_pending"),
            check_in_deposit_received=payload.get("check_in_deposit_received"),
            check_in_privacy_signed=payload.get("check_in_privacy_signed"),
            check_in_observations=observations,
            changed_by=current_user.get("username", "web"),
        )

        ip_address = ""
        if request:
            forwarded = request.headers.get("x-forwarded-for", "")
            ip_address = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else ""

        return complete_check_in(
            booking_id,
            changed_by=str(payload.get("changed_by") or current_user.get("username", "web")),
            payment_method=str(payload.get("payment_method", "")),
            ip_address=ip_address,
            observations=observations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@management_api_router.get("/check-outs/dates")
def check_out_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_check_out_dates(prop_id=prop_id)


@management_api_router.get("/check-outs")
def check_outs_api(
    operation_date: str = Query(..., alias="date"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_check_outs(operation_date=operation_date, prop_id=prop_id, user=current_user)


@management_api_router.get("/check-outs/{booking_id}/detail")
def check_out_detail_api(
    booking_id: str,
    current_user: dict = Depends(require_login),
):
    """Return all check-out detail data for the liquidation page."""
    try:
        return get_check_out_detail(booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@management_api_router.patch("/check-outs/{booking_id}/detail")
def check_out_save_detail_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Save check-out detail fields incrementally (draft)."""
    try:
        return save_check_out_detail(
            booking_id,
            check_out_room_inspected=payload.get("check_out_room_inspected"),
            check_out_keys_returned=payload.get("check_out_keys_returned"),
            check_out_damages_found=payload.get("check_out_damages_found"),
            check_out_late_checkout_fee=payload.get("check_out_late_checkout_fee"),
            check_out_discount=payload.get("check_out_discount"),
            check_out_discount_reason=payload.get("check_out_discount_reason"),
            check_out_payment_method=payload.get("check_out_payment_method"),
            check_out_payment_ref=payload.get("check_out_payment_ref"),
            check_out_observations=payload.get("check_out_observations"),
            changed_by=current_user.get("username", "web"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@management_api_router.post("/check-outs/{booking_id}/complete")
def check_out_complete_api(
    booking_id: str,
    payload: dict = Body(default={}),
    request: Request = None,
    current_user: dict = Depends(require_login),
):
    try:
        # Save checkout fields first, then complete
        observations = str(payload.get("check_out_observations") or "")
        save_check_out_detail(
            booking_id,
            check_out_room_inspected=payload.get("check_out_room_inspected"),
            check_out_keys_returned=payload.get("check_out_keys_returned"),
            check_out_damages_found=payload.get("check_out_damages_found"),
            check_out_late_checkout_fee=payload.get("check_out_late_checkout_fee"),
            check_out_discount=payload.get("check_out_discount"),
            check_out_discount_reason=payload.get("check_out_discount_reason"),
            check_out_payment_method=payload.get("check_out_payment_method"),
            check_out_payment_ref=payload.get("check_out_payment_ref"),
            check_out_observations=observations,
            changed_by=current_user.get("username", "web"),
        )

        ip_address = ""
        if request:
            forwarded = request.headers.get("x-forwarded-for", "")
            ip_address = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else ""

        return complete_check_out(
            booking_id,
            changed_by=str(payload.get("changed_by") or current_user.get("username", "web")),
            split_invoice=bool(payload.get("split_invoice", False)),
            ip_address=ip_address,
            observations=observations,
            payment_method=str(payload.get("check_out_payment_method", "")),
            payment_ref=str(payload.get("check_out_payment_ref", "")),
            late_checkout_fee=float(payload.get("check_out_late_checkout_fee", 0) or 0),
            discount=float(payload.get("check_out_discount", 0) or 0),
            discount_reason=str(payload.get("check_out_discount_reason", "") or ""),
            damages_found=bool(payload.get("check_out_damages_found", False)),
            keys_returned=bool(payload.get("check_out_keys_returned", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ──────────────────────────────────────────────────────────────────────────────
# POS — Add charges during active stay
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.post("/bookings/{booking_id}/pos-charge", status_code=201)
def booking_pos_charge_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """POS: add a charge to an actively checked-in booking during the stay.

    Validates that the booking is currently checked in before posting the charge.
    The charge is auto-posted to the guest's folio.

    Payload:
    {
      "concept": "Minibar",
      "amount": 15.00,
      "quantity": 1,
      "category": "minibar",  // optional, auto-inferred
      "note": "Coca-Cola, agua, cerveza"
    }
    """
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "stay_status": 1, "prop_id": 1, "guest_name": 1, "status": 1},
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if booking.get("stay_status") != "checked_in":
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden agregar cargos POS a una reserva en estado '{booking.get('stay_status', 'desconocido')}'. "
                   f"Solo reservas con check-in activo (estancia en curso) pueden recibir cargos."
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


# ──────────────────────────────────────────────────────────────────────────────
# User search — find registered users for fast guest data prefill
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.get("/users/search")
def user_search_api(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_login),
):
    """Search registered users by name or email for quick guest data prefill."""
    db = get_database()
    regex = {"$regex": re.escape(q), "$options": "i"}
    users = list(
        db.users.find(
            {"$or": [{"display_name": regex}, {"email": regex}]},
            {"_id": 0, "display_name": 1, "email": 1, "phone": 1, "cedula": 1},
        )
        .sort([("display_name", ASCENDING)])
        .limit(limit)
    )
    return {
        "items": [
            {
                "name": u.get("display_name", ""),
                "email": u.get("email", ""),
                "phone": u.get("phone", ""),
                "cedula": u.get("cedula", ""),
            }
            for u in users
        ]
    }


# ──────────────────────────────────────────────────────────────────────────────
# Room assignment — list available rooms and assign to booking
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.get("/bookings/{booking_id}/available-rooms")
def booking_available_rooms_api(
    booking_id: str,
    current_user: dict = Depends(require_login),
):
    """List available physical rooms for a booking based on its room type and prop."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "prop_id": 1, "room_type_id": 1, "check_in_date": 1, "check_out_date": 1, "rooms": 1},
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    prop_id = int(booking.get("prop_id", 0))
    room_type_id = booking.get("room_type_id", "")
    required = int(booking.get("rooms", 1))

    # Room type info
    room_type = None
    if room_type_id:
        rt = db.room_types.find_one(
            {"room_type_id": room_type_id, "prop_id": prop_id},
            {"_id": 0, "name": 1, "base_capacity": 1, "max_adults": 1},
        )
        if rt:
            room_type = rt

    # Available physical rooms — filter by room_type if present, else return all rooms for the hotel
    room_filter: dict[str, Any] = {"prop_id": prop_id, "is_active": True}
    if room_type_id:
        room_filter["room_type_id"] = room_type_id
    available_rooms = list(
        db.hotel_rooms.find(
            room_filter,
            {"_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1, "floor": 1},
        )
        .sort([("room_number", ASCENDING)])
    )

    # Enrich available rooms with current status from room_status_log
    room_labels = [r.get("room_label", "") or r.get("room_number", "") for r in available_rooms if r.get("room_label") or r.get("room_number")]
    status_map: dict[str, str] = {}
    if room_labels:
        for doc in db.room_status_log.find(
            {"prop_id": prop_id, "room_label": {"$in": room_labels}},
            {"_id": 0, "room_label": 1, "status": 1},
        ):
            status_map[doc["room_label"]] = doc["status"]

    for room in available_rooms:
        label = room.get("room_label", "") or room.get("room_number", "")
        room["room_status"] = status_map.get(label, "unknown")

    # Any already assigned rooms for this booking
    assigned = list(
        db.booking_orders.find(
            {"booking_id": booking_id},
            {"_id": 0, "assigned_rooms": 1},
        )
    )
    assigned_rooms = []
    if assigned and assigned[0].get("assigned_rooms"):
        assigned_rooms = assigned[0]["assigned_rooms"]

    return {
        "prop_id": prop_id,
        "room_type": room_type,
        "rooms_required": required,
        "rooms_available": len(available_rooms),
        "available_rooms": available_rooms,
        "assigned_rooms": assigned_rooms,
    }


@management_api_router.post("/bookings/{booking_id}/assign-rooms")
def booking_assign_rooms_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Assign specific physical rooms to a booking."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "status": 1, "is_test": 1},
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    room_ids = payload.get("room_ids", [])
    if not isinstance(room_ids, list):
        raise HTTPException(status_code=400, detail="room_ids must be a list")

    now = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"assigned_rooms": room_ids, "updated_at": now}},
    )

    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "confirmed"),
        "changed_at": now,
        "reason": f"rooms_assigned: {', '.join(room_ids)}",
        "changed_by": current_user.get("username", "web"),
        "is_test": bool(booking.get("is_test")),
    })

    return {"booking_id": booking_id, "assigned_rooms": room_ids, "assigned_count": len(room_ids)}
