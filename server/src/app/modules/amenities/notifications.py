"""Notification services for the amenities module.

Notifies hotel staff when a guest requests amenities during their stay.

Follows the same pattern as ``src.app.modules.reviews.service.notifications``
and ``src.app.modules.reservations.notifications.staff``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.email.templates import base_layout, detail_row, detail_table, cta_button
from src.app.security.role_helpers import build_role_query, get_role_name
from src.database.connection import get_database

logger = logging.getLogger(__name__)

STAFF_ROLES = ("hotel_partner", "gerente_hotel")
ADMIN_ROLES = ("super_admin", "admin_sistema")


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


def _get_staff_recipients(prop_id: int) -> list[tuple[str, str]]:
    """Find active staff users assigned to *prop_id*.

    Returns list of (email, display_name) tuples.
    """
    db = get_database()
    candidates = list(
        db.users.find(
            {**build_role_query(list(STAFF_ROLES + ADMIN_ROLES)), "is_active": True},
            {"_id": 0, "username": 1, "display_name": 1, "email": 1, "primary_role_id": 1, "assigned_hotels": 1},
        )
    )

    recipients: list[tuple[str, str]] = []
    for user in candidates:
        role = get_role_name(user)
        email = user.get("email", "").strip()
        if not email:
            continue
        if role in ADMIN_ROLES:
            recipients.append((email, user.get("display_name") or user.get("username", "Admin")))
            continue
        assigned = user.get("assigned_hotels", [])
        if isinstance(assigned, list) and assigned:
            try:
                int_ids = [int(p) for p in assigned if p is not None]
                if prop_id in int_ids:
                    recipients.append((email, user.get("display_name") or user.get("username", "Staff")))
            except (ValueError, TypeError):
                continue
    return recipients


def notify_staff_amenity_request(
    *,
    prop_id: int,
    booking_id: str,
    guest_name: str,
    items: list[dict[str, Any]],
    total: float,
) -> None:
    """Notify hotel staff when a guest requests amenities during their stay."""
    recipients = _get_staff_recipients(prop_id)
    if not recipients:
        logger.info(
            "No staff recipients for amenity-request notification prop_id=%s booking=%s",
            prop_id, booking_id,
        )
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/management/recepcion/{booking_id}"

    db = get_database()
    hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "display_name": 1, "hotel_name": 1},
    )
    hotel_label = (
        (hotel or {}).get("display_name")
        or (hotel or {}).get("hotel_name")
        or f"Propiedad #{prop_id}"
    )

    # Build items table rows
    items_rows = ""
    for item in items:
        label = item.get("label", "")
        qty = item.get("quantity", 1)
        amount = item.get("amount", 0)
        free = item.get("free", False)
        if free:
            items_rows += detail_row(label, f"x{qty} — Gratis")
        else:
            items_rows += detail_row(label, f"x{qty} — ${amount:.2f}")

    body = (
        f'<p style="margin:0 0 20px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{{{{STAFF_NAME}}}}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  El huesped <strong>{guest_name}</strong> ha solicitado servicios adicionales '
        f'para su estancia en <strong>{hotel_label}</strong>.\n'
        f'</p>\n'
        f'{detail_table("Articulos solicitados", items_rows)}\n'
        f'<p style="margin:0 0 16px;font-size:14px;color:#191c1e">\n'
        f'  <strong>Total cargos:</strong> ${total:.2f}\n'
        f'</p>\n'
        f'{cta_button(detail_url, "Ver reserva")}'
    )

    html = base_layout(
        "Solicitud de servicios",
        body,
        logo_url=settings.app_base_url,
        footer_note="El staff del hotel recibira esta notificacion para preparar los articulos solicitados.",
    )

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            final_html = html.replace("{{STAFF_NAME}}", name)
            total_items = len(items)
            ok = send_email(
                email,
                f"Solicitud de servicios — {guest_name} ({total_items} articulo{'s' if total_items != 1 else ''})",
                final_html,
            )
            if ok:
                logger.info(
                    "Amenity-request notification sent to %s (%s) for booking %s",
                    name, email, booking_id,
                )
                status = "sent"
            else:
                logger.warning(
                    "Failed to send amenity-request notification to %s for %s",
                    email, booking_id,
                )
                status = "failed"
                error_msg = "send_email returned False"
        except Exception as exc:
            logger.exception(
                "Error sending amenity-request notification to %s for %s",
                email, booking_id,
            )
            error_msg = str(exc)
        _log_notification(
            notification_type="staff_amenity_request",
            recipient_email=email,
            recipient_name=name,
            booking_id=booking_id,
            prop_id=prop_id,
            status=status,
            error_message=error_msg,
        )


def notify_guest_amenity_request(
    *,
    guest_email: str,
    guest_name: str,
    booking_id: str,
    prop_id: int,
    items: list[dict[str, Any]],
    total: float,
    hotel_label: str = "Hotel",
) -> None:
    """Notify the guest that their amenity request was processed successfully."""
    if not guest_email:
        logger.warning("No guest email for booking %s — skipping amenity confirmation", booking_id)
        return

    settings = get_settings()

    total_items = len(items)

    # Build items table rows
    items_rows = ""
    for item in items:
        label = item.get("label", "")
        qty = item.get("quantity", 1)
        amount = item.get("amount", 0)
        free = item.get("free", False)
        if free:
            items_rows += detail_row(label, f"x{qty} — Gratis")
        else:
            items_rows += detail_row(label, f"x{qty} — ${amount:.2f}")

    charges_summary = ""
    if total > 0:
        charges_summary = (
            f'<p style="margin:16px 0 0;font-size:13px;color:#6f797d">'
            f'<strong>Total cargos:</strong> ${total:.2f} — los cargos se liquidaran al momento del check-out.'
            f'</p>'
        )

    body = (
        f'<p style="margin:0 0 20px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{guest_name}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Hemos recibido tu solicitud de servicios adicionales para tu estancia en '
        f'<strong>{hotel_label}</strong>. El staff del hotel preparara los articulos solicitados.\n'
        f'</p>\n'
        f'{detail_table("Articulos solicitados", items_rows)}\n'
        f'{charges_summary}\n'
        f'<p style="margin:16px 0 0;font-size:13px;color:#9ca3af;line-height:1.5">'
        f'Si tienes alguna pregunta, contacta directamente con la recepcion del hotel.'
        f'</p>'
    )

    html = base_layout(
        "Solicitud de servicios confirmada",
        body,
        logo_url=settings.app_base_url,
    )
    subject = f"Solicitud de servicios — {hotel_label} ({total_items} articulo{'s' if total_items != 1 else ''})"

    status = "error"
    error_msg = ""
    try:
        ok = send_email(guest_email, subject, html)
        if ok:
            logger.info(
                "Guest amenity-request confirmation sent to %s for booking %s",
                guest_email, booking_id,
            )
            status = "sent"
        else:
            logger.warning(
                "Failed to send guest amenity-request confirmation to %s for %s",
                guest_email, booking_id,
            )
            status = "failed"
            error_msg = "send_email returned False"
    except Exception as exc:
        logger.exception(
            "Error sending guest amenity-request confirmation to %s for %s",
            guest_email, booking_id,
        )
        error_msg = str(exc)

    _log_notification(
        notification_type="guest_amenity_request",
        recipient_email=guest_email,
        recipient_name=guest_name,
        booking_id=booking_id,
        prop_id=prop_id,
        status=status,
        error_message=error_msg,
    )
