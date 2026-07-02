"""Guest notification functions for booking status changes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.database.connection import get_database
from src.app.email.service import send_email
from src.app.email.templates import status_badge
from ..email_templates import guest_invoice_html, guest_status_change_html

logger = logging.getLogger(__name__)


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
    if not guest_email:
        logger.warning("No guest email for booking %s — skipping notification", booking_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/reservations/{booking_id}"

    if new_status == "confirmed":
        subject = f"Reserva confirmada — {booking_id}"
        badge_html = status_badge("CONFIRMADA", bg_color="#dcfce7", text_color="#166534")
        headline = "Tu reserva ha sido confirmada"
        body_intro = 'Tu solicitud de reserva ha sido <strong>confirmada</strong> por el hotel. Prepara tus maletas.'
    elif new_status == "rejected":
        subject = f"Reserva rechazada — {booking_id}"
        badge_html = status_badge("RECHAZADA", bg_color="#fee2e2", text_color="#991b1b")
        headline = "Tu reserva no pudo ser confirmada"
        body_intro = 'Tu solicitud de reserva ha sido <strong>rechazada</strong> por el hotel.'
        if reason and reason not in ("rejected_by_staff", ""):
            body_intro += f" Motivo: {reason}."
        body_intro += " Te invitamos a buscar otras opciones disponibles."
    elif new_status == "cancelled":
        subject = f"Reserva cancelada — {booking_id}"
        badge_html = status_badge("CANCELADA", bg_color="#f3f4f6", text_color="#6b7280")
        headline = "Tu reserva ha sido cancelada"
        body_intro = 'Tu solicitud de reserva ha sido <strong>cancelada</strong>.'
        if reason and reason not in ("cancelled_by_user", ""):
            body_intro += f" Motivo: {reason}."
        body_intro += " Si necesitas ayuda, contacta al hotel directamente."
    elif new_status == "modified":
        subject = f"Reserva modificada — {booking_id}"
        badge_html = status_badge("MODIFICADA", bg_color="#fef3c7", text_color="#92400e")
        headline = "Tu reserva ha sido modificada"
        body_intro = 'Tu reserva ha sido <strong>modificada</strong> exitosamente. Por favor revisa los nuevos detalles.'
    elif new_status == "checked_in":
        subject = f"Check-in confirmado — {booking_id}"
        badge_html = status_badge("CHECK-IN", bg_color="#dbeafe", text_color="#1e40af")
        headline = "Tu check-in ha sido confirmado"
        body_intro = 'Tu <strong>check-in</strong> ha sido registrado exitosamente. Esperamos que disfrutes tu estancia.'
    elif new_status == "checked_out":
        subject = f"Check-out confirmado — {booking_id}"
        badge_html = status_badge("CHECK-OUT", bg_color="#f0fdf4", text_color="#166534")
        headline = "Tu check-out ha sido completado"
        body_intro = 'Tu <strong>check-out</strong> ha sido procesado. Esperamos que hayas tenido una excelente estancia.'
    else:
        logger.warning("Unsupported status '%s' for guest notification — skipping", new_status)
        return

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

    price_line = f"<strong>{total_price:.2f} {currency}</strong>" if total_price is not None else "—"
    nights_label = f"{total_nights} {'noche' if total_nights == 1 else 'noches'}"

    html = guest_status_change_html(
        hotel_label=hotel_label, booking_id=booking_id, guest_name=guest_name,
        check_in_date=check_in_date, check_out_date=check_out_date,
        nights_label=nights_label, price_line=price_line,
        badge_html=badge_html, headline=headline, body_intro=body_intro, detail_url=detail_url,
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

    notification_type = f"guest_{new_status}" if new_status in ("confirmed", "rejected", "cancelled", "checked_in", "checked_out", "modified") else "guest_other"
    _log_notification(
        notification_type=notification_type, recipient_email=guest_email,
        recipient_name=guest_name, booking_id=booking_id, prop_id=prop_id,
        status=status, error_message=error_msg,
    )


def notify_guest_invoice(
    booking_id: str,
    guest_name: str,
    guest_email: str,
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    total_nights: int,
    invoice_id: str,
    invoice_number: str,
    invoice_total: float,
    currency: str = "USD",
) -> None:
    """Notify a guest about an invoice issued after check-out."""
    if not guest_email:
        logger.warning("No guest email for booking %s — skipping invoice notification", booking_id)
        return

    settings = get_settings()
    invoice_url = f"{settings.app_base_url}/account/billing/invoices/{invoice_id}"

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

    nights_label = f"{total_nights} {'noche' if total_nights == 1 else 'noches'}"
    invoice_total_str = f"${invoice_total:.2f} {currency}"

    html = guest_invoice_html(
        hotel_label=hotel_label,
        booking_id=booking_id,
        guest_name=guest_name,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        nights_label=nights_label,
        invoice_number=invoice_number,
        invoice_total=invoice_total_str,
        invoice_url=invoice_url,
    )

    status = "error"
    error_msg = ""
    subject = f"Tu factura {invoice_number} ya esta disponible"
    try:
        ok = send_email(guest_email, subject, html)
        if ok:
            logger.info("Invoice notification sent to %s for booking %s", guest_email, booking_id)
            status = "sent"
        else:
            logger.warning("Failed to send invoice notification to %s for booking %s", guest_email, booking_id)
            status = "failed"
            error_msg = "send_email returned False"
    except Exception as exc:
        logger.exception("Error sending invoice notification to %s for booking %s", guest_email, booking_id)
        error_msg = str(exc)

    _log_notification(
        notification_type="guest_invoice_issued",
        recipient_email=guest_email,
        recipient_name=guest_name,
        booking_id=booking_id,
        prop_id=prop_id,
        status=status,
        error_message=error_msg,
    )
