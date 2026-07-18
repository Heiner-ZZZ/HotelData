"""Helper functions for check-in/out operations."""

from __future__ import annotations

import secrets
import logging
from datetime import datetime
from typing import Any

from src.app.modules.reservations.notifications import notify_guest_status_change, notify_staff_check_event

logger = logging.getLogger(__name__)


def _generate_folio(prop_id: int) -> str:
    """Generate a unique folio number for a check-in."""
    date_part = datetime.now().strftime("%y%m%d")
    random_part = secrets.token_hex(2).upper()
    return f"FOL-{prop_id}-{date_part}-{random_part}"


def _notify_guest_check_in(booking_id: str, booking: dict[str, Any]) -> None:
    """Fire-and-forget: notify guest about check-in."""
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email:
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="checked_in",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=booking.get("check_in_date", ""),
                check_out_date=booking.get("check_out_date", ""),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
            )
    except Exception:
        logger.exception("Failed to notify guest on check-in for booking %s", booking_id)


def _notify_staff_check_in(booking_id: str, booking: dict[str, Any]) -> None:
    """Fire-and-forget: notify staff about check-in."""
    try:
        notify_staff_check_event(
            event_type="check_in",
            prop_id=int(booking.get("prop_id", 0)),
            booking_id=booking_id,
            guest_name=booking.get("guest_name", ""),
            check_in_date=booking.get("check_in_date", ""),
            check_out_date=booking.get("check_out_date", ""),
            total_nights=int(booking.get("total_nights", 0)),
        )
    except Exception:
        logger.exception("Failed to notify staff on check-in for booking %s", booking_id)


def _notify_guest_check_out(booking_id: str, booking: dict[str, Any]) -> None:
    """Notify guest about check-out."""
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="checked_out",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=booking.get("check_in_date", ""),
                check_out_date=booking.get("check_out_date", ""),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
            )
    except Exception:
        logger.exception("Failed to notify guest on check-out for booking %s", booking_id)


def _notify_staff_check_out(booking_id: str, booking: dict[str, Any]) -> None:
    """Notify staff about check-out."""
    try:
        notify_staff_check_event(
            event_type="check_out",
            prop_id=int(booking.get("prop_id", 0)),
            booking_id=booking_id,
            guest_name=booking.get("guest_name", ""),
            check_in_date=booking.get("check_in_date", ""),
            check_out_date=booking.get("check_out_date", ""),
            total_nights=int(booking.get("total_nights", 0)),
        )
    except Exception:
        logger.exception("Failed to notify staff on check-out for booking %s", booking_id)
