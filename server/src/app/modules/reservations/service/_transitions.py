"""Status transition functions for reservation lifecycle.

Completes the status lifecycle:
  pending → confirmed → checked_in → checked_out
  pending → cancelled / rejected
"""
from __future__ import annotations

from typing import Any

from src.database.connection import get_database

from ._helpers import utc_now


def _transition_status(
    booking_id: str,
    *,
    target_status: str,
    allowed_current: str | set[str],
    reason: str,
    changed_by: str,
    extra_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic status transition with validation and history logging.

    Args:
        booking_id: The booking to transition.
        target_status: The status to set (e.g. "confirmed", "cancelled").
        allowed_current: The status(es) the booking must currently be in.
        reason: Reason string stored in the history record.
        changed_by: Who performed the transition.
        extra_updates: Additional fields to set on the booking document
                       (e.g. {"cancel_reason": "..."}).
    """
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise ValueError("booking not found")

    current = booking.get("status")
    allowed = {allowed_current} if isinstance(allowed_current, str) else set(allowed_current)
    if current not in allowed:
        raise ValueError(
            f"cannot transition from '{current}' to '{target_status}'; "
            f"allowed current statuses: {', '.join(sorted(allowed))}"
        )

    changed_at = utc_now()
    set_fields: dict[str, Any] = {"status": target_status, "updated_at": changed_at}
    if extra_updates:
        set_fields.update(extra_updates)
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": set_fields},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": target_status,
            "changed_at": changed_at,
            "reason": reason,
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    # Sync manual_reservations if applicable
    if db.manual_reservations.count_documents({"booking_id": booking_id}) > 0:
        db.manual_reservations.update_one(
            {"booking_id": booking_id},
            {"$set": {"status": target_status, "updated_at": changed_at}},
        )
    return {"booking_id": booking_id, "status": target_status}


def confirm_booking(
    booking_id: str,
    *,
    reason: str = "confirmed_by_staff",
    changed_by: str = "staff",
) -> dict[str, Any]:
    """Transition a booking from 'pending' to 'confirmed'."""
    return _transition_status(
        booking_id,
        target_status="confirmed",
        allowed_current="pending",
        reason=reason,
        changed_by=changed_by,
    )


def reject_booking(
    booking_id: str,
    *,
    reason: str = "rejected_by_staff",
    changed_by: str = "staff",
) -> dict[str, Any]:
    """Transition a booking from 'pending' to 'rejected'."""
    return _transition_status(
        booking_id,
        target_status="rejected",
        allowed_current="pending",
        reason=reason,
        changed_by=changed_by,
    )
