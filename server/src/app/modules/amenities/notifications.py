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
        {"_id": 0, "display_name": 1, "display_label": 1, "hotel_name": 1},
    )
    hotel_label = (
        (hotel or {}).get("display_label")
        or (hotel or {}).get("display_name")
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
            items_rows += (
                f'<tr><td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
                f'{label}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">x{qty}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px;color:#16a34a">Gratis</td></tr>'
            )
        else:
            items_rows += (
                f'<tr><td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
                f'{label}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">x{qty}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
                f'<strong>${amount:.2f}</strong></td></tr>'
            )

    body = (
        f'<p style="margin:0 0 20px;font-size:15px;color:#374151">Hola <strong>{{STAFF_NAME}}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">\n'
        f'  El huésped <strong>{guest_name}</strong> ha solicitado servicios adicionales '
        f'para su estancia en <strong>{hotel_label}</strong>.\n'
        f'</p>\n'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;'
        f'border-radius:12px;overflow:hidden;margin-bottom:20px">\n'
        f'  <tr><td style="background:#f9fafb;padding:10px 14px;font-size:13px;font-weight:600;'
        f'color:#374151;border-bottom:1px solid #e5e7eb" colspan="3">📋 Artículos solicitados</td></tr>\n'
        f'  <tr>\n'
        f'    <td style="padding:6px 12px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Artículo</td>\n'
        f'    <td style="padding:6px 12px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Cant.</td>\n'
        f'    <td style="padding:6px 12px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Total</td>\n'
        f'  </tr>\n'
        f'{items_rows}'
        f'</table>\n'
        f'<table width="100%" cellpadding="0" cellspacing="0">\n'
        f'  <tr><td style="padding:8px 0;font-size:14px;color:#4b5563">\n'
        f'    <strong>Total cargos:</strong> ${total:.2f}\n'
        f'  </td></tr>\n'
        f'  <tr>\n'
        f'    <td align="center" style="padding-top:16px">\n'
        f'      <a href="{detail_url}" '
        f'style="display:inline-block;padding:12px 28px;background:#1463ff;color:#fff;'
        f'text-decoration:none;border-radius:10px;font-size:15px;font-weight:600">\n'
        f'        Ver reserva →\n'
        f'      </a>\n'
        f'    </td>\n'
        f'  </tr>\n'
        f'</table>'
    )

    html = _base_layout("🛎️ Solicitud de amenities", body)

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            final_html = html.replace("{{STAFF_NAME}}", name)
            total_items = len(items)
            ok = send_email(
                email,
                f"🛎️ Solicitud de amenities — {guest_name} ({total_items} artículo{'s' if total_items != 1 else ''})",
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
    paid_items = [i for i in items if not i.get("free")]
    free_items = [i for i in items if i.get("free")]

    # Build items table rows
    items_rows = ""
    for item in items:
        label = item.get("label", "")
        qty = item.get("quantity", 1)
        amount = item.get("amount", 0)
        free = item.get("free", False)
        if free:
            items_rows += (
                f'<tr><td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
                f'{label}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">x{qty}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px;color:#16a34a;font-weight:600">Gratis</td></tr>'
            )
        else:
            items_rows += (
                f'<tr><td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
                f'{label}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">x{qty}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
                f'<strong>${amount:.2f}</strong></td></tr>'
            )

    charges_summary = ""
    if paid_items:
        charges_summary = (
            f'<p style="margin:16px 0 0;font-size:14px;color:#4b5563">'
            f'<strong>Total cargos:</strong> ${total:.2f} — los cargos se liquidarán al momento del check-out.'
            f'</p>'
        )
    if free_items:
        charges_summary += (
            f'<p style="margin:6px 0 0;font-size:13px;color:#16a34a">'
            f'🌟 {len(free_items)} artículo(s) gratuito(s) incluido(s) en tu solicitud.'
            f'</p>'
        )

    body = (
        f'<p style="margin:0 0 20px;font-size:15px;color:#374151">Hola <strong>{guest_name}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">\n'
        f'  Hemos recibido tu solicitud de servicios adicionales para tu estancia en '
        f'<strong>{hotel_label}</strong>. El staff del hotel preparará los artículos solicitados.\n'
        f'</p>\n'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;'
        f'border-radius:12px;overflow:hidden;margin-bottom:20px">\n'
        f'  <tr><td style="background:#f9fafb;padding:10px 14px;font-size:13px;font-weight:600;'
        f'color:#374151;border-bottom:1px solid #e5e7eb" colspan="3">📋 Artículos solicitados</td></tr>\n'
        f'  <tr>\n'
        f'    <td style="padding:6px 12px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Artículo</td>\n'
        f'    <td style="padding:6px 12px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Cant.</td>\n'
        f'    <td style="padding:6px 12px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Importe</td>\n'
        f'  </tr>\n'
        f'{items_rows}'
        f'</table>\n'
        f'{charges_summary}'
        f'<p style="margin:16px 0 0;font-size:13px;color:#9ca3af;line-height:1.5">'
        f'Si tienes alguna pregunta, contacta directamente con la recepción del hotel.'
        f'</p>'
    )

    html = _base_layout("🛎️ Solicitud de servicios confirmada", body)
    subject = f"🛎️ Solicitud de servicios — {hotel_label} ({total_items} artículo{'s' if total_items != 1 else ''})"

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


def _base_layout(headline: str, body_content: str) -> str:
    """Return a complete email HTML wrapped in the HotelData branded layout."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
  <table align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:32px auto">
    <tr>
      <td style="background:linear-gradient(135deg,#1463ff,#0a3d9e);border-radius:16px 16px 0 0;padding:24px 32px;text-align:center">
        <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700">🏨 HotelData</h1>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);font-size:14px">{headline}</p>
      </td>
    </tr>
    <tr>
      <td style="background:#fff;padding:32px;border-radius:0 0 16px 16px;box-shadow:0 4px 12px rgba(0,0,0,0.06)">
        {body_content}
        <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;text-align:center;line-height:1.4">
          Este es un mensaje automático de HotelData Hub.<br>
          El staff del hotel recibirá esta notificación para preparar los artículos solicitados.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""
