"""Helper functions for check-in/out operations."""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Any, Literal

from src.app.modules.reservations.notifications import (
    notify_guest_status_change,
    notify_staff_check_event,
)
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _generate_folio(prop_id: int) -> str:
    """Generate a unique folio number for a check-in."""
    date_part = datetime.now(UTC).strftime("%y%m%d")
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


_WINDOW_EXTENSION_CONFIG: dict[str, dict[str, str]] = {
    "early_checkin": {
        "title": "Llegada anticipada",
        "label": "early check-in",
        "mode_prefix": "early",
        "event_phrase": "llegó antes de la hora de check-in:",
        "actual_label": "llegada real",
        "relative_phrase": "antes de las",
        "minutes_key": "minutes_before",
        "policy_key": "policy_check_in_time",
        "actual_key": "actual_check_in_time",
        "mode_key": "early_checkin_mode",
        "fee_key": "early_checkin_fee",
        "reason_key": "early_checkin_reason",
        "log_prefix": "Early check-in",
        "error_label": "early check-in",
    },
    "late_checkout": {
        "title": "Salida extendida",
        "label": "late check-out",
        "mode_prefix": "late",
        "event_phrase": "extendió la salida:",
        "actual_label": "check-out real",
        "relative_phrase": "después de las",
        "minutes_key": "minutes_after",
        "policy_key": "policy_check_out_time",
        "actual_key": "actual_check_out_time",
        "mode_key": "late_checkout_mode",
        "fee_key": "late_checkout_fee",
        "reason_key": "late_checkout_reason",
        "log_prefix": "Late check-out",
        "error_label": "late check-out",
    },
}


def _notify_staff_window_extension(
    booking_id: str,
    booking: dict[str, Any],
    *,
    window: Literal["early_checkin", "late_checkout"],
    minutes: int,
    policy_time: str,
    actual_time: str,
    fee: float,
    reason: str = "",
    mode: str = "",
) -> None:
    """Fire-and-forget: notifica una extensión de ventana operativa.

    ``window`` parametriza los únicos datos que cambian entre early check-in y
    late check-out: texto de la notificación, dirección temporal y nombres de
    metadata. La estructura de persistencia y la semántica de cortesía/cargo
    permanecen en una sola ruta.
    """
    try:
        db = get_database()
        spec = _WINDOW_EXTENSION_CONFIG[window]
        normalized_mode = str(mode or "").strip().lower()
        is_courtesy = normalized_mode == f"{spec['mode_prefix']}_courtesy"
        mode_label = "en cortesía" if is_courtesy else "aprobado"
        notification_type = f"{window}_{'courtesy' if is_courtesy else 'approved'}"
        subject = f"{spec['title']} — {spec['label']} {mode_label} ({booking_id})"
        mode_line = " sin cargo (dentro de la cortesía de la política)." if is_courtesy else ""
        fee_line = (
            f" Cargo: ${round(float(fee or 0), 2):.2f}."
            if not is_courtesy and (fee or 0) > 0
            else ""
        )
        reason_line = f" Motivo: {reason}." if reason else ""
        log_msg = f"{spec['log_prefix']} {('courtesy' if is_courtesy else 'approved')} notification queued for booking %s"
        db.notification_log.insert_one({
            "notification_type": notification_type,
            "entity_type": "booking",
            "entity_id": booking_id,
            "prop_id": int(booking.get("prop_id", 0) or 0),
            "recipient_email": "",
            "subject": subject,
            "message": (
                f"El huésped {booking.get('guest_name', '')} {spec['event_phrase']} "
                f"{spec['actual_label']} a las {actual_time} "
                f"({int(minutes or 0)} min {spec['relative_phrase']} "
                f"{policy_time or 'hora de política'})."
                f"{mode_line}{fee_line}{reason_line}"
            ),
            "status": "pending",
            "created_at": datetime.now(UTC),
            "metadata": {
                "booking_id": booking_id,
                "guest_name": booking.get("guest_name", ""),
                spec["minutes_key"]: int(minutes or 0),
                spec["policy_key"]: policy_time,
                spec["actual_key"]: actual_time,
                spec["mode_key"]: normalized_mode,
                spec["fee_key"]: round(float(fee or 0), 2),
                spec["reason_key"]: reason,
            },
        })
        logger.info(log_msg, booking_id)
    except Exception:
        logger.exception(
            "Failed to notify staff about %s for booking %s",
            spec.get("error_label", window),
            booking_id,
        )
