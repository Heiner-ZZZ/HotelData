"""Guests route — list guests by property with search and pagination."""

from __future__ import annotations

from urllib.parse import unquote

from fastapi import Depends, Query

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services.guests import list_guests_for_prop
from src.app.security.dependencies import require_permission

from src.database.connection import get_database


@api_router.get("/guests")
def guests_list_api(
    prop_id: int = Query(..., ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """List guests (deduplicated by email) for a property, with search + pagination."""
    return list_guests_for_prop(prop_id, q=q, page=page, page_size=page_size)


@api_router.get("/guests/{guest_email}/bookings")
def guest_bookings_api(
    guest_email: str,
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Return all bookings for a guest (by email) at a specific property."""
    db = get_database()
    decoded_email = unquote(guest_email)
    cursor = db.booking_orders.find(
        {"prop_id": prop_id, "guest_email": decoded_email},
        {
            "_id": 0,
            "booking_id": 1,
            "check_in_date": 1,
            "check_out_date": 1,
            "total_price": 1,
            "currency": 1,
            "status": 1,
            "payment_status": 1,
            "guest_name": 1,
            "adults": 1,
            "children": 1,
            "rooms": 1,
            "created_at": 1,
            "booking_source": 1,
        },
    ).sort("check_in_date", -1)
    items = list(cursor)
    return {
        "guest_email": decoded_email,
        "guest_name": items[0].get("guest_name", "") if items else "",
        "prop_id": prop_id,
        "total_bookings": len(items),
        "items": items,
    }
