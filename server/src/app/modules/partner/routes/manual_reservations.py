from __future__ import annotations

from fastapi import Body, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from src.app.modules.partner.routes import api_router, web_router
from src.app.modules.reservations.service.lifecycle import create_booking
from src.app.modules.reservations.service.queries import list_bookings
from src.app.modules.reservations.service.validation import build_reservation_input


@web_router.get("/manual-reservations")
def manual_reservations_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    prop_id: int | None = Query(default=None, ge=1),
):
    results = list_bookings(
        page=page,
        page_size=20,
        status=status_filter,
        prop_id=prop_id,
    )
    return results


@web_router.get("/manual-reservations/new")
def manual_reservation_new_form(request: Request):
    return {"hotel_options": [], "room_type_options": []}


@web_router.post("/manual-reservations/new")
def manual_reservation_create(
    request: Request,
    prop_id: int = Body(...),
    room_type_id: str = Body(...),
    guest_name: str = Body(...),
    guest_email: str = Body(...),
    guest_phone: str = Body(default=""),
    check_in_date: str = Body(...),
    check_out_date: str = Body(...),
    adults: int = Body(default=1),
    children: int = Body(default=0),
    rooms: int = Body(default=1),
    comment: str = Body(default=""),
):
    payload = build_reservation_input(
        {
            "prop_id": prop_id,
            "room_type_id": room_type_id,
            "guest_name": guest_name,
            "guest_email": guest_email,
            "guest_phone": guest_phone,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "children": children,
            "rooms": rooms,
            "comment": comment,
            "source": "partner_manual",
            "created_by": "partner_manual",
        },
        source="partner_manual",
    )
    try:
        result = create_booking(payload, manual_reservation=True)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=status.HTTP_400_BAD_REQUEST)
    return JSONResponse({"ok": True, "booking_id": result.get("booking_id")}, status_code=status.HTTP_201_CREATED)


@api_router.post("/manual-reservations", status_code=status.HTTP_201_CREATED)
def manual_reservation_create_api(payload: dict = Body(...)):
    try:
        reservation_input = build_reservation_input(payload, source="partner_api")
        return create_booking(reservation_input, manual_reservation=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
