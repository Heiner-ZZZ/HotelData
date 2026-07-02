"""Staff notification functions for new bookings and check events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.app.email.service import send_email
from src.database.connection import get_database
from ..email_templates import staff_check_event_html, staff_new_booking_html

logger = logging.getLogger(__name__)

STAFF_ROLES = ("hotel_partner", "gerente_hotel")
ADMIN_ROLES = ("super_admin", "admin_sistema")


def _assigned_hotel_ids(user: dict[str, Any]) -> list[int]:
    assigned = user.get("assigned_hotels")
    if not isinstance(assigned, list) or not assigned:
        return []
    try:
        return [int(p) for p in assigned if p is not None]
    except (ValueError, TypeError):
        return []


def _log_notification(
    *,
    notification_type: str,
    recipient_email: str,
    recipient_name: str,
    booking_id: str,
    prop_id: int,
    status: str,
    error_message: str = "",
) -> None:
    try:
        db = get_database()
        db.notification_log.insert_one({
            "notification_type": notification_type,
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "booking_id": booking_id,
            "prop_id": prop_id,
            "status": status,
            "error_message": error_message,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        logger.exception("Failed to write notification_log for %s (%s)", notification_type, booking_id)


def notify_staff_new_booking(
    prop_id: int,
    booking_id: str,
    guest_name: str,
    guest_email: str,
    check_in_date: str,
    check_out_date: str,
    adults: int,
    children: int,
    rooms: int,
    total_price: float | None,
    currency: str,
    total_nights: int,
    comment: str = "",
) -> None:
    db = get_database()
    candidates = list(
        db.users.find(
            {"primary_role": {"$in": STAFF_ROLES + ADMIN_ROLES}, "is_active": True},
            {"_id": 0, "username": 1, "display_name": 1, "email": 1, "primary_role": 1, "assigned_hotels": 1},
        )
    )

    recipients: list[tuple[str, str]] = []
    for user in candidates:
        role = user.get("primary_role", "")
        email = user.get("email", "").strip()
        if not email:
            continue
        if role in ADMIN_ROLES:
            recipients.append((email, user.get("display_name") or user.get("username", "Admin")))
            continue
        assigned = _assigned_hotel_ids(user)
        if prop_id in assigned:
            recipients.append((email, user.get("display_name") or user.get("username", "Staff")))

    if not recipients:
        logger.info("No staff recipients found for prop_id=%s booking=%s", prop_id, booking_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/management/recepcion/{booking_id}"

    hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "display_name": 1, "display_label": 1, "hotel_name": 1},
    )
    hotel_label = (
        (hotel or {}).get("display_label")
        or (hotel or {}).get("display_name")
        or (hotel or {}).get("hotel_name")
        or f"Propiedad #{prop_id}"
    )

    price_line = f"<strong>{total_price:.2f} {currency}</strong>" if total_price is not None else "Pendiente de cálculo"
    nights_label = f"{total_nights} {'noche' if total_nights == 1 else 'noches'}"
    guests_label = f"{adults} adulto{'s' if adults != 1 else ''}"
    if children > 0:
        guests_label += f", {children} niño{'s' if children != 1 else ''}"
    guests_label += f" · {rooms} habitaci{'ón' if rooms == 1 else 'ones'}"

    comment_section = (
        f"""<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;vertical-align:top;white-space:nowrap">Comentario</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">{comment}</td></tr>"""
        if comment else ""
    )

    html_template = staff_new_booking_html(
        hotel_label=hotel_label, booking_id=booking_id, guest_name=guest_name,
        guest_email=guest_email, check_in_date=check_in_date, check_out_date=check_out_date,
        nights_label=nights_label, guests_label=guests_label, price_line=price_line,
        comment_section=comment_section, detail_url=detail_url,
    )

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            html = html_template.replace("{{STAFF_NAME}}", name)
            ok = send_email(email, f"Nueva reserva pendiente — {booking_id}", html)
            if ok:
                logger.info("Notification sent to %s (%s) for booking %s", name, email, booking_id)
                status = "sent"
            else:
                logger.warning("Failed to notify %s (%s) for booking %s", name, email, booking_id)
                status = "failed"
                error_msg = "send_email returned False"
        except Exception as exc:
            logger.exception("Error notifying %s for booking %s", email, booking_id)
            error_msg = str(exc)
        _log_notification(
            notification_type="staff_new_booking", recipient_email=email,
            recipient_name=name, booking_id=booking_id, prop_id=prop_id,
            status=status, error_message=error_msg,
        )


def notify_staff_check_event(
    event_type: str,
    prop_id: int,
    booking_id: str,
    guest_name: str,
    check_in_date: str,
    check_out_date: str,
    total_nights: int,
) -> None:
    db = get_database()
    candidates = list(
        db.users.find(
            {"primary_role": {"$in": STAFF_ROLES + ADMIN_ROLES}, "is_active": True},
            {"_id": 0, "username": 1, "display_name": 1, "email": 1, "primary_role": 1, "assigned_hotels": 1},
        )
    )

    recipients: list[tuple[str, str]] = []
    for user in candidates:
        role = user.get("primary_role", "")
        email = user.get("email", "").strip()
        if not email:
            continue
        if role in ADMIN_ROLES:
            recipients.append((email, user.get("display_name") or user.get("username", "Admin")))
            continue
        assigned = _assigned_hotel_ids(user)
        if prop_id in assigned:
            recipients.append((email, user.get("display_name") or user.get("username", "Staff")))

    if not recipients:
        logger.info("No staff recipients for check-event notification prop_id=%s booking=%s", prop_id, booking_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/management/recepcion/{booking_id}"

    hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "display_name": 1, "display_label": 1, "hotel_name": 1},
    )
    hotel_label = (
        (hotel or {}).get("display_label")
        or (hotel or {}).get("display_name")
        or (hotel or {}).get("hotel_name")
        or f"Propiedad #{prop_id}"
    )

    nights_label = f"{total_nights} {'noche' if total_nights == 1 else 'noches'}"
    html_template = staff_check_event_html(
        event_type=event_type, hotel_label=hotel_label, booking_id=booking_id,
        guest_name=guest_name, check_in_date=check_in_date, check_out_date=check_out_date,
        nights_label=nights_label, detail_url=detail_url,
    )

    is_check_in = event_type == "check_in"
    action_past = "check-in" if is_check_in else "check-out"
    notification_type = "staff_check_in" if is_check_in else "staff_check_out"

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            html = html_template.replace("{{STAFF_NAME}}", name)
            ok = send_email(email, f"Huesped completo {action_past} — {booking_id}", html)
            if ok:
                logger.info("Staff check-event notification sent to %s (%s) for booking %s", name, email, booking_id)
                status = "sent"
            else:
                logger.warning("Failed to send staff check-event notification to %s for %s", email, booking_id)
                status = "failed"
                error_msg = "send_email returned False"
        except Exception as exc:
            logger.exception("Error sending staff check-event notification to %s for %s", email, booking_id)
            error_msg = str(exc)
        _log_notification(
            notification_type=notification_type, recipient_email=email,
            recipient_name=name, booking_id=booking_id, prop_id=prop_id,
            status=status, error_message=error_msg,
        )
