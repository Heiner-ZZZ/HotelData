"""In-Stay (Mi Estancia) API — guest portal + staff inbox.

Guest endpoints use a session token (embedded in QR code).
Staff endpoints use standard JWT authentication.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.app.modules.instay.schemas import (
    SERVICE_REQUEST_TYPES,
    SERVICE_REQUEST_STATUSES,
    ChatMessageCreate,
    CompendiumInfo,
    PortalData,
    ServiceRequestCreate,
    ServiceRequestUpdate,
    StaySessionCreate,
    StaySessionResponse,
    utc_now,
)
from src.app.security.dependencies import require_login
from src.database.connection import get_database

# ── Routers ──

guest_router = APIRouter(prefix="/api/stay/guest", tags=["instay-guest"])
staff_router = APIRouter(prefix="/api/stay", tags=["instay-staff"])


# ── Helpers ──

_TOKEN_BYTES = 32
_SESSION_DAYS = 31  # max session lifetime


def _session_expiry() -> datetime:
    return utc_now() + timedelta(days=_SESSION_DAYS)


def _serialize_session(doc: dict) -> dict:
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


def _get_session_or_404(token: str) -> dict:
    """Validate a session token and return the session document."""
    db = get_database()
    session = db.stay_sessions.find_one({"token": token, "active": True})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada.")
    if session.get("expires_at") and session["expires_at"] < utc_now():
        raise HTTPException(status_code=410, detail="Sesión expirada.")
    return session


def _type_label(t: str) -> str:
    return SERVICE_REQUEST_TYPES.get(t, t.replace("_", " ").title())


def _status_label(s: str) -> str:
    return SERVICE_REQUEST_STATUSES.get(s, s.capitalize())


# ═══════════════════════════════════════════════════════════
# AUTHENTICATED GUEST ENDPOINT (JWT required — no token needed)
# ═══════════════════════════════════════════════════════════


@staff_router.post("/my-session")
def get_my_stay_session(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Get or create a stay session for the authenticated user's booking.

    This lets the guest access "Mi Estancia" from their reservation detail
    page without needing a QR code token. Returns the session token so the
    frontend can redirect to /stay/:token.

    Body: { "booking_id": "BK-xxx" }
    """
    booking_id = (payload.get("booking_id") or "").strip()
    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id requerido.")

    db = get_database()

    # Verify booking belongs to the current user
    user_email = current_user.get("email", "")
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    # Check the booking's guest email matches the authenticated user
    guest_email = booking.get("guest_email", "") or booking.get("email", "")
    is_owner = (
        guest_email.lower() == user_email.lower()
        or booking.get("booking_id", "") == booking_id
    )
    if not is_owner:
        # Also check if user is staff (admins can access any booking)
        role = current_user.get("primaryRole", "")
        if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
            raise HTTPException(status_code=403, detail="No tienes acceso a esta reserva.")

    # Check booking is checked in
    if booking.get("stay_status") != "checked_in":
        raise HTTPException(
            status_code=400,
            detail="La reserva no está en estancia activa. Debe tener estado 'checked_in'.",
        )

    # Check if session already exists
    existing = db.stay_sessions.find_one(
        {"booking_id": booking_id, "active": True}
    )
    if existing:
        return _serialize_session(existing)

    # Create a new session
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = utc_now()

    # Get assigned rooms for room_label
    assigned_rooms = booking.get("assigned_rooms", [])
    room_label = ""
    if assigned_rooms:
        first_room = assigned_rooms[0]
        if isinstance(first_room, dict):
            room_label = first_room.get("room_label", "") or first_room.get("room_number", "")
        else:
            room_label = str(first_room)

    doc = {
        "token": token,
        "booking_id": booking_id,
        "prop_id": booking.get("prop_id", 0),
        "room_label": room_label,
        "guest_name": booking.get("guest_name", ""),
        "check_in": str(booking.get("check_in_date", "")),
        "check_out": str(booking.get("check_out_date", "")),
        "created_at": now,
        "expires_at": _session_expiry(),
        "active": True,
    }
    db.stay_sessions.insert_one(doc)
    return _serialize_session(doc)


# ═══════════════════════════════════════════════════════════
# STAFF ENDPOINTS (JWT required)
# ═══════════════════════════════════════════════════════════


@staff_router.post("/sessions", status_code=201)
def create_stay_session(
    payload: StaySessionCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a stay session for a booking and return the token (for QR code).

    Staff generates this when the guest checks in. The token is embedded
    in a QR code placed in the room.
    """
    db = get_database()

    # Validate booking exists
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    # Check if session already exists
    existing = db.stay_sessions.find_one(
        {"booking_id": payload.booking_id, "active": True}
    )
    if existing:
        # Return existing token instead of creating duplicate
        return _serialize_session(existing)

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = utc_now()

    doc = {
        "token": token,
        "booking_id": payload.booking_id,
        "prop_id": payload.prop_id,
        "room_label": payload.room_label,
        "guest_name": payload.guest_name,
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "created_at": now,
        "expires_at": payload.expires_at or _session_expiry(),
        "active": True,
    }
    db.stay_sessions.insert_one(doc)
    return _serialize_session(doc)


@staff_router.get("/sessions")
def list_stay_sessions(
    prop_id: int | None = Query(default=None, ge=1),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List all stay sessions (active stays in the property)."""
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if active_only:
        query["active"] = True

    total = db.stay_sessions.count_documents(query)
    items = list(
        db.stay_sessions.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [_serialize_session(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


@staff_router.get("/sessions/{token}")
def get_stay_session(
    token: str,
    current_user: dict = Depends(require_login),
):
    """Get a single stay session by token."""
    db = get_database()
    session = db.stay_sessions.find_one({"token": token})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return _serialize_session(session)


@staff_router.post("/sessions/{token}/deactivate")
def deactivate_stay_session(
    token: str,
    current_user: dict = Depends(require_login),
):
    """Deactivate a stay session (e.g., after check-out)."""
    db = get_database()
    result = db.stay_sessions.update_one(
        {"token": token}, {"$set": {"active": False, "deactivated_at": utc_now()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return {"ok": True, "message": "Sesión desactivada."}


# ═══════════════════════════════════════════════════════════
# STAFF — Service Requests Inbox
# ═══════════════════════════════════════════════════════════


@staff_router.get("/requests")
def list_service_requests(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List service requests from guests (staff inbox)."""
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter

    total = db.stay_service_requests.count_documents(query)
    items = list(
        db.stay_service_requests.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return {
        "items": [
            {
                **r,
                "_id": str(r["_id"]),
                "request_type_label": _type_label(r.get("request_type", "")),
                "status_label": _status_label(r.get("status", "")),
                "created_at": _iso(r.get("created_at")),
                "resolved_at": _iso(r.get("resolved_at")),
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


@staff_router.put("/requests/{request_id}")
def update_service_request(
    request_id: str,
    payload: ServiceRequestUpdate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Update a service request status and add staff response."""
    db = get_database()
    update: dict = {
        "status": payload.status,
        "staff_responded_at": utc_now(),
    }
    if payload.staff_response:
        update["staff_response"] = payload.staff_response
    if payload.status == "completed":
        update["resolved_at"] = utc_now()

    result = db.stay_service_requests.update_one(
        {"_id": ObjectId(request_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    return {"ok": True, "message": "Solicitud actualizada."}


# ═══════════════════════════════════════════════════════════
# STAFF — Chat Inbox
# ═══════════════════════════════════════════════════════════


@staff_router.get("/conversations")
def list_conversations(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    """List active conversations grouped by room, with last message and unread count."""
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = prop_id

    pipeline = [
        {"$match": match},
        {"$sort": {"created_at": -1}},
        {
            "$group": {
                "_id": "$room_label",
                "booking_id": {"$first": "$booking_id"},
                "prop_id": {"$first": "$prop_id"},
                "last_message": {"$first": "$message"},
                "last_sender": {"$first": "$sender"},
                "last_time": {"$first": "$created_at"},
                "message_count": {"$sum": 1},
                "unread": {
                    "$sum": {"$cond": [{"$eq": ["$read", False]}, 1, 0]}
                },
            }
        },
        {"$sort": {"last_time": -1}},
    ]
    conversations = list(db.stay_messages.aggregate(pipeline))
    for c in conversations:
        c["last_time"] = _iso(c["last_time"])

    # Enrich with guest name from session
    room_labels = [c["_id"] for c in conversations]
    sessions = list(
        db.stay_sessions.find(
            {"room_label": {"$in": room_labels}, "active": True},
            {"room_label": 1, "guest_name": 1, "_id": 0},
        )
    )
    session_map = {s["room_label"]: s.get("guest_name", "") for s in sessions}
    for c in conversations:
        c["guest_name"] = session_map.get(c["_id"], "")

    return {"conversations": conversations}


@staff_router.get("/conversations/{room_label}")
def get_conversation_messages(
    room_label: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    """Get all messages for a specific room conversation."""
    db = get_database()
    query: dict = {"room_label": room_label}
    if prop_id:
        query["prop_id"] = prop_id

    messages = list(
        db.stay_messages.find(query).sort("created_at", 1)
    )
    for m in messages:
        m["_id"] = str(m["_id"])
        m["created_at"] = _iso(m.get("created_at"))

    # Mark guest messages as read
    db.stay_messages.update_many(
        {"room_label": room_label, "sender": "guest", "read": False},
        {"$set": {"read": True}},
    )

    return {"messages": messages}


@staff_router.post("/conversations/{room_label}/reply")
def staff_reply(
    room_label: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Staff replies to a guest in the chat."""
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    # Get the booking_id and prop_id from the conversation
    db = get_database()
    last_msg = db.stay_messages.find_one(
        {"room_label": room_label}, sort=[("created_at", -1)]
    )
    if not last_msg:
        raise HTTPException(status_code=404, detail="No hay conversación activa para esta habitación.")

    doc = {
        "booking_id": last_msg.get("booking_id", ""),
        "prop_id": last_msg.get("prop_id", 0),
        "room_label": room_label,
        "sender": "staff",
        "staff_name": current_user.get("display_name") or current_user.get("username", "Staff"),
        "message": message,
        "created_at": utc_now(),
        "read": True,
    }
    db.stay_messages.insert_one(doc)

    # Also create a notification
    try:
        from src.app.email.service import send_email
        session = db.stay_sessions.find_one(
            {"room_label": room_label, "active": True}
        )
        if session:
            _notify_guest_new_message(db, session)
    except Exception:
        pass

    return {"ok": True, "message": "Respuesta enviada."}


# ═══════════════════════════════════════════════════════════
# GUEST ENDPOINTS (token-based, no JWT)
# ═══════════════════════════════════════════════════════════


@guest_router.get("/ping")
def stay_ping():
    """Health check for the guest portal."""
    return {"ok": True, "module": "instay"}


@guest_router.get("/portal")
def get_portal_data(token: str = Query(..., min_length=1)):
    """Return all portal data for the guest (compendium + booking info)."""
    session = _get_session_or_404(token)
    db = get_database()
    prop_id = session["prop_id"]

    # ── Compendium: hotel info ──
    hotel = db.hotel_profile.find_one({"prop_id": prop_id})
    policies = list(db.hotel_policies.find({"prop_id": prop_id}, {"_id": 0}))
    amenities = list(
        db.hotel_amenities.find({"prop_id": prop_id}, {"_id": 0, "name": 1, "icon": 1})
    )

    compendium = CompendiumInfo(
        hotel_name=hotel.get("display_name", hotel.get("hotel_name", "")) if hotel else "",
        hotel_address=hotel.get("address", "") if hotel else "",
        hotel_phone=hotel.get("phone", "") if hotel else "",
        wifi_ssid=hotel.get("wifi_ssid", "") if hotel else "",
        wifi_password=hotel.get("wifi_password", "") if hotel else "",
        check_in_time=hotel.get("check_in_time", "15:00") if hotel else "15:00",
        check_out_time=hotel.get("check_out_time", "12:00") if hotel else "12:00",
        breakfast_hours=hotel.get("breakfast_hours", "") if hotel else "",
        restaurant_hours=hotel.get("restaurant_hours", "") if hotel else "",
        gym_hours=hotel.get("gym_hours", "") if hotel else "",
        pool_hours=hotel.get("pool_hours", "") if hotel else "",
        parking_info=hotel.get("parking_info", "") if hotel else "",
        emergency_contact=hotel.get("emergency_contact", "") if hotel else "",
        policies=policies,
        amenities=amenities,
    )

    # ── Charges ──
    booking_id = session["booking_id"]
    charges = list(
        db.additional_charges.find(
            {"booking_id": booking_id},
            {"_id": 0, "concept": 1, "amount": 1, "quantity": 1, "total": 1, "category": 1, "note": 1, "created_at": 1},
        ).sort("created_at", -1)
    )
    for c in charges:
        c["created_at"] = _iso(c.get("created_at"))

    # ── Unread messages from staff ──
    unread = db.stay_messages.count_documents({
        "booking_id": booking_id,
        "sender": "staff",
        "read": False,
    })

    # ── Pending requests ──
    pending = db.stay_service_requests.count_documents({
        "booking_id": booking_id,
        "status": {"$in": ["pending", "in_progress"]},
    })

    return {
        "session": _serialize_session(session),
        "compendium": compendium.model_dump(),
        "charges": charges,
        "unread_messages": unread,
        "pending_requests": pending,
    }


# ── Guest: Send Chat Message ──


@guest_router.post("/chat")
def guest_send_message(
    payload: dict = Body(...),
):
    """Guest sends a chat message to reception.

    Body:
    {
      "token": "<session_token>",
      "message": "Hola, necesito toallas"
    }
    """
    token = (payload.get("token") or "").strip()
    message = (payload.get("message") or "").strip()

    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    session = _get_session_or_404(token)
    db = get_database()

    doc = {
        "booking_id": session["booking_id"],
        "prop_id": session["prop_id"],
        "room_label": session["room_label"],
        "sender": "guest",
        "staff_name": "",
        "message": message,
        "created_at": utc_now(),
        "read": False,
    }
    db.stay_messages.insert_one(doc)

    # Notify staff via notification log
    try:
        _notify_staff_new_message(db, session)
    except Exception:
        pass

    return {"ok": True, "message": "Mensaje enviado."}


@guest_router.get("/chat")
def guest_get_messages(
    token: str = Query(..., min_length=1),
):
    """Guest fetches their chat history."""
    session = _get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]

    messages = list(
        db.stay_messages.find({"booking_id": booking_id}).sort("created_at", 1)
    )
    for m in messages:
        m["_id"] = str(m["_id"])
        m["created_at"] = _iso(m.get("created_at"))

    # Mark staff messages as read by guest
    db.stay_messages.update_many(
        {"booking_id": booking_id, "sender": "staff", "read": False},
        {"$set": {"read": True}},
    )

    return {"messages": messages}


# ── Guest: Service Requests ──


@guest_router.post("/requests")
def guest_create_request(
    payload: dict = Body(...),
):
    """Guest creates a service request.

    Body:
    {
      "token": "<session_token>",
      "request_type": "housekeeping",
      "description": "2 toallas extra"
    }
    """
    token = (payload.get("token") or "").strip()
    request_type = (payload.get("request_type") or "").strip()
    description = (payload.get("description") or "").strip()

    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")
    if not request_type or request_type not in SERVICE_REQUEST_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de solicitud inválido. Válidos: {', '.join(SERVICE_REQUEST_TYPES.keys())}")

    session = _get_session_or_404(token)
    db = get_database()

    doc = {
        "booking_id": session["booking_id"],
        "prop_id": session["prop_id"],
        "room_label": session["room_label"],
        "request_type": request_type,
        "request_type_label": _type_label(request_type),
        "description": description,
        "status": "pending",
        "status_label": "Pendiente",
        "staff_response": "",
        "created_at": utc_now(),
        "resolved_at": None,
    }
    result = db.stay_service_requests.insert_one(doc)

    # Notify staff
    try:
        _notify_staff_new_request(db, session, request_type)
    except Exception:
        pass

    return {
        "ok": True,
        "request_id": str(result.inserted_id),
        "message": "Solicitud enviada.",
    }


@guest_router.get("/requests")
def guest_list_requests(
    token: str = Query(..., min_length=1),
):
    """Guest lists their service requests."""
    session = _get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]

    items = list(
        db.stay_service_requests.find({"booking_id": booking_id})
        .sort("created_at", -1)
    )
    return {
        "items": [
            {
                "_id": str(r["_id"]),
                "booking_id": r.get("booking_id", ""),
                "prop_id": r.get("prop_id", 0),
                "room_label": r.get("room_label", ""),
                "request_type": r.get("request_type", ""),
                "request_type_label": _type_label(r.get("request_type", "")),
                "description": r.get("description", ""),
                "status": r.get("status", ""),
                "status_label": _status_label(r.get("status", "")),
                "staff_response": r.get("staff_response", ""),
                "created_at": _iso(r.get("created_at")),
                "resolved_at": _iso(r.get("resolved_at")),
            }
            for r in items
        ]
    }


# ═══════════════════════════════════════════════════════════
# Notification helpers
# ═══════════════════════════════════════════════════════════


def _notify_staff_new_message(db, session: dict):
    """Log a notification for staff about a new guest message."""
    db.notification_log.insert_one({
        "recipient_email": "staff",
        "notification_type": "guest_chat_message",
        "subject": f"Nuevo mensaje de {session.get('guest_name', 'huésped')} (Hab. {session.get('room_label', '')})",
        "body": f"La habitación {session.get('room_label', '')} envió un mensaje.",
        "status": "sent",
        "created_at": utc_now(),
        "metadata": {
            "prop_id": session.get("prop_id"),
            "room_label": session.get("room_label"),
            "booking_id": session.get("booking_id"),
        },
    })


def _notify_staff_new_request(db, session: dict, request_type: str):
    """Log a notification for staff about a new service request."""
    type_label = _type_label(request_type)
    db.notification_log.insert_one({
        "recipient_email": "staff",
        "notification_type": "guest_service_request",
        "subject": f"Nueva solicitud: {type_label} (Hab. {session.get('room_label', '')})",
        "body": f"El huésped {session.get('guest_name', '')} solicitó: {type_label}",
        "status": "sent",
        "created_at": utc_now(),
        "metadata": {
            "prop_id": session.get("prop_id"),
            "room_label": session.get("room_label"),
            "booking_id": session.get("booking_id"),
            "request_type": request_type,
        },
    })


def _notify_guest_new_message(db, session: dict):
    """Currently a no-op. In future, could send push notification or SMS."""
    pass


# ═══════════════════════════════════════════════════════════
# Collections setup
# ═══════════════════════════════════════════════════════════


def ensure_stay_collections():
    """Ensure MongoDB collections and indexes for the In-Stay module."""
    db = get_database()

    # stay_sessions
    if "stay_sessions" not in db.list_collection_names():
        db.create_collection("stay_sessions")
    db.stay_sessions.create_index("token", unique=True)
    db.stay_sessions.create_index("booking_id")
    db.stay_sessions.create_index([("prop_id", 1), ("active", 1)])
    db.stay_sessions.create_index("expires_at", expireAfterSeconds=0)

    # stay_messages
    if "stay_messages" not in db.list_collection_names():
        db.create_collection("stay_messages")
    db.stay_messages.create_index("booking_id")
    db.stay_messages.create_index([("prop_id", 1), ("room_label", 1)])
    db.stay_messages.create_index([("room_label", 1), ("created_at", -1)])
    db.stay_messages.create_index("created_at")

    # stay_service_requests
    if "stay_service_requests" not in db.list_collection_names():
        db.create_collection("stay_service_requests")
    db.stay_service_requests.create_index("booking_id")
    db.stay_service_requests.create_index([("prop_id", 1), ("status", 1)])
    db.stay_service_requests.create_index("created_at")
