"""Public self-check-in endpoint — no authentication required.

Guests can check in using a booking_id + token (embedded in a QR code)
without needing staff assistance or login credentials.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

from src.app.modules.reservations.service._checkinout import complete_check_in
from src.database.connection import get_database

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/check-in", tags=["check-in-public"])


@public_router.post("/auto")
def auto_check_in_api(
    booking_id: str = Query(..., min_length=1, description="Booking ID (BK-...)"),
    token: str = Query(..., min_length=1, description="Self-check-in token from booking"),
    payment_method: str = Query(default="", description="Optional payment method (e.g. cash, card)"),
):
    """Public endpoint for guest self-check-in using a QR-code token.

    Validates the token against the booking document, then completes
    the check-in process (marks stay_status, notifies guest/staff,
    marks rooms as occupied, notifies housekeeping).

    URL example (for QR code):
      /api/check-in/auto?booking_id=BK-20250101-ABC123&token=<token>
    """
    if not booking_id or not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="booking_id and token are required.",
        )

    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "self_check_in_token": 1, "self_check_in_token_used": 1,
         "status": 1, "stay_status": 1},
    )

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    # ── Validate token ──
    stored_token = booking.get("self_check_in_token", "")
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking does not support self-check-in (no token generated).",
        )

    if booking.get("self_check_in_token_used", False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Self-check-in token has already been used.",
        )

    if stored_token != token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token.",
        )

    # ── Validate booking status ──
    if booking.get("status") in ("cancelled", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in — booking status is '{booking.get('status')}'.",
        )

    if booking.get("stay_status") == "checked_in":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking is already checked in.",
        )

    # ── Mark token as used (prevent replay) ──
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"self_check_in_token_used": True}},
    )

    # ── Complete check-in ──
    try:
        result = complete_check_in(
            booking_id,
            changed_by="guest_self_check_in",
            payment_method=payment_method,
        )
        result["self_check_in"] = True
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
