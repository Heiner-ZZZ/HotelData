"""Shared helpers for In-Stay endpoint implementations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException

logger = logging.getLogger(__name__)

from src.app.modules.instay.schemas import SERVICE_REQUEST_TYPES, SERVICE_REQUEST_STATUSES, utc_now
from src.app.security.session import ensure_utc
from src.database.connection import get_database

_TOKEN_BYTES = 32
_SESSION_DAYS = 31


def session_expiry() -> datetime:
    return utc_now() + timedelta(days=_SESSION_DAYS)


def serialize_session(doc: dict) -> dict:
    return {
        "token": doc.get("token", ""),
        "booking_id": doc.get("booking_id", ""),
        "prop_id": doc.get("prop_id", 0),
        "room_label": doc.get("room_label", ""),
        "guest_name": doc.get("guest_name", ""),
        "check_in": doc.get("check_in", ""),
        "check_out": doc.get("check_out", ""),
        "created_at": _iso(doc.get("created_at")),
        "expires_at": _iso(doc.get("expires_at")),
        "active": bool(doc.get("active", True)),
    }


def _iso(val) -> str:
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val or "")


def get_session_or_404(token: str) -> dict:
    """Validate a session token and return the session document."""
    db = get_database()
    session = db.stay_sessions.find_one({"token": token, "active": True})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada.")
    expires_at = ensure_utc(session.get("expires_at"))
    if expires_at and expires_at < utc_now():
        raise HTTPException(status_code=410, detail="Sesión expirada.")
    return session


def type_label(t: str) -> str:
    return SERVICE_REQUEST_TYPES.get(t, t.replace("_", " ").title())


def status_label(s: str) -> str:
    return SERVICE_REQUEST_STATUSES.get(s, s.capitalize())


def notify_staff_new_message(db, session: dict):
    """Log a notification for staff about a new guest message + push SSE event."""
    prop_id = session.get("prop_id", 0)
    room_label = session.get("room_label", "")
    guest_name = session.get("guest_name", "huésped")

    db.notification_log.insert_one({
        "recipient_email": "staff",
        "notification_type": "guest_chat_message",
        "subject": f"Nuevo mensaje de {guest_name} (Hab. {room_label})",
        "body": f"La habitación {room_label} envió un mensaje.",
        "status": "sent",
        "created_at": utc_now(),
        "metadata": {
            "prop_id": prop_id,
            "room_label": room_label,
            "booking_id": session.get("booking_id"),
        },
    })

    # Push SSE event
    try:
        from src.app.modules.instay.routes_impl._event_manager import StayEventManager
        StayEventManager.instance_sync().publish_threadsafe(prop_id, "new_message", {
            "room_label": room_label,
            "guest_name": guest_name,
        })
    except Exception:
        pass


def notify_staff_new_request(db, session: dict, request_type: str):
    """Log a notification for staff about a new service request + push SSE event."""
    type_label_str = type_label(request_type)
    prop_id = session.get("prop_id", 0)
    room_label = session.get("room_label", "")
    guest_name = session.get("guest_name", "")

    db.notification_log.insert_one({
        "recipient_email": "staff",
        "notification_type": "guest_service_request",
        "subject": f"Nueva solicitud: {type_label_str} (Hab. {room_label})",
        "body": f"El huésped {guest_name} solicitó: {type_label_str}",
        "status": "sent",
        "created_at": utc_now(),
        "metadata": {
            "prop_id": prop_id,
            "room_label": room_label,
            "booking_id": session.get("booking_id"),
            "request_type": request_type,
        },
    })

    # Push SSE event
    try:
        from src.app.modules.instay.routes_impl._event_manager import StayEventManager
        StayEventManager.instance_sync().publish_threadsafe(prop_id, "new_request", {
            "room_label": room_label,
            "guest_name": guest_name,
            "request_type": type_label_str,
        })
    except Exception:
        pass


def notify_staff_dnd_toggled(db, session: dict, dnd_active: bool):
    """Push SSE event when a guest toggles Do Not Disturb."""
    prop_id = session.get("prop_id", 0)
    room_label = session.get("room_label", "")
    guest_name = session.get("guest_name", "huésped")

    action = "activó" if dnd_active else "desactivó"
    try:
        db.notification_log.insert_one({
            "recipient_email": "staff",
            "notification_type": "dnd_toggled",
            "subject": f"{guest_name} (Hab. {room_label}) {action} No Molestar",
            "body": f"La habitación {room_label} {action} el modo No Molestar.",
            "status": "sent",
            "created_at": utc_now(),
            "metadata": {
                "prop_id": prop_id,
                "room_label": room_label,
                "booking_id": session.get("booking_id"),
                "dnd_active": dnd_active,
            },
        })
    except Exception:
        pass

    # Push SSE event
    try:
        from src.app.modules.instay.routes_impl._event_manager import StayEventManager
        StayEventManager.instance_sync().publish_threadsafe(prop_id, "dnd_toggled", {
            "room_label": room_label,
            "guest_name": guest_name,
            "dnd_active": dnd_active,
        })
    except Exception:
        pass


def notify_staff_request_updated(db, request_doc: dict, new_status: str):
    """Log a notification for staff when a service request status changes + push SSE event."""
    prop_id = request_doc.get("prop_id", 0)
    room_label = request_doc.get("room_label", "")
    request_type = request_doc.get("request_type_label", request_doc.get("request_type", ""))
    old_status = request_doc.get("status", "")
    new_status_label_str = status_label(new_status)

    db.notification_log.insert_one({
        "recipient_email": "staff",
        "notification_type": "request_status_changed",
        "subject": f"Solicitud actualizada: {request_type} → {new_status_label_str} (Hab. {room_label})",
        "body": f"La solicitud de {request_type} (Hab. {room_label}) cambió de '{old_status}' a '{new_status}'.",
        "status": "sent",
        "created_at": utc_now(),
        "metadata": {
            "prop_id": prop_id,
            "room_label": room_label,
            "request_id": str(request_doc.get("_id", "")),
            "request_type": request_type,
            "old_status": old_status,
            "new_status": new_status,
        },
    })

    # Push SSE event
    try:
        from src.app.modules.instay.routes_impl._event_manager import StayEventManager
        StayEventManager.instance_sync().publish_threadsafe(prop_id, "request_updated", {
            "request_id": str(request_doc.get("_id", "")),
            "room_label": room_label,
            "request_type": request_type,
            "old_status": old_status,
            "new_status": new_status,
            "status_label": new_status_label_str,
        })
    except Exception:
        pass


def notify_guest_new_message(db, session: dict):
    """Send an email to the guest when a staff member replies to their chat message."""
    booking_id = session.get("booking_id", "")
    if not booking_id:
        return

    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        return

    guest_email = booking.get("guest_email", "") or booking.get("email", "")
    guest_name = booking.get("guest_name", "Huésped")
    if not guest_email:
        return

    prop_id = session.get("prop_id", 0)
    room_label = session.get("room_label", "")

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

    subject = f"Nueva respuesta de recepción — {booking_id}"

    html = f"""\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;padding:30px 0;margin:0">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.06)">
    <tr>
      <td style="background:#1a1a2e;padding:24px 32px;text-align:center">
        <span style="color:#fff;font-size:20px;font-weight:700;letter-spacing:-0.5px">{hotel_label}</span>
      </td>
    </tr>
    <tr>
      <td style="padding:32px">
        <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;background:#dbeafe;color:#1e40af;margin-bottom:16px">NUEVO MENSAJE</span>
        <h2 style="margin:0 0 10px;font-size:20px;color:#111827">Tienes una respuesta de recepción</h2>
        <p style="margin:0 0 8px;font-size:14px;color:#6b7280;line-height:1.6">Habitación: <strong style="color:#374151">{room_label}</strong></p>
        <p style="margin:0 0 20px;font-size:14px;color:#374151;line-height:1.6">El equipo de <strong>{hotel_label}</strong> ha respondido a tu mensaje. Ingresa al <strong>portal del huésped</strong> para ver la respuesta y continuar la conversación.</p>
        <p style="margin:0;font-size:14px;color:#374151;line-height:1.6">Si necesitas algo más, no dudes en escribirnos por el portal o acercarte a recepción.</p>
        <hr style="border:0;border-top:1px solid #e5e7eb;margin:20px 0">
        <p style="margin:0;font-size:12px;color:#9ca3af">Reserva: {booking_id}</p>
      </td>
    </tr>
    <tr>
      <td style="background:#f9fafb;padding:16px 32px;text-align:center">
        <p style="margin:0;font-size:11px;color:#9ca3af">HotelData &middot; Notificación automática</p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    status_result = "error"
    error_msg = ""
    try:
        from src.app.email.service import send_email
        ok = send_email(guest_email, subject, html)
        if ok:
            status_result = "sent"
            logger.info("Guest chat reply notification sent to %s for booking %s", guest_email, booking_id)
        else:
            status_result = "failed"
            error_msg = "send_email returned False"
            logger.warning("Failed to send chat reply notification to %s for booking %s", guest_email, booking_id)
    except Exception as exc:
        status_result = "error"
        error_msg = str(exc)
        logger.exception("Error sending chat reply notification to %s for booking %s", guest_email, booking_id)

    try:
        db.notification_log.insert_one({
            "recipient_email": guest_email,
            "recipient_name": guest_name,
            "notification_type": "guest_chat_reply",
            "subject": subject,
            "body": f"El huésped {guest_name} (Hab. {room_label}) recibió una respuesta de recepción.",
            "status": status_result,
            "error_message": error_msg,
            "created_at": utc_now(),
            "metadata": {
                "booking_id": booking_id,
                "prop_id": prop_id,
                "room_label": room_label,
            },
        })
    except Exception:
        pass


def notify_guest_request_completed(db, request_doc: dict, new_status: str) -> None:
    """Send an email to the guest when their service request is completed or cancelled."""
    if new_status not in ("completed", "cancelled"):
        return

    booking_id = request_doc.get("booking_id", "")
    if not booking_id:
        return

    # Look up the booking to get guest contact info
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        return

    guest_email = booking.get("guest_email", "") or booking.get("email", "")
    guest_name = booking.get("guest_name", "Huésped")
    if not guest_email:
        return

    prop_id = request_doc.get("prop_id", 0)
    request_type = request_doc.get("request_type_label", request_doc.get("request_type", ""))
    room_label = request_doc.get("room_label", "")
    description = request_doc.get("description", "")
    staff_response = request_doc.get("staff_response", "")
    new_status_label_str = status_label(new_status)

    # Look up hotel name
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

    # Compose email
    if new_status == "completed":
        subject = f"Tu solicitud ha sido atendida — {booking_id}"
        status_text = "COMPLETADA"
        headline = "Tu solicitud ha sido atendida"
        body_intro = f"Tu solicitud de <strong>{request_type}</strong> ha sido <strong>completada</strong> por nuestro equipo."
        if staff_response:
            body_intro += f"<br><br><em>Respuesta del personal:</em> {staff_response}"
    else:  # cancelled
        subject = f"Tu solicitud ha sido cancelada — {booking_id}"
        status_text = "CANCELADA"
        headline = "Tu solicitud ha sido cancelada"
        body_intro = f"Tu solicitud de <strong>{request_type}</strong> ha sido <strong>cancelada</strong>."
        if staff_response:
            body_intro += f"<br><br><em>Nota:</em> {staff_response}"

    html = f"""\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;padding:30px 0;margin:0">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.06)">
    <tr>
      <td style="background:#1a1a2e;padding:24px 32px;text-align:center">
        <span style="color:#fff;font-size:20px;font-weight:700;letter-spacing:-0.5px">{hotel_label}</span>
      </td>
    </tr>
    <tr>
      <td style="padding:32px">
        <span style="display:inline-block;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;background:#dcfce7;color:#166534;margin-bottom:16px">{status_text}</span>
        <h2 style="margin:0 0 10px;font-size:20px;color:#111827">{headline}</h2>
        <p style="margin:0 0 8px;font-size:14px;color:#6b7280;line-height:1.6">Habitación: <strong style="color:#374151">{room_label}</strong></p>
        <p style="margin:0 0 20px;font-size:14px;color:#374151;line-height:1.6">{body_intro}</p>
        <hr style="border:0;border-top:1px solid #e5e7eb;margin:20px 0">
        <p style="margin:0;font-size:12px;color:#9ca3af">Reserva: {booking_id} &middot; Tipo: {request_type}</p>
        <p style="margin:0;font-size:12px;color:#9ca3af">{description}</p>
      </td>
    </tr>
    <tr>
      <td style="background:#f9fafb;padding:16px 32px;text-align:center">
        <p style="margin:0;font-size:11px;color:#9ca3af">HotelData &middot; Notificación automática</p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    status_result = "error"
    error_msg = ""
    try:
        from src.app.email.service import send_email
        ok = send_email(guest_email, subject, html)
        if ok:
            status_result = "sent"
            logger.info("Guest request notification sent to %s for booking %s (status=%s)", guest_email, booking_id, new_status)
        else:
            status_result = "failed"
            error_msg = "send_email returned False"
            logger.warning("Failed to send guest request notification to %s for booking %s", guest_email, booking_id)
    except Exception as exc:
        status_result = "error"
        error_msg = str(exc)
        logger.exception("Error sending guest request notification to %s for booking %s", guest_email, booking_id)

    # Log to notification_log
    try:
        db.notification_log.insert_one({
            "recipient_email": guest_email,
            "recipient_name": guest_name,
            "notification_type": f"guest_request_{new_status}",
            "subject": subject,
            "body": f"Solicitud de {request_type} (Hab. {room_label}) → {new_status_label_str}",
            "status": status_result,
            "error_message": error_msg,
            "created_at": utc_now(),
            "metadata": {
                "booking_id": booking_id,
                "prop_id": prop_id,
                "room_label": room_label,
                "request_id": str(request_doc.get("_id", "")),
                "request_type": request_type,
                "new_status": new_status,
            },
        })
    except Exception:
        pass


def ensure_stay_collections():
    """Ensure MongoDB collections and indexes for the In-Stay module."""
    db = get_database()

    if "stay_sessions" not in db.list_collection_names():
        db.create_collection("stay_sessions")
    db.stay_sessions.create_index("token", unique=True)
    db.stay_sessions.create_index("booking_id")
    db.stay_sessions.create_index([("prop_id", 1), ("active", 1)])
    db.stay_sessions.create_index("expires_at", expireAfterSeconds=0)

    if "stay_messages" not in db.list_collection_names():
        db.create_collection("stay_messages")
    db.stay_messages.create_index("booking_id")
    db.stay_messages.create_index([("prop_id", 1), ("room_label", 1)])
    db.stay_messages.create_index([("room_label", 1), ("created_at", -1)])
    db.stay_messages.create_index("created_at")

    if "stay_service_requests" not in db.list_collection_names():
        db.create_collection("stay_service_requests")
    db.stay_service_requests.create_index("booking_id")
    db.stay_service_requests.create_index([("prop_id", 1), ("status", 1)])
    db.stay_service_requests.create_index("created_at")
