"""Shared helpers for In-Stay endpoint implementations."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException

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


def notify_guest_new_message(db, session: dict):
    """Currently a no-op."""
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
