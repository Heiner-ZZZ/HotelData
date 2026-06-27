from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.database.connection import get_database

from ..notifications import notify_guest_status_change
from ._helpers import utc_now


logger = logging.getLogger(__name__)


def auto_cancel_expired_pending() -> dict[str, Any]:
    """Cancel all pending bookings older than 24 hours.

    Returns a summary dict with counts of cancelled bookings and any errors.
    """
    db = get_database()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_str = cutoff.isoformat()

    expired = list(
        db.booking_orders.find(
            {"status": "pending", "created_at": {"$lt": cutoff_str}},
            {"_id": 0, "booking_id": 1, "guest_name": 1, "guest_email": 1, "is_test": 1,
             "prop_id": 1, "check_in_date": 1, "check_out_date": 1, "total_price": 1,
             "currency": 1, "total_nights": 1, "created_at": 1},
        )
    )

    if not expired:
        logger.info("auto_cancel_expired_pending: no expired pending bookings found")
        return {"cancelled": 0, "errors": [], "expired_count": 0}

    cancelled = 0
    errors: list[str] = []
    for booking in expired:
        booking_id = booking["booking_id"]
        try:
            cancel_booking(
                booking_id,
                reason="auto_cancel_24h",
                changed_by="auto_cancel_scheduler",
            )
            cancelled += 1
            logger.info("Auto-cancelled expired booking %s (created: %s)", booking_id, booking.get("created_at"))
        except Exception as exc:
            err_msg = f"{booking_id}: {exc}"
            errors.append(err_msg)
            logger.exception("Failed to auto-cancel booking %s", booking_id)

    # Log execution to etl_executions
    try:
        db.etl_executions.insert_one({
            "execution_id": f"AUTO_CANCEL_{utc_now().strftime('%Y%m%d%H%M%S')}",
            "executed_at": utc_now(),
            "pipeline": "auto_cancel_pending",
            "status": "completed" if not errors else "completed_with_errors",
            "summary": {
                "expired_found": len(expired),
                "cancelled": cancelled,
                "errors": len(errors),
            },
        })
    except Exception as exc:
        logger.exception("Failed to log auto_cancel execution: %s", exc)

    return {
        "cancelled": cancelled,
        "errors": errors,
        "expired_count": len(expired),
    }


def cancel_booking(booking_id: str, *, reason: str = "cancelled_by_user", changed_by: str = "web") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise ValueError("booking not found")
    if booking.get("status") != "pending":
        raise ValueError("only pending bookings can be cancelled")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today_str >= booking.get("check_in_date", ""):
        raise ValueError("No se puede cancelar una reserva cuya fecha de entrada ya ha comenzado o pasado.")
    changed_at = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "cancelled", "updated_at": changed_at, "cancel_reason": reason}},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "cancelled",
            "changed_at": changed_at,
            "reason": reason,
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    if db.manual_reservations.count_documents({"booking_id": booking_id}) > 0:
        db.manual_reservations.update_one(
            {"booking_id": booking_id},
            {"$set": {"status": "cancelled", "updated_at": changed_at}},
        )

    # ── Notify guest on cancellation ──
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="cancelled",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=booking.get("check_in_date", ""),
                check_out_date=booking.get("check_out_date", ""),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
                reason=reason,
            )
    except Exception:
        logger.exception("Failed to notify guest on cancel for booking %s", booking_id)

    return {"booking_id": booking_id, "status": "cancelled"}


def cleanup_test_booking(booking_id: str) -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "is_test": 1})
    if booking is None:
        return {"booking_id": booking_id, "deleted": False, "reason": "not_found"}
    if not booking.get("is_test"):
        return {"booking_id": booking_id, "deleted": False, "reason": "not_marked_as_test"}
    deleted = {
        "booking_orders": db.booking_orders.delete_one({"booking_id": booking_id}).deleted_count,
        "booking_guests": db.booking_guests.delete_many({"booking_id": booking_id}).deleted_count,
        "booking_status_history": db.booking_status_history.delete_many({"booking_id": booking_id}).deleted_count,
        "manual_reservations": db.manual_reservations.delete_many({"booking_id": booking_id}).deleted_count,
    }
    return {"booking_id": booking_id, "deleted": True, "counts": deleted}
