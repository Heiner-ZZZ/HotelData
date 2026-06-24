"""Notification services for the reviews module.

Sends email alerts when:
- A new review is created → notify hotel staff assigned to that property
- A review is moderated (approved/rejected) → notify the guest

Follows the same pattern as ``src.app.modules.reservations.notifications``
using ``send_email`` from ``src.app.email.service`` and logging to ``notification_log``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

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
    review_id: str,
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
                "booking_id": review_id,  # reuse booking_id field for review_id
                "prop_id": prop_id,
                "status": status,
                "error_message": error_message,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception:
        logger.exception("Failed to write notification_log for %s (%s)", notification_type, review_id)


def _get_staff_recipients(prop_id: int) -> list[tuple[str, str]]:
    """Find active staff users (hotel_partner, gerente_hotel, super_admin) assigned to *prop_id*.

    Returns list of (email, display_name) tuples.
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
        assigned = user.get("assigned_hotels", [])
        if isinstance(assigned, list) and assigned:
            try:
                int_ids = [int(p) for p in assigned if p is not None]
                if prop_id in int_ids:
                    recipients.append((email, user.get("display_name") or user.get("username", "Staff")))
            except (ValueError, TypeError):
                continue
    return recipients


def notify_review_created(
    *,
    prop_id: int,
    review_id: str,
    rating: int,
    title: str,
    comment: str,
    guest_name: str,
) -> None:
    """Notify staff when a new review is created (pending moderation)."""
    recipients = _get_staff_recipients(prop_id)
    if not recipients:
        logger.info("No staff recipients for review notification prop_id=%s review=%s", prop_id, review_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/management/reviews/{review_id}"

    # Look up hotel name
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

    comment_section = (
        f'<p style="margin:8px 0 0;padding:8px 12px;background:#f9fafb;'
        f'border-left:3px solid #1463ff;border-radius:4px;font-size:13px;color:#4b5563;line-height:1.5">'
        f'{comment}</p>'
    ) if comment else ""

    stars_display = "⭐" * rating + "☆" * (5 - rating)
    sentiment_badge = _sentiment_html(rating)

    body = (
        f'<p style="margin:0 0 20px;font-size:15px;color:#374151">Hola <strong>{{STAFF_NAME}}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">\n'
        f'  Se ha recibido una <strong style="color:#1463ff">nueva reseña</strong> de un huésped '
        f'para <strong>{hotel_label}</strong>.\n'
        f'  La reseña está <strong>pendiente de moderación</strong> y necesita revisión.\n'
        f'</p>\n'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;'
        f'border-radius:12px;overflow:hidden;margin-bottom:20px">\n'
        f'  <tr><td style="background:#f9fafb;padding:10px 14px;font-size:13px;font-weight:600;'
        f'color:#374151;border-bottom:1px solid #e5e7eb" colspan="2">📋 Detalles de la reseña</td></tr>\n'
        f'  <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;'
        f'vertical-align:top;white-space:nowrap">Huésped</td>\n'
        f'    <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
        f'<strong>{guest_name}</strong></td></tr>\n'
        f'  <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;'
        f'vertical-align:top;white-space:nowrap">Puntuación</td>\n'
        f'    <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
        f'{stars_display} <strong>{rating}/5</strong></td></tr>\n'
        f'  <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;'
        f'vertical-align:top;white-space:nowrap">Sentimiento</td>\n'
        f'    <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
        f'{sentiment_badge}</td></tr>\n'
        f'  <tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;'
        f'vertical-align:top;white-space:nowrap">Título</td>\n'
        f'    <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">'
        f'<strong>{title or "(sin título)"}</strong></td></tr>\n'
        f'  <tr><td style="padding:8px 12px;color:#4b5563;font-size:14px;vertical-align:top;'
        f'white-space:nowrap">Estado</td>\n'
        f'    <td style="padding:8px 12px;font-size:14px">'
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'background:#fef3c7;color:#92400e;font-size:12px;font-weight:600">⏳ PENDIENTE</span>'
        f'</td></tr>\n'
        f'</table>\n'
        f'{comment_section}\n'
        f'<table width="100%" cellpadding="0" cellspacing="0">\n'
        f'  <tr>\n'
        f'    <td align="center">\n'
        f'      <a href="{detail_url}" '
        f'style="display:inline-block;padding:12px 28px;background:#1463ff;color:#fff;'
        f'text-decoration:none;border-radius:10px;font-size:15px;font-weight:600">\n'
        f'        Revisar reseña →\n'
        f'      </a>\n'
        f'    </td>\n'
        f'  </tr>\n'
        f'</table>'
    )

    html = _base_layout("📝 Nueva reseña de huésped", body)

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            final_html = html.replace("{{STAFF_NAME}}", name)
            ok = send_email(email, f"📝 Nueva reseña pendiente — {hotel_label}", final_html)
            if ok:
                logger.info("Review notification sent to %s (%s) for review %s", name, email, review_id)
                status = "sent"
            else:
                logger.warning("Failed to send review notification to %s for %s", email, review_id)
                status = "failed"
                error_msg = "send_email returned False"
        except Exception as exc:
            logger.exception("Error sending review notification to %s for %s", email, review_id)
            error_msg = str(exc)
        _log_notification(
            notification_type="staff_new_review",
            recipient_email=email,
            recipient_name=name,
            review_id=review_id,
            prop_id=prop_id,
            status=status,
            error_message=error_msg,
        )


def notify_review_moderated(
    *,
    review_id: str,
    status: str,
    prop_id: int,
    guest_name: str,
) -> None:
    """Notify the guest when their review is moderated (approved or rejected)."""
    # Find the guest's email from the review document
    db = get_database()
    try:
        review = db.reviews.find_one({"_id": ObjectId(review_id)}, {"user_id": 1})
    except Exception:
        review = None

    if not review:
        logger.warning("Review %s not found for moderation notification", review_id)
        return

    user_id = review.get("user_id")
    if not user_id:
        logger.warning("Review %s has no user_id — skipping guest notification", review_id)
        return

    user = db.users.find_one({"_id": user_id}, {"email": 1, "display_name": 1, "username": 1})
    if not user:
        logger.warning("User %s not found for review %s — skipping guest notification", user_id, review_id)
        return

    guest_email = user.get("email", "").strip()
    if not guest_email:
        logger.warning("User %s has no email — skipping guest notification for review %s", user_id, review_id)
        return

    settings = get_settings()
    detail_url = f"{settings.app_base_url}/reservations"

    if status == "approved":
        subject = "✅ Tu reseña ha sido publicada"
        headline = "¡Tu reseña ha sido publicada!"
        body_intro = (
            f"Hola <strong>{guest_name}</strong>,<br><br>"
            "¡Gracias por compartir tu experiencia! Tu reseña ha sido <strong>aprobada</strong> "
            "y ya es visible en el perfil del hotel."
        )
    elif status == "rejected":
        subject = "ℹ️ Tu reseña no ha sido publicada"
        headline = "Tu reseña no ha sido publicada"
        body_intro = (
            f"Hola <strong>{guest_name}</strong>,<br><br>"
            "Lamentablemente, tu reseña no ha sido <strong>aprobada</strong> "
            "porque no cumple con las políticas de contenido del hotel. "
            "Si consideras que esto es un error, contacta al hotel directamente."
        )
    else:
        logger.warning("Unsupported moderation status '%s' — skipping guest notification", status)
        return

    body = (
        f'<p style="margin:0 0 20px;font-size:15px;color:#374151">{body_intro}</p>\n'
        f'<table width="100%" cellpadding="0" cellspacing="0">\n'
        f'  <tr>\n'
        f'    <td align="center">\n'
        f'      <a href="{detail_url}" '
        f'style="display:inline-block;padding:12px 28px;background:#1463ff;color:#fff;'
        f'text-decoration:none;border-radius:10px;font-size:15px;font-weight:600">\n'
        f'        Ver mis reservas →\n'
        f'      </a>\n'
        f'    </td>\n'
        f'  </tr>\n'
        f'</table>'
    )

    html = _base_layout(headline, body)
    notif_status = "error"
    error_msg = ""
    try:
        ok = send_email(guest_email, subject, html)
        if ok:
            logger.info("Moderation notification sent to %s for review %s (status=%s)", guest_email, review_id, status)
            notif_status = "sent"
        else:
            logger.warning("Failed to send moderation notification to %s for review %s", guest_email, review_id)
            notif_status = "failed"
            error_msg = "send_email returned False"
    except Exception as exc:
        logger.exception("Error sending moderation notification to %s for review %s", guest_email, review_id)
        error_msg = str(exc)

    notification_type = f"guest_review_{status}"
    _log_notification(
        notification_type=notification_type,
        recipient_email=guest_email,
        recipient_name=guest_name,
        review_id=review_id,
        prop_id=prop_id,
        status=notif_status,
        error_message=error_msg,
    )


def _sentiment_html(rating: int) -> str:
    """Generate a sentiment badge HTML based on rating."""
    if rating >= 4:
        return '<span style="display:inline-block;padding:2px 10px;border-radius:12px;background:#dcfce7;color:#166534;font-size:12px;font-weight:600">😊 Positivo</span>'
    if rating == 3:
        return '<span style="display:inline-block;padding:2px 10px;border-radius:12px;background:#fef9e7;color:#b8860b;font-size:12px;font-weight:600">😐 Neutral</span>'
    return '<span style="display:inline-block;padding:2px 10px;border-radius:12px;background:#fee2e2;color:#991b1b;font-size:12px;font-weight:600">😞 Negativo</span>'


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
          Si tienes dudas, contacta al hotel directamente.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""
