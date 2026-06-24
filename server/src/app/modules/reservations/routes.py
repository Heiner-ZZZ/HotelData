from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.app.modules.reservations.schemas import ModuleStatus
from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    complete_check_in,
    complete_check_out,
    create_booking,
    get_booking_detail,
    get_check_in_status,
    get_room_guests,
    hotel_booking_context,
    list_bookings,
    list_check_ins,
    list_check_in_dates,
    list_check_outs,
    list_check_out_dates,
    list_reservation_dates,
    module_status,
    modify_booking,
    reservation_hotel_options,
    save_room_guests,
    validate_reservation_input,
    confirm_booking,
    reject_booking,
    get_reservation_stats,
)
from src.app.modules.reservations.service.lifecycle import _check_availability, _calculate_total_price, validate_coupon_code
from src.app.security.dependencies import require_login
from src.database.connection import get_database


router = APIRouter(prefix="/modules/reservations", tags=["modules-reservations"])
api_router = APIRouter(prefix="/api/reservations", tags=["reservations-api"])
management_api_router = APIRouter(prefix="/api/management", tags=["management-operations-api"])


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return module_status()


@api_router.get("")
def reservations_list_api(
    page: int = Query(default=1, ge=1),
    created_date: str | None = Query(default=None, alias="date"),
    status: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    guest_name: str | None = Query(default=None),
    current_user: dict = Depends(require_login),
):
    return list_bookings(
        page=page,
        page_size=20,
        created_date=created_date,
        status=status,
        prop_id=prop_id,
        guest_name=guest_name,
        user=current_user,
    )



@api_router.get("/dates")
def reservation_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_reservation_dates(prop_id=prop_id, user=current_user)


@api_router.get("/options")
def reservations_options_api(current_user: dict = Depends(require_login)):
    return {"hotel_options": reservation_hotel_options(user=current_user)}


@api_router.post("/preview")
def reservation_preview_api(payload: dict = Body(...), current_user: dict = Depends(require_login)):
    try:
        reservation_input = build_reservation_input(payload, source="angular_api")
        errors = validate_reservation_input(reservation_input)
        if errors:
            raise ValueError("; ".join(errors))

        avail_error = _check_availability(
            reservation_input.prop_id,
            reservation_input.check_in_date,
            reservation_input.check_out_date,
            reservation_input.rooms,
            reservation_input.room_type_id,
        )
        total_price, currency, total_nights = _calculate_total_price(
            reservation_input.prop_id,
            reservation_input.room_type_id,
            reservation_input.check_in_date,
            reservation_input.check_out_date,
            reservation_input.rooms,
        )
        return {
            "available": avail_error is None,
            "availability_message": avail_error,
            "total_price": total_price,
            "currency": currency,
            "total_nights": total_nights,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("", status_code=status.HTTP_201_CREATED)
def reservations_create_api(payload: dict = Body(...), current_user: dict = Depends(require_login)):
    try:
        reservation_input = build_reservation_input(payload, source="angular_api")
        return create_booking(reservation_input)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/validate-coupon")
def validate_coupon_api(payload: dict = Body(...), current_user: dict = Depends(require_login)):
    coupon_code = payload.get("coupon_code") or payload.get("promo_code")
    prop_id = payload.get("prop_id")
    if not coupon_code:
        raise HTTPException(status_code=400, detail="coupon_code is required")
    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id is required")
    
    error, discount = validate_coupon_code(coupon_code, int(prop_id))
    if error:
        return {"valid": False, "message": error, "discount_percent": 0}
    return {"valid": True, "message": "Código válido", "discount_percent": discount}

# ── Static routes (must be before /{booking_id}) ──


@api_router.get("/stats")
def reservation_stats_api(current_user: dict = Depends(require_login)):
    return get_reservation_stats(user=current_user)


@api_router.get("/export")
def reservation_export_api(
    format: str = Query(default="csv"),
    status_filter: str | None = Query(default=None, alias="status"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    if format != "csv":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato no soportado. Usa 'csv'.")

    db = get_database()
    filters: dict[str, Any] = {}
    if status_filter:
        filters["status"] = status_filter
    if prop_id:
        filters["prop_id"] = prop_id

    bookings = list(
        db.booking_orders.find(filters, {"_id": 0}).sort([("created_at", -1)])
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Booking ID", "Prop ID", "Status", "Guest Name", "Guest Email", "Guest Phone",
        "Check-in", "Check-out", "Adults", "Children", "Rooms",
        "Total Price", "Currency", "Total Nights",
        "Booking Source", "Created At", "Comment",
    ])
    for b in bookings:
        writer.writerow([
            b.get("booking_id", ""),
            b.get("prop_id", ""),
            b.get("status", ""),
            b.get("guest_name", ""),
            b.get("guest_email", ""),
            b.get("guest_phone", ""),
            b.get("check_in_date", ""),
            b.get("check_out_date", ""),
            b.get("adults", ""),
            b.get("children", ""),
            b.get("rooms", ""),
            b.get("total_price", "") if b.get("total_price") is not None else "",
            b.get("currency", ""),
            b.get("total_nights", ""),
            b.get("booking_source", ""),
            b.get("created_at", ""),
            b.get("comment", ""),
        ])

    output.seek(0)
    # created_at is a datetime object in MongoDB — convert to string before slicing
    raw_date = str(bookings[0].get("created_at", "export")) if bookings else "export"
    date_str = raw_date[:10]
    filename = f"reservas_{date_str}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@api_router.get("/{booking_id}")
def reservation_detail_api(booking_id: str, current_user: dict = Depends(require_login)):
    detail = get_booking_detail(booking_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return detail


@api_router.post("/{booking_id}/cancel")
def reservation_cancel_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    try:
        return cancel_booking(
            booking_id,
            reason=str(payload.get("reason") or "cancelled_by_user"),
            changed_by=str(payload.get("changed_by") or "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ── Confirm / Reject ──


@api_router.post("/{booking_id}/confirm")
def reservation_confirm_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    role = current_user.get("primary_role", "")
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede confirmar reservas.")
    try:
        return confirm_booking(
            booking_id,
            reason=str(payload.get("reason") or "confirmed_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/reject")
def reservation_reject_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    role = current_user.get("primary_role", "")
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede rechazar reservas.")
    try:
        return reject_booking(
            booking_id,
            reason=str(payload.get("reason") or "rejected_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ── Booking Modification ──


@api_router.patch("/{booking_id}")
def reservation_modify_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Modify a booking's dates, room type, room count, or comment."""
    try:
        return modify_booking(
            booking_id,
            check_in_date=str(payload["check_in_date"]) if payload.get("check_in_date") else None,
            check_out_date=str(payload["check_out_date"]) if payload.get("check_out_date") else None,
            room_type_id=str(payload["room_type_id"]) if payload.get("room_type_id") else None,
            rooms=int(payload["rooms"]) if payload.get("rooms") is not None else None,
            comment=str(payload["comment"]) if payload.get("comment") is not None else None,
            changed_by=current_user.get("username", "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ── Room Guests (per-room passenger manifest) ──


@api_router.get("/{booking_id}/room-guests")
def room_guests_get_api(booking_id: str, current_user: dict = Depends(require_login)):
    return get_room_guests(booking_id)


@api_router.put("/{booking_id}/room-guests")
def room_guests_put_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Save per-room guest data for a booking.
    Body: {room_guests: [{room_index, guests: [{guest_name, guest_email, ...}]}]}
    """
    try:
        return save_room_guests(booking_id, payload.get("room_guests", []))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/check-in-status")
def check_in_status_api(booking_id: str, current_user: dict = Depends(require_login)):
    """Get check-in readiness status (per-room guest data completeness)."""
    return get_check_in_status(booking_id)


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


@management_api_router.post("/check-ins/{booking_id}/complete")
def check_in_complete_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    try:
        return complete_check_in(
            booking_id,
            changed_by=str(payload.get("changed_by") or "angular_api"),
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


@management_api_router.post("/check-outs/{booking_id}/complete")
def check_out_complete_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    try:
        return complete_check_out(
            booking_id,
            changed_by=str(payload.get("changed_by") or "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
