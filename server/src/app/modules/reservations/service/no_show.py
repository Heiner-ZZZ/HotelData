"""No-show processing — integrated into the reservations service module.

A no-show occurs when a guest with a confirmed reservation never arrives
on check-in day. The hotel charges the first night as penalty.

- process_no_show(): marks a single booking as no-show, charges penalty,
  restores inventory, posts to folio, sends notification email.
- auto_process_no_shows(): scheduled daily task that finds confirmed
  bookings whose check-in date has passed without arrival.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from src.app.core.timezone import local_today
from src.app.modules.partner.services.audit import register_action

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _room_rate_per_night(booking: dict) -> float:
    """Calculate the room rate per night from the booking."""
    total_price = float(booking.get("total_price", 0) or 0)
    total_nights = int(booking.get("total_nights", 1)) or 1
    return round(total_price / total_nights, 2)


def process_no_show(
    booking_id: str,
    *,
    changed_by: str = "no_show_scheduler",
) -> dict[str, Any]:
    """Mark a confirmed booking as no-show and charge first night penalty.

    Only applicable to bookings with status="confirmed" and stay_status="pending"
    whose check-in date has already passed.

    Returns {"ok": True, "penalty_amount": X.XX} or raises ValueError.
    """
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id, "status": "confirmed", "stay_status": "pending"},
    )
    if not booking:
        raise ValueError("Reserva no encontrada o no está en estado válido para no-show.")

    check_in_str = str(booking.get("check_in_date", ""))[:10]
    try:
        check_in_date = date.fromisoformat(check_in_str)
    except ValueError:
        raise ValueError(f"Fecha de check-in inválida: {check_in_str}")

    today = date.fromisoformat(local_today())
    if check_in_date > today:
        raise ValueError(
            f"No se puede marcar como no-show antes del check-in "
            f"({check_in_str}). Hoy es {today}."
        )

    # Calculate first night penalty — read penalty % from hotel_policies
    from src.app.modules.reservations.service.cleanup import _resolve_penalty_percent
    penalty_pct = _resolve_penalty_percent(
        prop_id=int(booking.get("prop_id", 0)),
        room_type_id=str(booking.get("room_type_id", "")),
        rate_plan_id=str(booking.get("rate_plan_id", "")),
    )
    rate_per_night = _room_rate_per_night(booking)
    penalty_amount = round(rate_per_night * penalty_pct / 100, 2)

    # If penalty_pct > 0 but rate is so low it rounds to zero, charge at least the full night
    if penalty_pct > 0 and penalty_amount <= 0:
        penalty_amount = rate_per_night

    now = _now()

    # Update booking
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "stay_status": "no_show",
                "no_show_penalty_amount": penalty_amount,
                "no_show_penalty_percent": penalty_pct,
                "no_show_processed_at": now,
                "no_show_processed_by": changed_by,
                "updated_at": now,
            }
        },
    )

    # Restore inventory (rooms were deducted on confirm, release them)
    try:
        from src.app.modules.reservations.service._transitions import _restore_inventory
        _restore_inventory(
            prop_id=int(booking.get("prop_id", 0)),
            check_in_date=str(booking.get("check_in_date", "")),
            check_out_date=str(booking.get("check_out_date", "")),
            rooms=int(booking.get("rooms", 1)),
            room_type_id=str(booking.get("room_type_id", "")),
        )
    except Exception:
        logger.exception("Failed to restore inventory for no-show %s", booking_id)

    # Create minimal folio with penalty only (no room charge — guest never checked in)
    try:
        from src.app.modules.billing.service.folio import FOLIO_COLLECTION

        existing_folio = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
        if not existing_folio:
            folio_number = f"FL-NS-{booking_id[:8].upper()}"
            db[FOLIO_COLLECTION].insert_one({
                "folio_number": folio_number,
                "booking_id": booking_id,
                "prop_id": int(booking.get("prop_id", 0)),
                "guest_name": booking.get("guest_name", ""),
                "guest_email": booking.get("guest_email", ""),
                "check_in_date": check_in_str,
                "check_out_date": str(booking.get("check_out_date", "")),
                "status": "open",
                "total_room": 0.0,
                "total_charges": penalty_amount,
                "total_discounts": 0.0,
                "total_payments": 0.0,
                "total_due": penalty_amount,
                "postings": [{
                    "posting_id": ObjectId(),
                    "type": "charge",
                    "category": "Penalización",
                    "concept": f"No-show — Penalización del {penalty_pct}% de 1 noche ({check_in_str})",
                    "amount": penalty_amount,
                    "quantity": 1,
                    "unit_price": penalty_amount,
                    "reference_id": booking_id,
                    "reference_type": "no_show_penalty",
                    "posted_at": now,
                }],
                "posting_count": 1,
                "created_at": now,
                "closed_at": None,
                "closed_by": None,
                "invoice_id": None,
            })
        else:
            from src.app.modules.billing.service.folio import post_to_folio
            post_to_folio(
                booking_id,
                posting_type="charge",
                category="Penalización",
                concept=f"No-show — Penalización del {penalty_pct}% de 1 noche ({check_in_str})",
                amount=penalty_amount,
                quantity=1,
                reference_id=booking_id,
                reference_type="no_show_penalty",
            )
    except Exception:
        logger.exception("Failed to post no-show penalty to folio for %s", booking_id)

    # Log in history
    reason_detail = (
        f"No-show — penalización: ${penalty_amount:.2f} "
        f"({penalty_pct}% de 1 noche de {booking.get('total_nights', 1)} reservadas)"
    )
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "no_show",
        "changed_at": now,
        "reason": reason_detail,
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test")),
    })

    # Audit log
    if not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="no_show",
                summary=f"No-show registrado — {booking.get('guest_name', '')} — penalización ${penalty_amount:.2f}",
                changed_by=changed_by,
                metadata={
                    "guest_name": booking.get("guest_name", ""),
                    "check_in_date": check_in_str,
                    "penalty_amount": penalty_amount,
                },
            )
        except Exception:
            logger.exception("Failed to register audit action for no-show %s", booking_id)

    # Deactivate stay session if exists
    try:
        db.stay_sessions.update_many(
            {"booking_id": booking_id, "active": True},
            {"$set": {"active": False, "deactivated_at": now}},
        )
    except Exception:
        logger.exception("Failed to deactivate stay session for no-show %s", booking_id)

    # Notify guest via email
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            from src.app.modules.reservations.notifications import notify_guest_status_change
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="no_show",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=check_in_str,
                check_out_date=str(booking.get("check_out_date", "")),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
                reason=reason_detail,
            )
    except Exception:
        logger.exception("Failed to notify guest on no-show for booking %s", booking_id)

    logger.info(
        "No-show processed for booking %s: $%.2f penalty charged",
        booking_id, penalty_amount,
    )

    return {
        "ok": True,
        "booking_id": booking_id,
        "penalty_amount": penalty_amount,
        "check_in_date": check_in_str,
    }


def auto_process_no_shows() -> dict[str, Any]:
    """Daily task: find confirmed bookings whose check-in date has passed.

    Processes bookings with status="confirmed", stay_status="pending",
    and check_in_date < today (yesterday or earlier).

    Returns a summary dict with counts of processed no-shows and any errors.
    """
    db = get_database()
    today = local_today()

    candidates = list(
        db.booking_orders.find(
            {
                "status": "confirmed",
                "stay_status": "pending",
                "check_in_date": {"$lt": today},
            },
            {
                "_id": 0,
                "booking_id": 1,
                "guest_name": 1,
                "guest_email": 1,
                "is_test": 1,
                "prop_id": 1,
                "check_in_date": 1,
                "check_out_date": 1,
                "total_price": 1,
                "currency": 1,
                "total_nights": 1,
            },
        )
    )

    if not candidates:
        logger.info("auto_process_no_shows: no bookings to process")
        return {"processed": 0, "errors": [], "candidate_count": 0}

    processed = 0
    errors: list[str] = []

    for booking in candidates:
        booking_id = booking["booking_id"]
        try:
            process_no_show(booking_id, changed_by="no_show_scheduler")
            processed += 1
            logger.info("Auto no-show processed for booking %s", booking_id)
        except Exception as exc:
            err_msg = f"{booking_id}: {exc}"
            errors.append(err_msg)
            logger.exception("Failed to process no-show for booking %s", booking_id)

    # Log execution
    try:
        db.etl_executions.insert_one({
            "execution_id": f"NO_SHOW_{_now().strftime('%Y%m%d%H%M%S')}",
            "executed_at": _now(),
            "pipeline": "auto_no_show",
            "status": "completed" if not errors else "completed_with_errors",
            "summary": {
                "candidates_found": len(candidates),
                "processed": processed,
                "errors": len(errors),
            },
        })
    except Exception as exc:
        logger.exception("Failed to log auto_no_show execution: %s", exc)

    return {
        "processed": processed,
        "errors": errors,
        "candidate_count": len(candidates),
    }
