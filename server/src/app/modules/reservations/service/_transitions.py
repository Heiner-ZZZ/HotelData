"""Status transition functions for reservation lifecycle.

Completes the status lifecycle:
  pending → confirmed → checked_in → checked_out
  pending → cancelled / rejected
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from pymongo import ASCENDING

from src.app.modules.billing.service import generate_invoice_for_booking
from src.database.connection import get_database

from ..notifications import notify_guest_status_change
from ._helpers import utc_now



logger = logging.getLogger(__name__)


def _auto_assign_rooms(
    prop_id: int,
    room_type_id: str,
    check_in_date: str,
    check_out_date: str,
    rooms_required: int,
    booking_id: str,
    is_test: bool = False,
) -> list[str]:
    """Auto-assign physical rooms from hotel_rooms to a confirmed booking.

    Finds active rooms of the matching type, excludes rooms already assigned
    to other overlapping active bookings, and assigns up to ``rooms_required``.

    Returns the list of assigned hotel_room_id values.
    """
    if not room_type_id or rooms_required < 1:
        return []

    db = get_database()

    # 1. All active physical rooms of this type
    all_rooms = list(
        db.hotel_rooms.find(
            {"prop_id": prop_id, "room_type_id": room_type_id, "is_active": True},
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1},
        ).sort([("room_number", ASCENDING)])
    )
    if not all_rooms:
        logger.info(
            "No physical rooms found for prop_id=%s room_type=%s — skipping auto-assign",
            prop_id, room_type_id,
        )
        return []

    all_room_ids = [r["hotel_room_id"] for r in all_rooms]

    # 2. Rooms already assigned to other overlapping active bookings
    overlapping = list(
        db.booking_orders.find(
            {
                "booking_id": {"$ne": booking_id},
                "prop_id": prop_id,
                "status": {"$in": ["confirmed", "checked_in"]},
                "check_in_date": {"$lt": check_out_date},
                "check_out_date": {"$gt": check_in_date},
                "assigned_rooms.0": {"$exists": True},
            },
            {"_id": 0, "assigned_rooms": 1},
        )
    )
    assigned_elsewhere: set[str] = set()
    for booking in overlapping:
        for room_id in booking.get("assigned_rooms", []):
            assigned_elsewhere.add(room_id)

    # 3. Filter available rooms
    available = [r for r in all_rooms if r["hotel_room_id"] not in assigned_elsewhere]

    # 4. Take what we need
    to_assign = available[:rooms_required]
    if not to_assign:
        logger.warning(
            "No available rooms to auto-assign for booking %s (prop=%s, type=%s, needed=%d, total_rooms=%d, occupied=%d)",
            booking_id, prop_id, room_type_id, rooms_required,
            len(all_rooms), len(assigned_elsewhere),
        )
        return []

    assigned_ids = [r["hotel_room_id"] for r in to_assign]

    # 5. Update room_status_log → "occupied" for assigned rooms
    now_iso = utc_now()
    for room in to_assign:
        room_label = room.get("room_label", "")
        if room_label:
            try:
                db.room_status_log.update_one(
                    {"prop_id": prop_id, "room_label": room_label},
                    {
                        "$set": {
                            "status": "occupied",
                            "note": f"Auto-asignada desde reserva {booking_id}",
                            "updated_at": now_iso,
                        },
                        "$setOnInsert": {
                            "created_at": now_iso,
                            "prop_id": prop_id,
                            "room_type_id": room_type_id,
                            "room_label": room_label,
                            "hotel_room_id": room["hotel_room_id"],
                            "room_number": room.get("room_number", ""),
                        },
                    },
                    upsert=True,
                )
            except Exception:
                logger.exception("Failed to update room_status_log for %s", room_label)

    # 6. Update the booking document
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"assigned_rooms": assigned_ids, "updated_at": now_iso}},
    )

    # 7. Log in booking_status_history
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "confirmed",
        "changed_at": now_iso,
        "reason": f"rooms_auto_assigned: {', '.join(assigned_ids)}",
        "changed_by": "system",
        "is_test": is_test,
    })

    logger.info(
        "Auto-assigned %d room(s) to booking %s: %s",
        len(assigned_ids), booking_id, ", ".join(assigned_ids),
    )
    return assigned_ids


def _deduct_inventory(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str,
) -> None:
    """Decrement available_rooms in room_inventory_calendar for the stay dates.

    Uses atomic find_one_and_update with optimistic locking:
    only decrements if available_rooms >= rooms.
    Raises ValueError if any date has insufficient inventory.
    """
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    for date_str in dates:
        result = db.room_inventory_calendar.find_one_and_update(
            {
                "prop_id": prop_id,
                "room_type_id": room_type_id,
                "date": date_str,
                "available_rooms": {"$gte": rooms},  # Optimistic lock
            },
            {"$inc": {"available_rooms": -rooms}},
            projection={"_id": 0, "available_rooms": 1},
        )
        if result is None:
            # Check if the record exists at all
            existing = db.room_inventory_calendar.find_one(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                {"_id": 0, "available_rooms": 1},
            )
            if existing is None:
                raise ValueError(
                    f"No hay datos de inventario para la fecha {date_str}. "
                    f"No se puede confirmar la reserva sin inventario disponible."
                )
            else:
                current_avail = existing.get("available_rooms", 0)
                raise ValueError(
                    f"Inventario insuficiente para {date_str}: "
                    f"se requieren {rooms} habitación(es) pero solo hay {current_avail} disponible(s)."
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

    # ═══ Generate self-check-in token BEFORE persist (so it's included in $set) ═══
    if target_status == "confirmed":
        if extra_updates is None:
            extra_updates = {}
        extra_updates["self_check_in_token"] = secrets.token_urlsafe(24)
        extra_updates["self_check_in_token_used"] = False

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

    # ── On confirm: auto-assign physical rooms ──
    if target_status == "confirmed":
        prop_id = int(booking.get("prop_id", 0))
        room_type = (booking.get("room_type_id") or "").strip()
        check_in = (booking.get("check_in_date") or "").strip()
        check_out = (booking.get("check_out_date") or "").strip()
        rooms_count = int(booking.get("rooms", 1))

        if room_type and prop_id > 0 and check_in and check_out:
            try:
                assigned = _auto_assign_rooms(
                    prop_id=prop_id,
                    room_type_id=room_type,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    rooms_required=rooms_count,
                    booking_id=booking_id,
                    is_test=bool(booking.get("is_test", False)),
                )
                if assigned:
                    result["assigned_rooms"] = assigned
                    result["assigned_count"] = len(assigned)
                elif rooms_count > 0:
                    logger.warning(
                        "Could not auto-assign rooms for booking %s (needed %d, found none)",
                        booking_id, rooms_count,
                    )
            except Exception:
                logger.exception("Failed to auto-assign rooms for booking %s", booking_id)

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
                # Inventory available → deduct with optimistic locking
                try:
                    _deduct_inventory(prop_id, check_in, check_out, rooms, room_type)
                    logger.info(
                        "Inventory deducted for booking %s (%d rooms from %s to %s)",
                        booking_id, rooms, check_in, check_out,
                    )
                except ValueError as inv_err:
                    result["inventory_conflict"] = True
                    result["inventory_warning"] = str(inv_err)
                    logger.warning(
                        "Inventory conflict for booking %s: %s", booking_id, inv_err
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
