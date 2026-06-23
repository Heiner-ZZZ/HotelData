from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from src.app.modules.reservations.schemas import ModuleStatus
from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    complete_check_in,
    complete_check_out,
    create_booking,
    get_booking_detail,
    hotel_booking_context,
    list_bookings,
    list_check_ins,
    list_check_in_dates,
    list_check_outs,
    list_check_out_dates,
    list_reservation_dates,
    module_status,
    reservation_hotel_options,
)
from src.app.security.dependencies import require_login


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
    current_user: dict = Depends(require_login),
):
    return list_bookings(page=page, page_size=20, created_date=created_date, user=current_user)


@api_router.get("/dates")
def reservation_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_reservation_dates(prop_id=prop_id, user=current_user)


@api_router.get("/options")
def reservations_options_api(current_user: dict = Depends(require_login)):
    return {"hotel_options": reservation_hotel_options(user=current_user)}


@api_router.post("", status_code=status.HTTP_201_CREATED)
def reservations_create_api(payload: dict = Body(...)):
    try:
        reservation_input = build_reservation_input(payload, source="angular_api")
        return create_booking(reservation_input)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}")
def reservation_detail_api(booking_id: str):
    detail = get_booking_detail(booking_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return detail


@api_router.post("/{booking_id}/cancel")
def reservation_cancel_api(booking_id: str, payload: dict = Body(default={})):
    try:
        return cancel_booking(
            booking_id,
            reason=str(payload.get("reason") or "cancelled_by_user"),
            changed_by=str(payload.get("changed_by") or "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@management_api_router.get("/check-ins/dates")
def check_in_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
):
    return list_check_in_dates(prop_id=prop_id)


@management_api_router.get("/check-ins")
def check_ins_api(
    operation_date: str = Query(..., alias="date"),
    prop_id: int | None = Query(default=None, ge=1),
):
    return list_check_ins(operation_date=operation_date, prop_id=prop_id)


@management_api_router.post("/check-ins/{booking_id}/complete")
def check_in_complete_api(booking_id: str, payload: dict = Body(default={})):
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
):
    return list_check_out_dates(prop_id=prop_id)


@management_api_router.get("/check-outs")
def check_outs_api(
    operation_date: str = Query(..., alias="date"),
    prop_id: int | None = Query(default=None, ge=1),
):
    return list_check_outs(operation_date=operation_date, prop_id=prop_id)


@management_api_router.post("/check-outs/{booking_id}/complete")
def check_out_complete_api(booking_id: str, payload: dict = Body(default={})):
    try:
        return complete_check_out(
            booking_id,
            changed_by=str(payload.get("changed_by") or "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
