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
from src.app.modules.reservations.service._checkinout import update_check_in_datetime
from src.app.modules.partner.services.audit import register_action
from src.app.security.dependencies import require_permission
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
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("check-ins.read")),
):
    result = list_check_in_dates(prop_id=prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="check_in",
        entity_id="dates",
        action="read",
        summary="Listado de fechas de check-in",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return result


@management_api_router.get("/check-ins")
def check_ins_api(
    request: Request,
    operation_date: str = Query(..., alias="date"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("check-ins.read")),
):
    result = list_check_ins(operation_date=operation_date, prop_id=prop_id, user=current_user)
    register_action(
        prop_id=prop_id or 0,
        entity_type="check_in",
        entity_id="list",
        action="read",
        summary=f"Listado de check-ins para {operation_date}",
        changed_by=current_user.get("username", "system"),
        metadata={"operation_date": operation_date, "prop_id": prop_id, "url": str(request.url)},
    )
    return result


@management_api_router.patch("/check-ins/{booking_id}/update-datetime")
def check_in_update_datetime_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("check-ins.manage")),
):
    db = get_database()
    before = db.booking_orders.find_one({"booking_id": booking_id}, {"check_in_date": 1, "check_in_time": 1, "prop_id": 1})
    try:
        result = update_check_in_datetime(
            booking_id,
            check_in_date=str(payload["check_in_date"]) if payload.get("check_in_date") else None,
            check_in_time=str(payload["check_in_time"]) if payload.get("check_in_time") else None,
            changed_by=current_user.get("username", "web"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    diff = {}
    if payload.get("check_in_date"):
        diff["check_in_date"] = {"old": before.get("check_in_date") if before else None, "new": payload["check_in_date"]}
    if payload.get("check_in_time"):
        diff["check_in_time"] = {"old": before.get("check_in_time") if before else None, "new": payload["check_in_time"]}
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="check_in",
        entity_id=booking_id,
        action="update",
        summary=f"Actualización de fecha/hora de check-in para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return result


@management_api_router.get("/check-ins/{booking_id}/detail")
def check_in_detail_api(
    request: Request,
    booking_id: str,
    current_user: dict = Depends(require_permission("check-ins.read")),
):
    """Return all check-in detail data for the booking page."""
    try:
        result = get_check_in_detail(booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    register_action(
        prop_id=result.get("prop_id", 0),
        entity_type="check_in",
        entity_id=booking_id,
        action="read",
        summary=f"Consulta de detalle de check-in para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return result


@management_api_router.patch("/check-ins/{booking_id}/detail")
def check_in_save_detail_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("check-ins.manage")),
):
    """Save check-in detail fields incrementally (draft)."""
    db = get_database()
    before = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "prop_id": 1,
            "check_in_arrival_time": 1, "check_in_has_companions": 1,
            "check_in_companions_count": 1, "check_in_document_verified": 1,
            "check_in_keys_delivered": 1, "check_in_payment_pending": 1,
            "check_in_deposit_received": 1, "check_in_privacy_signed": 1,
            "check_in_observations": 1,
        },
    )
    try:
        result = save_check_in_detail(
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
    diff = {}
    for key in [
        "check_in_arrival_time", "check_in_has_companions", "check_in_companions_count",
        "check_in_document_verified", "check_in_keys_delivered", "check_in_payment_pending",
        "check_in_deposit_received", "check_in_privacy_signed", "check_in_observations",
    ]:
        if key in payload:
            diff[key] = {"old": before.get(key) if before else None, "new": payload[key]}
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="check_in",
        entity_id=booking_id,
        action="update",
        summary=f"Guardado de detalle de check-in para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return result


@management_api_router.post("/check-ins/{booking_id}/complete")
def check_in_complete_api(
    booking_id: str,
    payload: dict = Body(default={}),
    request: Request = None,
    current_user: dict = Depends(require_permission("check-ins.manage")),
):
    db = get_database()
    before = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"prop_id": 1, "status": 1, "stay_status": 1, "check_in_by": 1},
    )
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

        result = complete_check_in(
            booking_id,
            changed_by=str(payload.get("changed_by") or current_user.get("username", "web")),
            payment_method=str(payload.get("payment_method", "")),
            ip_address=ip_address,
            observations=observations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    diff = {
        "stay_status": {"old": before.get("stay_status") if before else None, "new": "checked_in"},
        "check_in_by": {"old": before.get("check_in_by") if before else None, "new": current_user.get("username", "web")},
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="check_in",
        entity_id=booking_id,
        action="update",
        summary=f"Completado de check-in para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@management_api_router.get("/check-outs/dates")
def check_out_dates_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("check-outs.read")),
):
    result = list_check_out_dates(prop_id=prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="check_out",
        entity_id="dates",
        action="read",
        summary="Listado de fechas de check-out",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return result


@management_api_router.get("/check-outs")
def check_outs_api(
    request: Request,
    operation_date: str = Query(..., alias="date"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("check-outs.read")),
):
    result = list_check_outs(operation_date=operation_date, prop_id=prop_id, user=current_user)
    register_action(
        prop_id=prop_id or 0,
        entity_type="check_out",
        entity_id="list",
        action="read",
        summary=f"Listado de check-outs para {operation_date}",
        changed_by=current_user.get("username", "system"),
        metadata={"operation_date": operation_date, "prop_id": prop_id, "url": str(request.url)},
    )
    return result


@management_api_router.get("/check-outs/{booking_id}/detail")
def check_out_detail_api(
    request: Request,
    booking_id: str,
    current_user: dict = Depends(require_permission("check-outs.read")),
):
    """Return all check-out detail data for the liquidation page."""
    try:
        result = get_check_out_detail(booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    register_action(
        prop_id=result.get("prop_id", 0),
        entity_type="check_out",
        entity_id=booking_id,
        action="read",
        summary=f"Consulta de detalle de check-out para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return result


@management_api_router.patch("/check-outs/{booking_id}/detail")
def check_out_save_detail_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("check-outs.manage")),
):
    """Save check-out detail fields incrementally (draft)."""
    db = get_database()
    before = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "prop_id": 1,
            "check_out_room_inspected": 1, "check_out_keys_returned": 1,
            "check_out_damages_found": 1, "check_out_late_checkout_fee": 1,
            "check_out_discount": 1, "check_out_discount_reason": 1,
            "check_out_payment_method": 1, "check_out_payment_ref": 1,
            "check_out_observations": 1,
        },
    )
    try:
        result = save_check_out_detail(
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
    diff = {}
    for key in [
        "check_out_room_inspected", "check_out_keys_returned", "check_out_damages_found",
        "check_out_late_checkout_fee", "check_out_discount", "check_out_discount_reason",
        "check_out_payment_method", "check_out_payment_ref", "check_out_observations",
    ]:
        if key in payload:
            diff[key] = {"old": before.get(key) if before else None, "new": payload[key]}
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="check_out",
        entity_id=booking_id,
        action="update",
        summary=f"Guardado de detalle de check-out para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return result


@management_api_router.post("/check-outs/{booking_id}/complete")
def check_out_complete_api(
    booking_id: str,
    payload: dict = Body(default={}),
    request: Request = None,
    current_user: dict = Depends(require_permission("check-outs.manage")),
):
    db = get_database()
    before = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"prop_id": 1, "status": 1, "stay_status": 1, "check_out_by": 1},
    )
    # Check-out is a terminal transition. A stale tab, double click, or retry
    # after a successful request must be safe and must not repeat side effects
    # such as inventory restoration, housekeeping tasks, or audit entries.
    if before and before.get("stay_status") == "checked_out":
        return {"booking_id": booking_id, "stay_status": "checked_out"}

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

        result = complete_check_out(
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
    diff = {
        "stay_status": {"old": before.get("stay_status") if before else None, "new": "checked_out"},
        "check_out_by": {"old": before.get("check_out_by") if before else None, "new": current_user.get("username", "web")},
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="check_out",
        entity_id=booking_id,
        action="update",
        summary=f"Completado de check-out para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# POS — Add charges during active stay
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.post("/bookings/{booking_id}/pos-charge", status_code=201)
def booking_pos_charge_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("charges.manage")),
):
    """POS: add a charge to an actively checked-in booking during the stay."""
    db = get_database()
    before = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1, "total_charges": 1})
    result = apply_pos_charge(booking_id, payload, current_user, db)
    after = db.booking_orders.find_one({"booking_id": booking_id}, {"total_charges": 1})
    diff = {
        "total_charges": {
            "old": before.get("total_charges") if before else None,
            "new": after.get("total_charges") if after else None,
        },
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="booking_pos_charge",
        entity_id=booking_id,
        action="create",
        summary=f"Cargo POS a reserva {booking_id}: {payload.get('concept', '')} — ${payload.get('amount', 0)}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# User search — find registered users for fast guest data prefill
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.get("/users/search")
def user_search_api(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_permission("users.read")),
):
    """Search registered users by name or email for quick guest data prefill."""
    db = get_database()
    result = search_users(q, limit, db)
    register_action(
        prop_id=0,
        entity_type="user_search",
        entity_id="search",
        action="read",
        summary=f"Búsqueda de usuarios: '{q}'",
        changed_by=current_user.get("username", "system"),
        metadata={"q": q, "limit": limit, "url": str(request.url)},
    )
    return {"items": result}


# ──────────────────────────────────────────────────────────────────────────────
# No-show — mark booking as no-show when guest never arrived
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.post("/bookings/{booking_id}/no-show")
def booking_no_show_api(
    booking_id: str,
    current_user: dict = Depends(require_permission("reservations.update")),
):
    """Mark a confirmed booking as no-show with first-night penalty."""
    from src.app.modules.reservations.service.no_show import process_no_show

    db = get_database()
    before = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"prop_id": 1, "status": 1, "stay_status": 1, "guest_name": 1},
    )
    try:
        result = process_no_show(
            booking_id,
            changed_by=current_user.get("username", "web"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    diff = {
        "stay_status": {"old": before.get("stay_status") if before else None, "new": "no_show"},
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="reservation",
        entity_id=booking_id,
        action="no_show",
        summary=f"No-show manual — {before.get('guest_name', booking_id) if before else booking_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Room assignment — list available rooms and assign to booking
# ──────────────────────────────────────────────────────────────────────────────


@management_api_router.get("/bookings/{booking_id}/available-rooms")
def booking_available_rooms_api(
    request: Request,
    booking_id: str,
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """List available physical rooms for a booking based on its room type and prop."""
    db = get_database()
    result = get_available_rooms(booking_id, db)
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1})
    register_action(
        prop_id=(booking.get("prop_id") or 0) if booking else 0,
        entity_type="booking_room_assignment",
        entity_id=booking_id,
        action="read",
        summary=f"Consulta de habitaciones disponibles para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return result


@management_api_router.post("/bookings/{booking_id}/assign-rooms")
def booking_assign_rooms_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("reservations.update")),
):
    """Assign specific physical rooms to a booking."""
    db = get_database()
    before = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1, "assigned_rooms": 1})
    room_ids = payload.get("room_ids", [])
    result = assign_rooms_to_booking(booking_id, room_ids, current_user, db)
    diff = {
        "assigned_rooms": {
            "old": before.get("assigned_rooms") if before else None,
            "new": room_ids,
        },
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="booking_room_assignment",
        entity_id=booking_id,
        action="update",
        summary=f"Asignación de habitaciones a reserva {booking_id}: {', '.join(room_ids) if room_ids else 'ninguna'}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result
