from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from src.database.connection import get_database
from src.app.security.session import ensure_utc
from src.app.core.timezone import local_now, local_today

from src.app.modules.reservations.notifications import notify_guest_status_change
from src.app.modules.partner.services.audit import register_action
from ._helpers import utc_now


logger = logging.getLogger(__name__)


def auto_cancel_expired_pending() -> dict[str, Any]:
    """Cancel all pending bookings older than 24 hours.

    Returns a summary dict with counts of cancelled bookings and any errors.
    """
    db = get_database()
    cutoff = utc_now() - timedelta(hours=24)
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


def _resolve_penalty_percent(
    prop_id: int,
    room_type_id: str = "",
    rate_plan_id: str = "",
) -> int:
    """Read cancellation_penalty_percent from hotel_policies.

    Hierarchy: rate_plan > room_type > hotel-wide.
    Returns the configured percentage (0-100), defaulting to 100
    if no policy is found (full penalty).
    """
    db = get_database()
    policy = None
    if rate_plan_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "rate_plan_id": rate_plan_id},
            {"_id": 0, "cancellation_penalty_percent": 1},
        )
    if not policy and room_type_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_penalty_percent": 1},
        )
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_penalty_percent": 1},
        )
    if not policy:
        return 100
    return int(policy.get("cancellation_penalty_percent", 100) or 100)


def _calculate_cancellation_penalty(
    prop_id: int,
    check_in_date: str,
    total_price: float | None,
    total_nights: int,
    room_type_id: str = "",
    rate_plan_id: str = "",
) -> dict[str, Any]:
    """Determine if a cancellation penalty applies based on hotel policy.

    Checks rate-plan-specific policies first, then room-type, then hotel-wide.

    Returns a dict with:
      - free_cancellation: bool
      - penalty_percent: int
      - penalty_amount: float
      - hours_until_checkin: int | None
      - cancellation_hours: int
    """
    if not check_in_date:
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": 0}

    db = get_database()
    # Hierarchy: rate_plan > room_type > hotel-wide
    policy = None
    # 1. Rate-plan-specific policy
    if rate_plan_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "rate_plan_id": rate_plan_id},
            {"_id": 0, "cancellation_hours": 1, "cancellation_penalty_percent": 1},
        )
    # 2. Room-type-specific policy
    if not policy and room_type_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_hours": 1, "cancellation_penalty_percent": 1},
        )
    # 3. Hotel-wide fallback
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_hours": 1, "cancellation_penalty_percent": 1},
        )
    if not policy:
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": 0}

    cancellation_hours = int(policy.get("cancellation_hours", 0) or 0)
    penalty_percent = int(policy.get("cancellation_penalty_percent", 100) or 100)

    if cancellation_hours <= 0:
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": 0}

    try:
        checkin_dt = ensure_utc(datetime.strptime(check_in_date, "%Y-%m-%d"))
    except (ValueError, TypeError):
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": cancellation_hours}

    now = local_now()
    # check_in_date is at midnight, so hours_until = (checkin - now) total hours
    delta = checkin_dt - now
    hours_until_checkin = max(0, int(delta.total_seconds() / 3600))

    if hours_until_checkin >= cancellation_hours:
        # Outside penalty window → free cancellation
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": hours_until_checkin, "cancellation_hours": cancellation_hours}

    # Inside penalty window → calculate amount
    if total_price is None or total_price <= 0 or total_nights <= 0:
        penalty_amount = 0.0
    else:
        one_night = total_price / total_nights
        penalty_amount = round(one_night * penalty_percent / 100, 2)

    # If penalty rounds to zero (or there's nothing to charge), treat as free cancellation
    if penalty_amount <= 0:
        return {
            "free_cancellation": True,
            "penalty_percent": 0,
            "penalty_amount": 0.0,
            "hours_until_checkin": hours_until_checkin,
            "cancellation_hours": cancellation_hours,
        }

    return {
        "free_cancellation": False,
        "penalty_percent": penalty_percent,
        "penalty_amount": penalty_amount,
        "hours_until_checkin": hours_until_checkin,
        "cancellation_hours": cancellation_hours,
    }


def cancel_booking(booking_id: str, *, reason: str = "cancelled_by_user", changed_by: str = "web") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise ValueError("booking not found")
    if booking.get("status") != "pending":
        raise ValueError("only pending bookings can be cancelled")
    today_str = local_today()
    if today_str >= booking.get("check_in_date", ""):
        raise ValueError("No se puede cancelar una reserva cuya fecha de entrada ya ha comenzado o pasado.")

    # ── Calculate cancellation penalty ──
    penalty = _calculate_cancellation_penalty(
        prop_id=int(booking.get("prop_id", 0)),
        check_in_date=booking.get("check_in_date", ""),
        total_price=booking.get("total_price"),
        total_nights=int(booking.get("total_nights", 0)),
        room_type_id=booking.get("room_type_id", ""),
        rate_plan_id=booking.get("rate_plan_id", ""),
    )

    changed_at = utc_now()
    update_set: dict[str, Any] = {
        "status": "cancelled",
        "updated_at": changed_at,
        "cancel_reason": reason,
        "cancellation_free": penalty["free_cancellation"],
        "cancellation_penalty_percent": penalty["penalty_percent"],
        "cancellation_penalty_amount": penalty["penalty_amount"],
    }
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": update_set},
    )

    reason_detail = reason
    if not penalty["free_cancellation"]:
        reason_detail = f"{reason} — penalización: ${penalty['penalty_amount']:.2f} ({penalty['penalty_percent']}% de 1 noche)"

    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "cancelled",
            "changed_at": changed_at,
            "reason": reason_detail,
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
            "cancellation_penalty_amount": penalty["penalty_amount"],
            "cancellation_free": penalty["free_cancellation"],
        }
    )

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="cancel",
                summary=f"Reserva cancelada — {booking.get('guest_name', '')} — {penalty['penalty_amount']:.2f} USD penalización",
                changed_by=changed_by,
                metadata={"guest_name": booking.get("guest_name", ""), "reason": reason,
                         "free_cancellation": penalty["free_cancellation"],
                         "penalty_amount": penalty["penalty_amount"],
                         "penalty_percent": penalty["penalty_percent"]},
            )
        except Exception:
            logger.exception("Failed to register audit action for cancel %s", booking_id)
    if db.manual_reservations.count_documents({"booking_id": booking_id}) > 0:
        db.manual_reservations.update_one(
            {"booking_id": booking_id},
            {"$set": {"status": "cancelled", "updated_at": changed_at}},
        )

    # ── Register transaction on active shift ──
    if not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="cancellation",
                booking_id=booking_id,
                amount=-float(penalty["penalty_amount"]),
                description=f"Cancelación: {booking.get('guest_name', '')} — razón: {reason}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for cancellation %s", booking_id)

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
                reason=reason_detail,
            )
    except Exception:
        logger.exception("Failed to notify guest on cancel for booking %s", booking_id)

    return {
        "booking_id": booking_id,
        "status": "cancelled",
        "free_cancellation": penalty["free_cancellation"],
        "penalty_amount": penalty["penalty_amount"],
        "penalty_percent": penalty["penalty_percent"],
        "hours_until_checkin": penalty["hours_until_checkin"],
        "cancellation_hours": penalty["cancellation_hours"],
    }


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
