"""Status transition functions for reservation lifecycle.

Completes the status lifecycle:
  pending → confirmed → checked_in → checked_out
  pending → cancelled / rejected
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from src.app.modules.billing.service import generate_invoice_for_booking
from src.database.connection import get_database

from ..notifications import notify_guest_status_change
from ._helpers import utc_now



logger = logging.getLogger(__name__)


def _deduct_inventory(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str,
) -> None:
    """Decrement available_rooms in room_inventory_calendar for the stay dates."""
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    for date_str in dates:
        db.room_inventory_calendar.update_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
            {"$inc": {"available_rooms": -rooms}},
        )


def _restore_inventory(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str,
) -> None:
    """Increment available_rooms in room_inventory_calendar for the stay dates.

    Called on check-out to release rooms back to inventory.
    """
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    for date_str in dates:
        db.room_inventory_calendar.update_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
            {"$inc": {"available_rooms": rooms}},
        )


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

    result: dict[str, Any] = {"booking_id": booking_id, "status": target_status}

    # ── On confirm: check inventory + deduct ──
    if target_status == "confirmed":
        prop_id = int(booking.get("prop_id", 0))
        check_in = (booking.get("check_in_date") or "").strip()
        check_out = (booking.get("check_out_date") or "").strip()
        rooms = int(booking.get("rooms", 1))
        room_type = (booking.get("room_type_id") or "").strip()

        if check_in and check_out and prop_id > 0:
            from .lifecycle.create import _check_availability
            avail_error = _check_availability(prop_id, check_in, check_out, rooms, room_type)
            if avail_error:
                result["inventory_conflict"] = True
                result["inventory_warning"] = avail_error
                logger.warning(
                    "Inventory conflict when confirming %s: %s", booking_id, avail_error
                )
            else:
                # Inventory available → deduct
                try:
                    _deduct_inventory(prop_id, check_in, check_out, rooms, room_type)
                    logger.info(
                        "Inventory deducted for booking %s (%d rooms from %s to %s)",
                        booking_id, rooms, check_in, check_out,
                    )
                except Exception:
                    logger.exception("Failed to deduct inventory for booking %s", booking_id)
        else:
            logger.warning(
                "Cannot check inventory for booking %s: missing dates, prop_id=%s",
                booking_id, prop_id,
            )

    # ── Auto-generate invoice on confirm ──
    if target_status == "confirmed":
        try:
            booking_id_for_inv = booking.get("_id", booking.get("booking_id"))
            if booking_id_for_inv:
                inv_result = generate_invoice_for_booking(
                    booking_id=str(booking_id_for_inv),
                    total_price=booking.get("total_price"),
                    currency=booking.get("currency", "USD"),
                )
                if inv_result:
                    result["invoice"] = {
                        "id": inv_result.get("id", inv_result.get("_id", "")),
                        "invoice_number": inv_result.get("invoice_number", ""),
                        "total": inv_result.get("total", 0),
                        "status": inv_result.get("status", "issued"),
                    }
                    logger.info("Invoice %s auto-generated for booking %s", inv_result.get("invoice_number"), booking_id)
                else:
                    logger.warning("Could not generate invoice for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to auto-generate invoice for booking %s", booking_id)

    # ── Notify guest on confirmed / rejected ──
    if target_status in ("confirmed", "rejected"):
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email and not booking.get("is_test"):
                notify_guest_status_change(
                    booking_id=booking_id,
                    guest_name=booking.get("guest_name", ""),
                    guest_email=guest_email,
                    new_status=target_status,
                    prop_id=int(booking.get("prop_id", 0)),
                    check_in_date=booking.get("check_in_date", ""),
                    check_out_date=booking.get("check_out_date", ""),
                    total_price=booking.get("total_price"),
                    currency=booking.get("currency", "USD"),
                    total_nights=int(booking.get("total_nights", 0)),
                    reason=reason,
                )
        except Exception:
            logger.exception("Failed to notify guest for booking %s", booking_id)

    return result


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
