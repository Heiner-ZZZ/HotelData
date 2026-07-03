"""Management operations routes — check-in and check-out endpoints."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from src.app.modules.reservations.service import (
    list_check_ins, list_check_outs, list_check_in_dates,
    list_check_out_dates, complete_check_in, complete_check_out,
    get_check_in_detail, save_check_in_detail,
    get_check_out_detail, save_check_out_detail,
)
from src.app.modules.reservations.service._helpers import utc_now
from src.app.modules.reservations.service._checkinout import update_check_in_datetime
from src.app.security.dependencies import require_login
from src.database.connection import get_database

from src.app.modules.reservations.routes.management_impl import (
    extract_ip_address,
    extract_checkout_ip_address,
    apply_pos_charge,
    search_users,
    get_available_rooms,
    assign_rooms_to_booking,
)

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

        ip_address = extract_ip_address(request)

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

        ip_address = extract_checkout_ip_address(request)

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
    """POS: add a charge to an actively checked-in booking during the stay."""
    db = get_database()
    return apply_pos_charge(booking_id, payload, current_user, db)


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
    result = search_users(q, limit, db)
    return {"items": result}


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
    return get_available_rooms(booking_id, db)


@management_api_router.post("/bookings/{booking_id}/assign-rooms")
def booking_assign_rooms_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Assign specific physical rooms to a booking."""
    db = get_database()
    room_ids = payload.get("room_ids", [])
    return assign_rooms_to_booking(booking_id, room_ids, current_user, db)
