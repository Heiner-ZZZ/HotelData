"""Reservations CRUD, search and report routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.app.modules.reservations.schemas import (
    BookingListResponse,
    BookingResponse,
    ModuleStatus,
)
from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    create_booking,
    get_booking_detail,
    get_check_in_status,
    get_room_guests,
    list_reservation_dates,
    modify_booking,
    reservation_hotel_options,
    save_room_guests,
    confirm_booking,
    reject_booking,
    get_reservation_stats,
)
from src.app.modules.reservations.service.lifecycle.create import validate_coupon_code
from src.app.modules.reservations.routes.reservations_impl import (
    check_hotel_availability,
    list_rate_plans_with_rates,
    validate_rate_plan_eligibility,
    export_reservations_csv,
    preview_reservation,
)
from src.app.security.dependencies import require_permission
from src.app.security.role_helpers import get_role_name

from src.database.connection import get_database

_router_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modules/reservations", tags=["modules-reservations"])
api_router = APIRouter(prefix="/api/reservations", tags=["reservations-api"])


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return ModuleStatus(
        module="reservations", status="partial",
        description="Solicitudes de reserva con disponibilidad, precio, teléfono huésped, historial de estados, check-in/out manual sin pagos reales.",
    )


@api_router.get("", response_model=BookingListResponse)
def reservations_list_api(
    page: int = Query(default=1, ge=1),
    created_date: str | None = Query(default=None, alias="date"),
    status: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    guest_name: str | None = Query(default=None),
    folio: str | None = Query(default=None),
    stay_status: str | None = Query(default=None, alias="stay_status"),
    booking_source: str | None = Query(default=None, alias="booking_source"),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    from src.app.modules.reservations.service.queries import list_bookings as _list
    return BookingListResponse.model_validate(_list(page=page, page_size=20, created_date=created_date, status=status, prop_id=prop_id, guest_name=guest_name, folio=folio, stay_status=stay_status, booking_source=booking_source, user=current_user))


@api_router.get("/dates")
def reservation_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    return list_reservation_dates(prop_id=prop_id, user=current_user)


@api_router.get("/options")
def reservations_options_api(current_user: dict = Depends(require_permission("reservations.read"))):
    return {"hotel_options": reservation_hotel_options(user=current_user)}


@api_router.get("/availability-check")
def reservation_availability_check_api(
    prop_id: int = Query(..., ge=1),
    check_in: str = Query(...),
    check_out: str = Query(...),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Check if a hotel has room types and inventory available for a given date range."""
    return check_hotel_availability(prop_id, check_in, check_out)


@api_router.get("/rate-plans")
def available_rate_plans_api(
    prop_id: int = Query(..., ge=1),
    check_in: str = Query(...),
    check_out: str = Query(...),
    room_type_id: str = Query(default=""),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Return available rate plans for a hotel + date range + optional room type."""
    return list_rate_plans_with_rates(prop_id, check_in, check_out, room_type_id)


@api_router.post("/preview")
def reservation_preview_api(payload: dict = Body(...), current_user: dict = Depends(require_permission("reservations.read"))):
    return preview_reservation(payload)


@api_router.post("", status_code=status.HTTP_201_CREATED, response_model=BookingResponse)
def reservations_create_api(payload: dict = Body(...), current_user: dict = Depends(require_permission("reservations.create"))):
    try:
        user_role = get_role_name(current_user)
        elig_error = validate_rate_plan_eligibility(payload, user_role)
        if elig_error:
            raise ValueError(elig_error)
        if not payload.get("created_by"):
            payload["created_by"] = current_user.get("username", "web")
        if not payload.get("user_id"):
            payload["user_id"] = str(current_user.get("_id", ""))
        reservation_input = build_reservation_input(payload, source=get_role_name(current_user))
        if reservation_input.rate_plan_id:
            payload["rate_plan_id"] = reservation_input.rate_plan_id
        return BookingResponse.model_validate(create_booking(reservation_input))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/validate-coupon")
def validate_coupon_api(payload: dict = Body(...), current_user: dict = Depends(require_permission("reservations.read"))):
    coupon_code = payload.get("coupon_code") or payload.get("promo_code")
    prop_id = payload.get("prop_id")
    if not coupon_code:
        raise HTTPException(status_code=400, detail="coupon_code is required")
    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id is required")
    error, discount, _ = validate_coupon_code(coupon_code, int(prop_id))
    return {"valid": error is None, "message": error or "Código válido", "discount_percent": discount or 0}


@api_router.get("/stats")
def reservation_stats_api(current_user: dict = Depends(require_permission("reservations.read"))):
    return get_reservation_stats(user=current_user)


@api_router.get("/export")
def reservation_export_api(
    format: str = Query(default="csv"),
    status_filter: str | None = Query(default=None, alias="status"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    output, raw_date = export_reservations_csv(status_filter=status_filter, prop_id=prop_id)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reservas_{raw_date}.csv"},
    )


@api_router.get("/{booking_id}", response_model=BookingResponse)
def reservation_detail_api(booking_id: str, current_user: dict = Depends(require_permission("reservations.read"))):
    """Booking detail with embedded reservation history (``history: list[BookingHistoryResponse]``).

    The history is surfaced by ``get_booking_detail``
    (queries.py:401) and validated under the BookingResponse's nested
    ``BookingHistoryResponse`` items.
    """
    detail = get_booking_detail(booking_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingResponse.model_validate(detail)


@api_router.get("/{booking_id}/cancel-preview")
def reservation_cancel_preview_api(booking_id: str, current_user: dict = Depends(require_permission("reservations.read"))):
    """Preview cancellation penalty without actually cancelling."""
    from src.app.core.timezone import local_today
    from src.app.modules.reservations.service.cleanup import _calculate_cancellation_penalty

    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending bookings can be previewed for cancellation")
    today_str = local_today()
    if today_str >= (booking.get("check_in_date") or ""):
        raise HTTPException(status_code=400, detail="No se puede cancelar una reserva cuya fecha de entrada ya ha comenzado o pasado.")

    penalty = _calculate_cancellation_penalty(
        prop_id=int(booking.get("prop_id", 0)),
        check_in_date=booking.get("check_in_date", ""),
        total_price=booking.get("total_price"),
        total_nights=int(booking.get("total_nights", 0)),
        room_type_id=booking.get("room_type_id", ""),
    )

    total_price = booking.get("total_price") or 0
    total_nights = int(booking.get("total_nights") or 0)
    one_night_price = round(float(total_price) / max(total_nights, 1), 2)

    return {
        "booking_id": booking_id,
        "guest_name": booking.get("guest_name", ""),
        "check_in_date": booking.get("check_in_date", ""),
        "total_price": booking.get("total_price"),
        "currency": booking.get("currency", "USD"),
        "total_nights": total_nights,
        "one_night_price": one_night_price,
        "free_cancellation": penalty["free_cancellation"],
        "penalty_percent": penalty["penalty_percent"],
        "penalty_amount": penalty["penalty_amount"],
        "hours_until_checkin": penalty["hours_until_checkin"],
        "cancellation_hours": penalty["cancellation_hours"],
    }


@api_router.post("/{booking_id}/cancel")
def reservation_cancel_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_permission("reservations.delete"))):
    try:
        return cancel_booking(booking_id, reason=str(payload.get("reason") or "cancelled_by_user"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "web")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/confirm")
def reservation_confirm_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_permission("reservations.update"))):
    role = get_role_name(current_user)
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede confirmar reservas.")
    try:
        return confirm_booking(booking_id, reason=str(payload.get("reason") or "confirmed_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/reject")
def reservation_reject_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_permission("reservations.update"))):
    role = get_role_name(current_user)
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede rechazar reservas.")
    try:
        return reject_booking(booking_id, reason=str(payload.get("reason") or "rejected_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.patch("/{booking_id}", response_model=BookingResponse)
def reservation_modify_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_permission("reservations.update"))):
    try:
        return BookingResponse.model_validate(modify_booking(booking_id,
            check_in_date=str(payload["check_in_date"]) if payload.get("check_in_date") else None,
            check_in_time=str(payload["check_in_time"]) if payload.get("check_in_time") else None,
            check_out_date=str(payload["check_out_date"]) if payload.get("check_out_date") else None,
            room_type_id=str(payload["room_type_id"]) if payload.get("room_type_id") else None,
            rooms=int(payload["rooms"]) if payload.get("rooms") is not None else None,
            comment=str(payload["comment"]) if payload.get("comment") is not None else None,
            changed_by=current_user.get("username", "web"),
            selected_amenities=payload.get("selected_amenities")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/room-guests")
def room_guests_get_api(booking_id: str, current_user: dict = Depends(require_permission("reservations.read"))):
    return get_room_guests(booking_id)


@api_router.put("/{booking_id}/room-guests")
def room_guests_put_api(booking_id: str, payload: dict = Body(...), current_user: dict = Depends(require_permission("reservations.update"))):
    try:
        return save_room_guests(booking_id, payload.get("room_guests", []))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/check-in-status")
def check_in_status_api(booking_id: str, current_user: dict = Depends(require_permission("reservations.read"))):
    return get_check_in_status(booking_id)
