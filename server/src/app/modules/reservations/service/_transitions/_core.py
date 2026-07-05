"""Core status transition logic for reservation lifecycle."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from src.database.connection import get_database
from src.app.core.state_machine import booking_sm
from .._helpers import utc_now
from src.app.modules.reservations.notifications import notify_guest_status_change
from src.app.modules.billing.service import generate_invoice_for_booking
from src.app.modules.partner.services.audit import register_action
from src.app.modules.reservations.service._transitions._inventory import (
    _auto_assign_rooms,
    _deduct_inventory,
    _restore_inventory,
)

logger = logging.getLogger(__name__)


def _transition_status(
    booking_id: str,
    *,
    target_status: str,
    reason: str,
    changed_by: str,
    extra_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transition a booking's status using the central booking StateMachine."""
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise ValueError("booking not found")

    current = booking.get("status")
    # Use central StateMachine for validation
    booking_sm.validate_transition(current, target_status)

    if target_status == "confirmed":
        if extra_updates is None:
            extra_updates = {}
        extra_updates["self_check_in_token"] = secrets.token_urlsafe(24)
        extra_updates["self_check_in_token_used"] = False

    changed_at = utc_now()
    set_fields: dict[str, Any] = {"status": target_status, "updated_at": changed_at}
    if extra_updates:
        set_fields.update(extra_updates)
    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": set_fields})
    db.booking_status_history.insert_one({
        "booking_id": booking_id, "status": target_status,
        "changed_at": changed_at, "reason": reason,
        "changed_by": changed_by, "is_test": bool(booking.get("is_test")),
    })

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test") and target_status in ("confirmed", "rejected"):
        try:
            action_verb = "confirm" if target_status == "confirmed" else "reject"
            summary_label = "confirmada" if target_status == "confirmed" else "rechazada"
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action=action_verb,
                summary=f"Reserva {summary_label} — {booking.get('guest_name', '')}",
                changed_by=changed_by,
                metadata={"guest_name": booking.get("guest_name", ""), "new_status": target_status, "reason": reason},
            )
        except Exception:
            logger.exception("Failed to register audit action for %s booking %s", target_status, booking_id)
    if db.manual_reservations.count_documents({"booking_id": booking_id}) > 0:
        db.manual_reservations.update_one(
            {"booking_id": booking_id},
            {"$set": {"status": target_status, "updated_at": changed_at}},
        )

    result: dict[str, Any] = {"booking_id": booking_id, "status": target_status}

    # ── On confirm: auto-assign rooms + inventory check ──
    if target_status == "confirmed":
        prop_id = int(booking.get("prop_id", 0))
        room_type = (booking.get("room_type_id") or "").strip()
        check_in = (booking.get("check_in_date") or "").strip()
        check_out = (booking.get("check_out_date") or "").strip()
        rooms_count = int(booking.get("rooms", 1))

        if room_type and prop_id > 0 and check_in and check_out:
            try:
                assigned = _auto_assign_rooms(
                    prop_id=prop_id, room_type_id=room_type,
                    check_in_date=check_in, check_out_date=check_out,
                    rooms_required=rooms_count, booking_id=booking_id,
                    is_test=bool(booking.get("is_test", False)),
                )
                if assigned:
                    result["assigned_rooms"] = assigned
                    result["assigned_count"] = len(assigned)
            except Exception:
                logger.exception("Failed to auto-assign rooms for booking %s", booking_id)

        if check_in and check_out and prop_id > 0:
            from src.app.modules.reservations.service.lifecycle.create._availability import _check_availability
            avail_error = _check_availability(prop_id, check_in, check_out, rooms_count, room_type)
            if avail_error:
                result["inventory_conflict"] = True
                result["inventory_warning"] = avail_error
                logger.warning("Inventory conflict when confirming %s: %s", booking_id, avail_error)
            else:
                try:
                    _deduct_inventory(prop_id, check_in, check_out, rooms_count, room_type)
                    logger.info("Inventory deducted for booking %s", booking_id)
                except ValueError as inv_err:
                    result["inventory_conflict"] = True
                    result["inventory_warning"] = str(inv_err)
                    logger.warning("Inventory conflict for booking %s: %s", booking_id, inv_err)
                except Exception:
                    logger.exception("Failed to deduct inventory for booking %s", booking_id)

        # ── Auto-generate invoice ──
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
                    booking_id=booking_id, guest_name=booking.get("guest_name", ""),
                    guest_email=guest_email, new_status=target_status,
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
    booking_id: str, *, reason: str = "confirmed_by_staff", changed_by: str = "staff",
) -> dict[str, Any]:
    """Transition a booking from 'pending' to 'confirmed'."""
    return _transition_status(
        booking_id, target_status="confirmed",
        reason=reason, changed_by=changed_by,
    )


def reject_booking(
    booking_id: str, *, reason: str = "rejected_by_staff", changed_by: str = "staff",
) -> dict[str, Any]:
    """Transition a booking from 'pending' to 'rejected'."""
    return _transition_status(
        booking_id, target_status="rejected",
        reason=reason, changed_by=changed_by,
    )
