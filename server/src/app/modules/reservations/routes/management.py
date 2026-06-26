"""Management operations routes — check-in and check-out endpoints."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from pymongo import ASCENDING

from src.app.modules.reservations.service import (
    list_check_ins, list_check_outs, list_check_in_dates,
    list_check_out_dates, complete_check_in, complete_check_out,
)
from src.app.modules.reservations.service._helpers import utc_now
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

    # Available physical rooms of this type
    available_rooms = list(
        db.hotel_rooms.find(
            {"prop_id": prop_id, "room_type_id": room_type_id, "is_active": True},
            {"_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1, "floor": 1},
        )
        .sort([("room_number", ASCENDING)])
    )

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
        "changed_by": current_user.get("username", "angular_api"),
        "is_test": bool(booking.get("is_test")),
    })

    return {"booking_id": booking_id, "assigned_rooms": room_ids, "assigned_count": len(room_ids)}
