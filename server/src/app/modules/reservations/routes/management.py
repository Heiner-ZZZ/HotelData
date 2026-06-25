"""Management operations routes — check-in and check-out endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from src.app.modules.reservations.service import (
    list_check_ins, list_check_outs, list_check_in_dates,
    list_check_out_dates, complete_check_in, complete_check_out,
)
from src.app.security.dependencies import require_login

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


@management_api_router.post("/check-ins/{booking_id}/complete")
def check_in_complete_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    try:
        return complete_check_in(booking_id, changed_by=str(payload.get("changed_by") or "angular_api"))
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
def check_out_complete_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    try:
        return complete_check_out(booking_id, changed_by=str(payload.get("changed_by") or "angular_api"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
