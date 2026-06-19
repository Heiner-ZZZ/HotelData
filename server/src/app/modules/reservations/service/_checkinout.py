from __future__ import annotations

from typing import Any

from src.database.connection import get_database

from ._helpers import CHECKIN_COMPLETED_STATUSES, CHECKOUT_COMPLETED_STATUSES, utc_now
from ._history_lookup import _booking_history_lookup, _derived_stay_status


def complete_check_in(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        raise ValueError("booking not found")
    history = _booking_history_lookup([booking_id]).get(booking_id, [])
    stay_status = _derived_stay_status(booking, history, flow="check_in")
    if stay_status in CHECKIN_COMPLETED_STATUSES:
        raise ValueError("booking already checked in")
    if booking.get("status") in {"cancelled", "rejected"}:
        raise ValueError("booking cannot be checked in from current reservation status")
    changed_at = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"stay_status": "checked_in", "updated_at": changed_at}},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "checked_in",
            "changed_at": changed_at,
            "reason": "front_desk_check_in",
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    return {"booking_id": booking_id, "stay_status": "checked_in"}


def complete_check_out(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        raise ValueError("booking not found")
    history = _booking_history_lookup([booking_id]).get(booking_id, [])
    stay_status = _derived_stay_status(booking, history, flow="check_out")
    if stay_status in CHECKOUT_COMPLETED_STATUSES:
        raise ValueError("booking already checked out")
    if booking.get("status") in {"cancelled", "rejected"}:
        raise ValueError("booking cannot be checked out from current reservation status")
    changed_at = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"stay_status": "checked_out", "updated_at": changed_at}},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "checked_out",
            "changed_at": changed_at,
            "reason": "front_desk_check_out",
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    return {"booking_id": booking_id, "stay_status": "checked_out"}
