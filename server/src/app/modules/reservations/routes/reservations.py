"""Reservations CRUD, search and report routes."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.app.modules.reservations.schemas import ModuleStatus
from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    create_booking,
    get_booking_detail,
    get_check_in_status,
    get_room_guests,
    hotel_booking_context,
    list_bookings,
    list_reservation_dates,
    modify_booking,
    reservation_hotel_options,
    save_room_guests,
    validate_reservation_input,
    confirm_booking,
    reject_booking,
    get_reservation_stats,
)
from datetime import datetime, timedelta

from src.app.modules.reservations.service.lifecycle.create import _check_availability, _calculate_total_price, validate_coupon_code
from src.app.security.dependencies import require_login
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


@api_router.get("")
def reservations_list_api(
    page: int = Query(default=1, ge=1),
    created_date: str | None = Query(default=None, alias="date"),
    status: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    guest_name: str | None = Query(default=None),
    current_user: dict = Depends(require_login),
):
    from src.app.modules.reservations.service.queries import list_bookings as _list
    return _list(page=page, page_size=20, created_date=created_date, status=status, prop_id=prop_id, guest_name=guest_name, user=current_user)


@api_router.get("/dates")
def reservation_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    return list_reservation_dates(prop_id=prop_id, user=current_user)


@api_router.get("/options")
def reservations_options_api(current_user: dict = Depends(require_login)):
    return {"hotel_options": reservation_hotel_options(user=current_user)}


@api_router.get("/availability-check")
def reservation_availability_check_api(
    prop_id: int = Query(..., ge=1),
    check_in: str = Query(...),
    check_out: str = Query(...),
    current_user: dict = Depends(require_login),
):
    """Check if a hotel has room types and inventory available for a given date range."""
    db = get_database()

    # 1. Check if the hotel has room types
    room_types_count = db.room_types.count_documents({"prop_id": prop_id})
    has_room_types = room_types_count > 0

    # 2. Check if there's inventory for the date range
    try:
        cin = datetime.strptime(check_in, "%Y-%m-%d")
        cout = datetime.strptime(check_out, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    dates = [(cin + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(max(1, (cout - cin).days))]

    if not has_room_types:
        return {
            "hasInventory": False, "hasRoomTypes": False,
            "totalRooms": 0, "availableRooms": 0,
            "message": "El hotel no tiene tipos de habitación configurados.",
        }

    # Count total inventory rows for this hotel across the date range
    inventory_records = list(
        db.room_inventory_calendar.find(
            {"prop_id": prop_id, "date": {"$in": dates}},
            {"_id": 0, "available_rooms": 1, "total_rooms": 1},
        )
    )

    if not inventory_records:
        return {
            "hasInventory": False, "hasRoomTypes": True,
            "totalRooms": 0, "availableRooms": 0,
            "message": "No hay datos de inventario para las fechas seleccionadas.",
        }

    total_rooms = max(r.get("total_rooms", 0) or 0 for r in inventory_records)
    min_available = min(r.get("available_rooms", 0) or 0 for r in inventory_records)
    has_inventory = min_available > 0

    return {
        "hasInventory": has_inventory,
        "hasRoomTypes": True,
        "totalRooms": total_rooms,
        "availableRooms": min_available,
        "message": f"{min_available} habitación(es) disponible(s) en las fechas seleccionadas." if has_inventory
                   else "Sin disponibilidad en las fechas seleccionadas.",
    }


@api_router.post("/preview")
def reservation_preview_api(payload: dict = Body(...), current_user: dict = Depends(require_login)):
    try:
        reservation_input = build_reservation_input(payload, source="angular_api")
        errors = validate_reservation_input(reservation_input)
        if errors:
            raise ValueError("; ".join(errors))
        avail_error = _check_availability(
            reservation_input.prop_id, reservation_input.check_in_date,
            reservation_input.check_out_date, reservation_input.rooms, reservation_input.room_type_id,
        )
        total_price, currency, total_nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
            reservation_input.prop_id, reservation_input.room_type_id,
            reservation_input.check_in_date, reservation_input.check_out_date, reservation_input.rooms,
            adults=reservation_input.adults, children=reservation_input.children,
        )
        return {
            "available": avail_error is None, "availability_message": avail_error,
            "total_price": total_price, "currency": currency, "total_nights": total_nights,
            "tax_rate": tax_rate, "tax_amount": tax_amount, "tax_included": tax_included,
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
    return {"valid": error is None, "message": error or "Código válido", "discount_percent": discount or 0}


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
    db = get_database()
    filters: dict[str, Any] = {}
    if status_filter:
        filters["status"] = status_filter
    if prop_id:
        filters["prop_id"] = prop_id
    bookings = list(db.booking_orders.find(filters, {"_id": 0}).sort([("created_at", -1)]))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Booking ID", "Prop ID", "Status", "Guest Name", "Guest Email", "Guest Phone",
                      "Check-in", "Check-out", "Adults", "Children", "Rooms",
                      "Total Price", "Currency", "Total Nights", "Booking Source", "Created At", "Comment"])
    for b in bookings:
        writer.writerow([b.get(k, "") for k in ("booking_id", "prop_id", "status", "guest_name", "guest_email",
            "guest_phone", "check_in_date", "check_out_date", "adults", "children", "rooms",
            "total_price", "currency", "total_nights", "booking_source", "created_at", "comment")])
    output.seek(0)
    raw_date = str(bookings[0].get("created_at", "export"))[:10] if bookings else "export"
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reservas_{raw_date}.csv"})


@api_router.get("/{booking_id}")
def reservation_detail_api(booking_id: str, current_user: dict = Depends(require_login)):
    detail = get_booking_detail(booking_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return detail


@api_router.post("/{booking_id}/cancel")
def reservation_cancel_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    try:
        return cancel_booking(booking_id, reason=str(payload.get("reason") or "cancelled_by_user"),
            changed_by=str(payload.get("changed_by") or "angular_api"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/confirm")
def reservation_confirm_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    role = current_user.get("primary_role", "")
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede confirmar reservas.")
    try:
        return confirm_booking(booking_id, reason=str(payload.get("reason") or "confirmed_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/reject")
def reservation_reject_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    role = current_user.get("primary_role", "")
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede rechazar reservas.")
    try:
        return reject_booking(booking_id, reason=str(payload.get("reason") or "rejected_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.patch("/{booking_id}")
def reservation_modify_api(booking_id: str, payload: dict = Body(default={}), current_user: dict = Depends(require_login)):
    try:
        return modify_booking(booking_id,
            check_in_date=str(payload["check_in_date"]) if payload.get("check_in_date") else None,
            check_in_time=str(payload["check_in_time"]) if payload.get("check_in_time") else None,
            check_out_date=str(payload["check_out_date"]) if payload.get("check_out_date") else None,
            room_type_id=str(payload["room_type_id"]) if payload.get("room_type_id") else None,
            rooms=int(payload["rooms"]) if payload.get("rooms") is not None else None,
            comment=str(payload["comment"]) if payload.get("comment") is not None else None,
            changed_by=current_user.get("username", "angular_api"),
            selected_amenities=payload.get("selected_amenities"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/room-guests")
def room_guests_get_api(booking_id: str, current_user: dict = Depends(require_login)):
    return get_room_guests(booking_id)


@api_router.put("/{booking_id}/room-guests")
def room_guests_put_api(booking_id: str, payload: dict = Body(...), current_user: dict = Depends(require_login)):
    try:
        return save_room_guests(booking_id, payload.get("room_guests", []))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/check-in-status")
def check_in_status_api(booking_id: str, current_user: dict = Depends(require_login)):
    return get_check_in_status(booking_id)
