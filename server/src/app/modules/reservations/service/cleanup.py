from __future__ import annotations

from typing import Any

from ._transitions import _transition_status


def cancel_booking(booking_id: str, *, reason: str = "cancelled_by_user", changed_by: str = "web") -> dict[str, Any]:
    """Transition a booking from 'pending' to 'cancelled'.

    Delegates to _transition_status() with extra_updates to store
    cancel_reason on the booking document.
    """
    return _transition_status(
        booking_id,
        target_status="cancelled",
        allowed_current="pending",
        reason=reason,
        changed_by=changed_by,
        extra_updates={"cancel_reason": reason},
    )


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
