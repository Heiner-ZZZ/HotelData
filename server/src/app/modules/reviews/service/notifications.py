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

from bson import ObjectId

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.email.templates import base_layout, detail_row, detail_table, cta_button, status_badge
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


def _sentiment_html(rating: int) -> str:
    """Generate a sentiment label based on rating (no emoji)."""
    if rating >= 4:
        return status_badge("Positivo", bg_color="#dcfce7", text_color="#166534")
    if rating == 3:
        return status_badge("Neutral", bg_color="#fef9e7", text_color="#b8860b")
    return status_badge("Negativo", bg_color="#fee2e2", text_color="#991b1b")


def _stars_display(rating: int) -> str:
    """Simple text-based star rating (no emoji)."""
    filled = "★" * rating
    empty = "☆" * (5 - rating)
    return f'{filled}{empty} <strong>{rating}/5</strong>'


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
        f'<div style="margin:8px 0 0;padding:8px 12px;background:#f7f9fb;'
        f'border-left:2px solid #006076;font-size:13px;color:#6f797d;line-height:1.5">'
        f'{comment}</div>'
    ) if comment else ""

    body = (
        f'<p style="margin:0 0 20px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{{STAFF_NAME}}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Se ha recibido una <strong>nueva resena</strong> de un huesped '
        f'para <strong>{hotel_label}</strong>.\n'
        f'  La resena esta <strong>pendiente de moderacion</strong> y necesita revision.\n'
        f'</p>\n'
        f'{detail_table("Detalles de la resena", "")}'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e3e5;margin-bottom:20px">\n'
        f'{detail_row("Huesped", f"<strong>{guest_name}</strong>")}'
        f'{detail_row("Puntuacion", _stars_display(rating))}'
        f'{detail_row("Sentimiento", _sentiment_html(rating))}'
        f'{detail_row("Titulo", f"<strong>{title or '(sin titulo)'}</strong>")}'
        f'{detail_row("Estado", status_badge("PENDIENTE", bg_color="#fef3c7", text_color="#92400e"))}'
        f'</table>\n'
        f'{comment_section}\n'
        f'{cta_button(detail_url, "Revisar resena")}'
    )

    html = base_layout("Nueva resena de huesped", body, logo_url=settings.app_base_url)

    for email, name in recipients:
        status = "error"
        error_msg = ""
        try:
            final_html = html.replace("{{STAFF_NAME}}", name)
            ok = send_email(email, f"Nueva resena pendiente — {hotel_label}", final_html)
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
        subject = "Tu resena ha sido publicada"
        headline = "Tu resena ha sido publicada"
        body_intro = (
            f"Hola <strong>{guest_name}</strong>,<br><br>"
            "Gracias por compartir tu experiencia. Tu resena ha sido <strong>aprobada</strong> "
            "y ya es visible en el perfil del hotel."
        )
    elif status == "rejected":
        subject = "Tu resena no ha sido publicada"
        headline = "Tu resena no ha sido publicada"
        body_intro = (
            f"Hola <strong>{guest_name}</strong>,<br><br>"
            "Lamentablemente, tu resena no ha sido <strong>aprobada</strong> "
            "porque no cumple con las politicas de contenido del hotel. "
            "Si consideras que esto es un error, contacta al hotel directamente."
        )
    else:
        logger.warning("Unsupported moderation status '%s' — skipping guest notification", status)
        return

    body = (
        f'<p style="margin:0 0 20px;font-size:14px;color:#3f484c">{body_intro}</p>\n'
        f'{cta_button(detail_url, "Ver mis reservas")}'
    )

    html = base_layout(headline, body, logo_url=settings.app_base_url)
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
