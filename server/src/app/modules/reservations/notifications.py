"""Notification services for reservation lifecycle.

Sends email alerts to hotel staff when a new booking is created
so they can review and confirm/reject it promptly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.app.email.service import send_email
from src.database.connection import get_database

from .email_templates import guest_status_change_html, staff_check_event_html, staff_new_booking_html

logger = logging.getLogger(__name__)

STAFF_ROLES = ("hotel_partner", "gerente_hotel")
ADMIN_ROLES = ("super_admin", "admin_sistema")


def _assigned_hotel_ids(user: dict[str, Any]) -> list[int]:
    """Extract assigned hotel IDs from a user document, normalized to ints."""
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
    """Insert an audit record into the notification_log collection."""
    try:
        db = get_database()
        db.notification_log.insert_one(
            {
                "notification_type": notification_type,
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "booking_id": booking_id,
                "prop_id": prop_id,
                "status": status,
                "error_message": error_message,
                "created_at": datetime.now(timezone.utc),
            }
        )
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
    """Find staff assigned to *prop_id* and send them an email about the new booking.

    Sends to:
    - hotel_partner / gerente_hotel users whose ``assigned_hotels`` includes prop_id
    - super_admin / admin_sistema (always notified when they have the hotel in their list or no restriction)
    """
    db = get_database()

    # Fetch candidate users
    candidates = list(
        db.users.find(
            {
                "primary_role": {"$in": STAFF_ROLES + ADMIN_ROLES},
                "is_active": True,
            },
            {"_id": 0, "username": 1, "display_name": 1, "email": 1, "primary_role": 1, "assigned_hotels": 1},
        )
    )

    recipients: list[tuple[str, str]] = []
    for user in candidates:
        role = user.get("primary_role", "")
        email = user.get("email", "").strip()
        if not email:
            continue

        # Admins always get notified (they manage everything)
        if role in ADMIN_ROLES:
            recipients.append((email, user.get("display_name") or user.get("username", "Admin")))
            continue

        # Staff: must have the hotel in their assigned list
        assigned = _assigned_hotel_ids(user)
        if prop_id in assigned:
            recipients.append((email, user.get("display_name") or user.get("username", "Staff")))

    if not recipients:
        logger.info("No staff recipients found for prop_id=%s booking=%s", prop_id, booking_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/management/recepcion/{booking_id}"

    # Look up hotel display name
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

    price_line = (
        f"<strong>{total_price:.2f} {currency}</strong>" if total_price is not None else "Pendiente de cálculo"
    )
    nights_label = f"{total_nights} {'noche' if total_nights == 1 else 'noches'}"
    guests_label = f"{adults} adulto{'s' if adults != 1 else ''}"
    if children > 0:
        guests_label += f", {children} niño{'s' if children != 1 else ''}"
    guests_label += f" · {rooms} habitaci{'ón' if rooms == 1 else 'ones'}"
    comment_section = (
        f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;vertical-align:top;white-space:nowrap">Comentario</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">{comment}</td>
        </tr>"""
        if comment
        else ""
    )

    html_template = staff_new_booking_html(
        hotel_label=hotel_label,
        booking_id=booking_id,
        guest_name=guest_name,
        guest_email=guest_email,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        nights_label=nights_label,
        guests_label=guests_label,
        price_line=price_line,
        comment_section=comment_section,
        detail_url=detail_url,
    )

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            html = html_template.replace("{{STAFF_NAME}}", name)
            ok = send_email(email, f"🔔 Nueva reserva pendiente — {booking_id}", html)
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
            notification_type="staff_new_booking",
            recipient_email=email,
            recipient_name=name,
            booking_id=booking_id,
            prop_id=prop_id,
            status=status,
            error_message=error_msg,
        )


def notify_staff_check_event(
    event_type: str,  # "check_in" or "check_out"
    prop_id: int,
    booking_id: str,
    guest_name: str,
    check_in_date: str,
    check_out_date: str,
    total_nights: int,
) -> None:
    """Notify staff when a guest completes check-in or check-out.

    Uses the same staff-lookup logic as ``notify_staff_new_booking``:
    - hotel_partner / gerente_hotel with the hotel in their assigned list
    - super_admin / admin_sistema (always)
    """
    db = get_database()

    candidates = list(
        db.users.find(
            {
                "primary_role": {"$in": STAFF_ROLES + ADMIN_ROLES},
                "is_active": True,
            },
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
        event_type=event_type,
        hotel_label=hotel_label,
        booking_id=booking_id,
        guest_name=guest_name,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        nights_label=nights_label,
        detail_url=detail_url,
    )

    is_check_in = event_type == "check_in"
    subject_prefix = "🔑" if is_check_in else "👋"
    action_past = "check-in" if is_check_in else "check-out"
    notification_type = "staff_check_in" if is_check_in else "staff_check_out"

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            html = html_template.replace("{{STAFF_NAME}}", name)
            ok = send_email(email, f"{subject_prefix} Huésped completó {action_past} — {booking_id}", html)
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
            notification_type=notification_type,
            recipient_email=email,
            recipient_name=name,
            booking_id=booking_id,
            prop_id=prop_id,
            status=status,
            error_message=error_msg,
        )


def notify_guest_status_change(
    booking_id: str,
    guest_name: str,
    guest_email: str,
    new_status: str,
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    total_price: float | None,
    currency: str,
    total_nights: int,
    reason: str = "",
) -> None:
    """Send an email to the guest when their reservation is confirmed or rejected."""
    if not guest_email:
        logger.warning("No guest email for booking %s — skipping notification", booking_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/reservations/{booking_id}"

    if new_status == "confirmed":
        subject = f"✅ Reserva confirmada — {booking_id}"
        badge_html = "<span style=\"display:inline-block;padding:4px 14px;border-radius:12px;background:#dcfce7;color:#166534;font-size:13px;font-weight:700\">✅ CONFIRMADA</span>"
        headline = "¡Tu reserva ha sido confirmada!"
        body_intro = "Tu solicitud de reserva ha sido <strong>confirmada</strong> por el hotel. ¡Prepara tus maletas!"
    elif new_status == "rejected":
        subject = f"❌ Reserva rechazada — {booking_id}"
        badge_html = "<span style=\"display:inline-block;padding:4px 14px;border-radius:12px;background:#fee2e2;color:#991b1b;font-size:13px;font-weight:700\">❌ RECHAZADA</span>"
        headline = "Tu reserva no pudo ser confirmada"
        body_intro = "Lamentablemente, tu solicitud de reserva ha sido <strong>rechazada</strong> por el hotel."
        if reason and reason not in ("rejected_by_staff", ""):
            body_intro += f" Motivo: {reason}."
        body_intro += " Te invitamos a buscar otras opciones disponibles."
    elif new_status == "cancelled":
        subject = f"↩️ Reserva cancelada — {booking_id}"
        badge_html = "<span style=\"display:inline-block;padding:4px 14px;border-radius:12px;background:#f3f4f6;color:#6b7280;font-size:13px;font-weight:700\">↩️ CANCELADA</span>"
        headline = "Tu reserva ha sido cancelada"
        body_intro = "Tu solicitud de reserva ha sido <strong>cancelada</strong>."
        if reason and reason not in ("cancelled_by_user", ""):
            body_intro += f" Motivo: {reason}."
        body_intro += " Si necesitas ayuda, contacta al hotel directamente."
    elif new_status == "checked_in":
        subject = f"🔑 Check-in confirmado — {booking_id}"
        badge_html = "<span style=\"display:inline-block;padding:4px 14px;border-radius:12px;background:#dbeafe;color:#1e40af;font-size:13px;font-weight:700\">🔑 CHECK-IN</span>"
        headline = "¡Tu check-in ha sido confirmado!"
        body_intro = "Tu <strong>check-in</strong> ha sido registrado exitosamente. ¡Esperamos que disfrutes tu estancia!"
        detail_url = f"{settings.app_base_url}/reservations/{booking_id}"
    elif new_status == "checked_out":
        subject = f"👋 Check-out confirmado — {booking_id}"
        badge_html = "<span style=\"display:inline-block;padding:4px 14px;border-radius:12px;background:#f0fdf4;color:#166534;font-size:13px;font-weight:700\">👋 CHECK-OUT</span>"
        headline = "Tu check-out ha sido completado"
        body_intro = (
            "Tu <strong>check-out</strong> ha sido procesado. "
            "Esperamos que hayas tenido una excelente estancia.<br><br>"
            "Si deseas dejar una reseña sobre tu experiencia, "
            "puedes hacerlo desde el detalle de tu reserva."
        )
    else:
        logger.warning("Unsupported status '%s' for guest notification — skipping", new_status)
        return

    # Look up hotel label
    db = get_database()
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

    price_line = (
        f"<strong>{total_price:.2f} {currency}</strong>" if total_price is not None else "—"
    )
    nights_label = f"{total_nights} {'noche' if total_nights == 1 else 'noches'}"

    html = guest_status_change_html(
        hotel_label=hotel_label,
        booking_id=booking_id,
        guest_name=guest_name,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        nights_label=nights_label,
        price_line=price_line,
        badge_html=badge_html,
        headline=headline,
        body_intro=body_intro,
        detail_url=detail_url,
    )

    status = "error"
    error_msg = ""
    try:
        ok = send_email(guest_email, subject, html)
        if ok:
            logger.info("Guest notification sent to %s for booking %s (status=%s)", guest_email, booking_id, new_status)
            status = "sent"
        else:
            logger.warning("Failed to send guest notification to %s for booking %s", guest_email, booking_id)
            status = "failed"
            error_msg = "send_email returned False"
    except Exception as exc:
        logger.exception("Error sending guest notification to %s for booking %s", guest_email, booking_id)
        error_msg = str(exc)

    notification_type = f"guest_{new_status}" if new_status in ("confirmed", "rejected", "cancelled", "checked_in", "checked_out") else "guest_other"
    _log_notification(
        notification_type=notification_type,
        recipient_email=guest_email,
        recipient_name=guest_name,
        booking_id=booking_id,
        prop_id=prop_id,
        status=status,
        error_message=error_msg,
    )
