from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Body, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.app.modules.reservations.schemas import ModuleStatus
from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    create_booking,
    get_booking_detail,
    hotel_booking_context,
    list_bookings,
    module_status,
    reservation_hotel_options,
)


router = APIRouter(prefix="/modules/reservations", tags=["modules-reservations"])
web_router = APIRouter(tags=["reservations"])
api_router = APIRouter(prefix="/api/reservations", tags=["reservations-api"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return module_status()


def _page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    return f"{request.url.path}?{urlencode(params)}"


@web_router.get("/reservations")
def reservations_list(request: Request, page: int = Query(default=1, ge=1)):
    results = list_bookings(page=page, page_size=20)
    return templates.TemplateResponse(
        request,
        "reservations/list.html",
        {
            "results": results,
            "prev_url": _page_url(request, results["page"] - 1) if results["has_prev"] else None,
            "next_url": _page_url(request, results["page"] + 1) if results["has_next"] else None,
        },
    )


@web_router.get("/reservations/new")
def reservation_new_form(request: Request, prop_id: int | None = None, error: str = ""):
    hotel = hotel_booking_context(prop_id) if prop_id else None
    return templates.TemplateResponse(
        request,
        "reservations/new.html",
        {
            "error": error,
            "hotel": hotel,
            "hotel_options": reservation_hotel_options(),
            "form_values": {
                "prop_id": prop_id or "",
                "guest_name": "",
                "guest_email": "",
                "check_in_date": "",
                "check_out_date": "",
                "adults": 2,
                "children": 0,
                "rooms": 1,
                "comment": "",
            },
        },
    )


@web_router.post("/reservations/new")
def reservation_new_submit(
    request: Request,
    prop_id: int = Form(...),
    guest_name: str = Form(...),
    guest_email: str = Form(...),
    check_in_date: str = Form(...),
    check_out_date: str = Form(...),
    adults: int = Form(...),
    children: int = Form(...),
    rooms: int = Form(...),
    comment: str = Form(""),
):
    form_data = {
        "prop_id": prop_id,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "comment": comment,
    }
    payload = build_reservation_input(form_data, source="web_request")
    try:
        result = create_booking(payload)
        return RedirectResponse(f"/reservations/{result['booking_id']}", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as exc:
        hotel = hotel_booking_context(prop_id) if prop_id else None
        return templates.TemplateResponse(
            request,
            "reservations/new.html",
            {"error": str(exc), "hotel": hotel, "hotel_options": reservation_hotel_options(), "form_values": form_data},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@web_router.get("/reservations/{booking_id}")
def reservation_detail(request: Request, booking_id: str):
    detail = get_booking_detail(booking_id)
    if detail is None:
        return RedirectResponse("/reservations", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "reservations/detail.html", detail)


@web_router.post("/reservations/{booking_id}/cancel")
def reservation_cancel(booking_id: str):
    try:
        cancel_booking(booking_id, reason="cancelled_by_user", changed_by="web")
    except ValueError:
        pass
    return RedirectResponse(f"/reservations/{booking_id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/partner/manual-reservations/new")
def manual_reservation_form(request: Request, prop_id: int | None = None, error: str = ""):
    hotel = hotel_booking_context(prop_id) if prop_id else None
    return templates.TemplateResponse(
        request,
        "partner/manual_reservation_new.html",
        {
            "error": error,
            "hotel": hotel,
            "hotel_options": reservation_hotel_options(),
            "form_values": {
                "prop_id": prop_id or "",
                "guest_name": "",
                "guest_email": "",
                "check_in_date": "",
                "check_out_date": "",
                "adults": 2,
                "children": 0,
                "rooms": 1,
                "comment": "",
                "created_by": "partner_manual",
            },
        },
    )


@web_router.post("/partner/manual-reservations/new")
def manual_reservation_submit(
    request: Request,
    prop_id: int = Form(...),
    guest_name: str = Form(...),
    guest_email: str = Form(...),
    check_in_date: str = Form(...),
    check_out_date: str = Form(...),
    adults: int = Form(...),
    children: int = Form(...),
    rooms: int = Form(...),
    comment: str = Form(""),
    created_by: str = Form("partner_manual"),
):
    form_data = {
        "prop_id": prop_id,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "comment": comment,
        "created_by": created_by,
    }
    payload = build_reservation_input(form_data, source="partner_manual")
    try:
        result = create_booking(payload, manual_reservation=True)
        return RedirectResponse(f"/reservations/{result['booking_id']}", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as exc:
        hotel = hotel_booking_context(prop_id) if prop_id else None
        return templates.TemplateResponse(
            request,
            "partner/manual_reservation_new.html",
            {"error": str(exc), "hotel": hotel, "hotel_options": reservation_hotel_options(), "form_values": form_data},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@api_router.get("")
def reservations_list_api(page: int = Query(default=1, ge=1)):
    return list_bookings(page=page, page_size=20)


@api_router.get("/options")
def reservations_options_api():
    return {"hotel_options": reservation_hotel_options()}


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
