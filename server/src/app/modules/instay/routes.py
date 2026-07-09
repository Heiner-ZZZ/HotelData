"""In-Stay (Mi Estancia) API — guest portal + staff inbox.

Guest endpoints use a session token (embedded in QR code).
Staff endpoints use standard JWT authentication.
"""

from __future__ import annotations

import asyncio
import json
import secrets

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.app.modules.instay.schemas import (
    SERVICE_REQUEST_TYPES,
    CompendiumInfo,
    ServiceRequestUpdate,
    StaySessionCreate,
    utc_now,
)
from src.app.modules.instay.routes_impl._helpers import (
    ensure_stay_collections,
    get_session_or_404,
    notify_guest_new_message,
    notify_guest_request_completed,
    notify_staff_dnd_toggled,
    notify_staff_new_message,
    notify_staff_new_request,
    notify_staff_request_updated,
    serialize_session,
    session_expiry,
    status_label,
    type_label,
    _iso,
)
from src.app.modules.instay.routes_impl._event_manager import StayEventManager
from src.app.security.dependencies import require_login
from src.database.connection import get_database

guest_router = APIRouter(prefix="/api/stay/guest", tags=["instay-guest"])
staff_router = APIRouter(prefix="/api/stay", tags=["instay-staff"])

_TOKEN_BYTES = 32


# ═══════════════════════════════════════════════════════════
# AUTHENTICATED GUEST ENDPOINT (JWT required — no token needed)
# ═══════════════════════════════════════════════════════════


@staff_router.post("/my-session")
def get_my_stay_session(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    booking_id = (payload.get("booking_id") or "").strip()
    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id requerido.")

    db = get_database()
    user_email = current_user.get("email", "")
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    guest_email = booking.get("guest_email", "") or booking.get("email", "")
    is_owner = guest_email.lower() == user_email.lower() or booking.get("booking_id", "") == booking_id
    if not is_owner:
        role = current_user.get("primaryRole", "")
        if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
            raise HTTPException(status_code=403, detail="No tienes acceso a esta reserva.")

    if booking.get("stay_status") != "checked_in":
        raise HTTPException(status_code=400, detail="La reserva no está en estancia activa. Debe tener estado 'checked_in'.")

    existing = db.stay_sessions.find_one({"booking_id": booking_id, "active": True})
    if existing:
        return serialize_session(existing)

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = utc_now()
    assigned_rooms = booking.get("assigned_rooms", [])
    room_label = ""
    if assigned_rooms:
        first_room = assigned_rooms[0]
        room_label = first_room.get("room_label", "") or first_room.get("room_number", "") if isinstance(first_room, dict) else str(first_room)

    doc = {
        "token": token, "booking_id": booking_id,
        "prop_id": booking.get("prop_id", 0), "room_label": room_label,
        "guest_name": booking.get("guest_name", ""),
        "check_in": str(booking.get("check_in_date", "")),
        "check_out": str(booking.get("check_out_date", "")),
        "created_at": now, "expires_at": session_expiry(), "active": True,
    }
    db.stay_sessions.insert_one(doc)
    return serialize_session(doc)


# ═══════════════════════════════════════════════════════════
# STAFF — Sessions
# ═══════════════════════════════════════════════════════════


@staff_router.post("/sessions", status_code=201)
def create_stay_session(
    payload: StaySessionCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    existing = db.stay_sessions.find_one({"booking_id": payload.booking_id, "active": True})
    if existing:
        return serialize_session(existing)

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = utc_now()
    doc = {
        "token": token, "booking_id": payload.booking_id,
        "prop_id": payload.prop_id, "room_label": payload.room_label,
        "guest_name": payload.guest_name, "check_in": payload.check_in,
        "check_out": payload.check_out, "created_at": now,
        "expires_at": payload.expires_at or session_expiry(), "active": True,
    }
    db.stay_sessions.insert_one(doc)
    return serialize_session(doc)


@staff_router.get("/sessions")
def list_stay_sessions(
    prop_id: int | None = Query(default=None, ge=1),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if active_only:
        query["active"] = True
    total = db.stay_sessions.count_documents(query)
    items = list(db.stay_sessions.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size))
    return {"items": [serialize_session(s) for s in items], "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1}


@staff_router.get("/sessions/{token}")
def get_stay_session(token: str, current_user: dict = Depends(require_login)):
    db = get_database()
    session = db.stay_sessions.find_one({"token": token})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return serialize_session(session)


@staff_router.post("/sessions/{token}/deactivate")
def deactivate_stay_session(token: str, current_user: dict = Depends(require_login)):
    db = get_database()
    result = db.stay_sessions.update_one({"token": token}, {"$set": {"active": False, "deactivated_at": utc_now()}})
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
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    total = db.stay_service_requests.count_documents(query)
    items = list(db.stay_service_requests.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size))
    return {
        "items": [{**r, "_id": str(r["_id"]), "request_type_label": type_label(r.get("request_type", "")),
                   "status_label": status_label(r.get("status", "")),
                   "created_at": _iso(r.get("created_at")), "resolved_at": _iso(r.get("resolved_at"))} for r in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


@staff_router.post("/requests", status_code=201)
def staff_create_request(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a service request from the staff inbox on behalf of a guest."""
    booking_id = (payload.get("booking_id") or "").strip()
    request_type = (payload.get("request_type") or "").strip()
    description = (payload.get("description") or "").strip()

    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id requerido.")
    if not request_type or request_type not in SERVICE_REQUEST_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de solicitud inválido. Válidos: {', '.join(SERVICE_REQUEST_TYPES.keys())}",
        )

    db = get_database()
    session = db.stay_sessions.find_one({"booking_id": booking_id, "active": True})
    if not session:
        raise HTTPException(status_code=400, detail="No hay sesión activa para esta reserva.")

    # ── DND enforcement: auto-deactivate when staff creates a request ──
    # Staff is responding to a direct guest request, so DND is no longer applicable.
    prop_id = int(session.get("prop_id") or 0)
    room_label = str(session.get("room_label") or "").strip()
    if prop_id and room_label:
        dnd_state = db.room_status_log.find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"dnd": 1},
        )
        if dnd_state and dnd_state.get("dnd"):
            db.room_status_log.update_one(
                {"prop_id": prop_id, "room_label": room_label},
                {"$set": {"dnd": False, "dnd_updated_at": utc_now()}},
            )
            # Push SSE notification about the auto-deactivation
            try:
                notify_staff_dnd_toggled(db, session, False)
            except Exception:
                pass
            # Log the auto-deactivation
            try:
                db.stay_messages.insert_one({
                    "booking_id": booking_id,
                    "prop_id": prop_id,
                    "room_label": room_label,
                    "sender": "system",
                    "staff_name": "Sistema",
                    "message": f"Modo No Molestar desactivado automáticamente — {current_user.get('display_name', current_user.get('username', 'Staff'))} creó una solicitud de servicio.",
                    "created_at": utc_now(),
                    "read": True,
                })
            except Exception:
                pass

    doc = {
        "booking_id": booking_id,
        "prop_id": session.get("prop_id", 0),
        "room_label": session.get("room_label", ""),
        "request_type": request_type,
        "request_type_label": type_label(request_type),
        "description": description,
        "status": "pending",
        "status_label": "Pendiente",
        "staff_response": "",
        "created_by": "staff",
        "staff_name": current_user.get("display_name") or current_user.get("username", "Staff"),
        "created_at": utc_now(),
        "resolved_at": None,
    }
    result = db.stay_service_requests.insert_one(doc)
    return {"ok": True, "request_id": str(result.inserted_id), "message": "Solicitud creada."}


@staff_router.put("/requests/{request_id}")
def update_service_request(
    request_id: str,
    payload: ServiceRequestUpdate = Body(...),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    # Fetch the request before updating to get its current state
    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de solicitud inválido.")
    existing = db.stay_service_requests.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    update: dict = {"status": payload.status, "staff_responded_at": utc_now()}
    if payload.staff_response:
        update["staff_response"] = payload.staff_response
    if payload.status == "completed":
        update["resolved_at"] = utc_now()
    result = db.stay_service_requests.update_one({"_id": oid}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    # Push SSE event for real-time notification to all staff
    try:
        notify_staff_request_updated(db, existing, payload.status)
    except Exception:
        pass

    # Send email to guest when request is completed or cancelled (fire-and-forget in background)
    import threading
    threading.Thread(
        target=notify_guest_request_completed,
        args=(db, existing, payload.status),
        daemon=True,
    ).start()

    return {"ok": True, "message": "Solicitud actualizada."}


# ═══════════════════════════════════════════════════════════
# STAFF — Chat Inbox
# ═══════════════════════════════════════════════════════════


@staff_router.get("/conversations")
def list_conversations(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = prop_id
    pipeline = [
        {"$match": match}, {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$room_label", "booking_id": {"$first": "$booking_id"}, "prop_id": {"$first": "$prop_id"},
                    "last_message": {"$first": "$message"}, "last_sender": {"$first": "$sender"},
                    "last_time": {"$first": "$created_at"}, "message_count": {"$sum": 1},
                    "unread": {"$sum": {"$cond": [{"$eq": ["$read", False]}, 1, 0]}}}},
        {"$sort": {"last_time": -1}},
    ]
    conversations = list(db.stay_messages.aggregate(pipeline))
    for c in conversations:
        c["last_time"] = _iso(c["last_time"])
    room_labels = [c["_id"] for c in conversations]
    sessions = list(db.stay_sessions.find({"room_label": {"$in": room_labels}, "active": True}, {"room_label": 1, "guest_name": 1, "_id": 0}))
    session_map = {s["room_label"]: s.get("guest_name", "") for s in sessions}
    for c in conversations:
        c["guest_name"] = session_map.get(c["_id"], "")

    # ── DND status per room ──
    room_labels = [c["_id"] for c in conversations]
    dnd_docs = list(db.room_status_log.find(
        {"room_label": {"$in": room_labels}},
        {"room_label": 1, "dnd": 1, "_id": 0},
    )) if room_labels else []
    dnd_map = {d["room_label"]: bool(d.get("dnd", False)) for d in dnd_docs}
    for c in conversations:
        c["dnd"] = dnd_map.get(c["_id"], False)

    return {"conversations": conversations}


@staff_router.get("/conversations/{room_label}")
def get_conversation_messages(room_label: str, prop_id: int | None = Query(default=None, ge=1), current_user: dict = Depends(require_login)):
    db = get_database()
    query: dict = {"room_label": room_label}
    if prop_id:
        query["prop_id"] = prop_id
    messages = list(db.stay_messages.find(query).sort("created_at", 1))
    for m in messages:
        m["_id"] = str(m["_id"])
        m["created_at"] = _iso(m.get("created_at"))
    db.stay_messages.update_many({"room_label": room_label, "sender": "guest", "read": False}, {"$set": {"read": True}})
    return {"messages": messages}


# ═══════════════════════════════════════════════════════════
# STAFF — Real-time Notifications (SSE)
# ═══════════════════════════════════════════════════════════


@staff_router.get("/notifications/stream")
async def staff_notifications_stream(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_login),
):
    """Server-Sent Events stream for real-time staff notifications.

    The client receives events when a guest sends a message or creates
    a service request for the specified property.

    Event format:
      data: {"type":"new_message","data":{...},"timestamp":"..."}
    """
    mgr = await StayEventManager.instance()
    queue = await mgr.subscribe(prop_id)

    async def event_generator():
        try:
            # Send initial heartbeat
            yield f"event: connected\ndata: {{}}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await mgr.unsubscribe(prop_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@staff_router.post("/conversations/{room_label}/reply")
def staff_reply(room_label: str, payload: dict = Body(...), current_user: dict = Depends(require_login)):
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    db = get_database()
    last_msg = db.stay_messages.find_one({"room_label": room_label}, sort=[("created_at", -1)])
    if not last_msg:
        raise HTTPException(status_code=404, detail="No hay conversación activa para esta habitación.")
    doc = {
        "booking_id": last_msg.get("booking_id", ""), "prop_id": last_msg.get("prop_id", 0),
        "room_label": room_label, "sender": "staff",
        "staff_name": current_user.get("display_name") or current_user.get("username", "Staff"),
        "message": message, "created_at": utc_now(), "read": True,
    }
    db.stay_messages.insert_one(doc)
    # Notify guest about the reply via email (fire-and-forget in background)
    try:
        session = db.stay_sessions.find_one({"room_label": room_label, "active": True})
        if session:
            import threading
            threading.Thread(
                target=notify_guest_new_message,
                args=(db, session),
                daemon=True,
            ).start()
    except Exception:
        pass
    return {"ok": True, "message": "Respuesta enviada."}


# ═══════════════════════════════════════════════════════════
# GUEST ENDPOINTS (token-based, no JWT)
# ═══════════════════════════════════════════════════════════


@guest_router.get("/ping")
def stay_ping():
    return {"ok": True, "module": "instay"}


@guest_router.get("/portal")
def get_portal_data(token: str = Query(..., min_length=1)):
    session = get_session_or_404(token)
    db = get_database()
    prop_id = session["prop_id"]

    hotel = db.hotel_profile.find_one({"prop_id": prop_id})
    policies = list(db.hotel_policies.find({"prop_id": prop_id}, {"_id": 0}))
    amenities = list(db.hotel_amenities.find({"prop_id": prop_id}, {"_id": 0, "name": 1, "icon": 1}))

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
        policies=policies, amenities=amenities,
    )

    booking_id = session["booking_id"]
    charges = list(db.additional_charges.find({"booking_id": booking_id},
        {"_id": 0, "concept": 1, "amount": 1, "quantity": 1, "total": 1, "category": 1, "note": 1, "created_at": 1}
    ).sort("created_at", -1))
    for c in charges:
        c["created_at"] = _iso(c.get("created_at"))

    unread = db.stay_messages.count_documents({"booking_id": booking_id, "sender": "staff", "read": False})
    pending = db.stay_service_requests.count_documents({"booking_id": booking_id, "status": {"$in": ["pending", "in_progress"]}})

    # ── Folio balance from guest_folios ──
    folio_balance = 0.0
    folio_postings: list[dict] = []
    folio = db.guest_folios.find_one({"booking_id": booking_id}, {"total_due": 1, "postings": 1})
    if folio:
        folio_balance = round(float(folio.get("total_due", 0)), 2)
        postings = folio.get("postings", []) or []
        for p in postings[-10:]:  # last 10 transactions
            posted = p.get("posted_at")
            if hasattr(posted, "isoformat"):
                posted = posted.isoformat()
            folio_postings.append({
                "concept": p.get("concept", ""),
                "category": p.get("category", ""),
                "amount": round(float(p.get("amount", 0)), 2),
                "type": p.get("type", ""),
                "posted_at": str(posted or "")[:10],
            })

    # ── Nights remaining ──
    nights_remaining = 0
    try:
        ci = session.get("check_in", "")
        co = session.get("check_out", "")
        if ci and co:
            from datetime import date
            ci_d = date.fromisoformat(ci)
            co_d = date.fromisoformat(co)
            today = date.today()
            if today >= co_d:
                nights_remaining = 0
            elif today <= ci_d:
                nights_remaining = (co_d - ci_d).days
            else:
                nights_remaining = (co_d - today).days
    except Exception:
        nights_remaining = 0

    # ── DND status ──
    dnd_active = False
    room_label = session.get("room_label", "")
    if room_label:
        dnd_doc = db.room_status_log.find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"dnd": 1},
        )
        if dnd_doc and dnd_doc.get("dnd"):
            dnd_active = True

    return {
        "session": serialize_session(session),
        "compendium": compendium.model_dump(),
        "charges": charges,
        "folio_balance": folio_balance,
        "folio_postings": folio_postings,
        "nights_remaining": nights_remaining,
        "dnd_active": dnd_active,
        "unread_messages": unread,
        "pending_requests": pending,
    }


@guest_router.post("/chat")
def guest_send_message(payload: dict = Body(...)):
    token = (payload.get("token") or "").strip()
    message = (payload.get("message") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    session = get_session_or_404(token)
    db = get_database()
    doc = {
        "booking_id": session["booking_id"], "prop_id": session["prop_id"],
        "room_label": session["room_label"], "sender": "guest",
        "staff_name": "", "message": message, "created_at": utc_now(), "read": False,
    }
    db.stay_messages.insert_one(doc)
    try:
        notify_staff_new_message(db, session)
    except Exception:
        pass
    return {"ok": True, "message": "Mensaje enviado."}


@guest_router.post("/dnd/toggle")
def guest_toggle_dnd(payload: dict = Body(...)):
    """Toggle Do Not Disturb for the guest's room."""
    token = (payload.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")

    session = get_session_or_404(token)
    db = get_database()
    prop_id = int(session.get("prop_id") or 0)
    room_label = str(session.get("room_label") or "").strip()
    if not room_label or not prop_id:
        raise HTTPException(status_code=400, detail="Esta sesión no tiene habitación o propiedad asignada.")

    current = db.room_status_log.find_one({"prop_id": prop_id, "room_label": room_label}, {"dnd": 1})
    current_dnd = current.get("dnd", False) if current else False
    new_dnd = not current_dnd

    db.room_status_log.update_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"$set": {"dnd": new_dnd, "dnd_updated_at": utc_now()}},
        upsert=True,
    )

    # Push SSE notification to staff
    try:
        notify_staff_dnd_toggled(db, session, new_dnd)
    except Exception:
        pass

    return {"ok": True, "dnd_active": new_dnd, "message": "DND " + ("activado" if new_dnd else "desactivado")}


@guest_router.get("/chat")
def guest_get_messages(token: str = Query(..., min_length=1)):
    session = get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]
    messages = list(db.stay_messages.find({"booking_id": booking_id}).sort("created_at", 1))
    for m in messages:
        m["_id"] = str(m["_id"])
        m["created_at"] = _iso(m.get("created_at"))
    db.stay_messages.update_many({"booking_id": booking_id, "sender": "staff", "read": False}, {"$set": {"read": True}})
    return {"messages": messages}


@guest_router.post("/requests")
def guest_create_request(payload: dict = Body(...)):
    token = (payload.get("token") or "").strip()
    request_type = (payload.get("request_type") or "").strip()
    description = (payload.get("description") or "").strip()

    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")
    if not request_type or request_type not in SERVICE_REQUEST_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de solicitud inválido. Válidos: {', '.join(SERVICE_REQUEST_TYPES.keys())}")

    session = get_session_or_404(token)
    db = get_database()

    # ── DND enforcement: auto-deactivate when guest creates a request ──
    # Guest is actively asking for service, so DND no longer applies.
    prop_id = int(session.get("prop_id") or 0)
    room_label = str(session.get("room_label") or "").strip()
    dnd_was_active = False
    if prop_id and room_label:
        dnd_state = db.room_status_log.find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"dnd": 1},
        )
        if dnd_state and dnd_state.get("dnd"):
            dnd_was_active = True
            db.room_status_log.update_one(
                {"prop_id": prop_id, "room_label": room_label},
                {"$set": {"dnd": False, "dnd_updated_at": utc_now()}},
            )
            # Push SSE notification about the auto-deactivation
            try:
                notify_staff_dnd_toggled(db, session, False)
            except Exception:
                pass

    doc = {
        "booking_id": session["booking_id"], "prop_id": session["prop_id"],
        "room_label": session["room_label"], "request_type": request_type,
        "request_type_label": type_label(request_type), "description": description,
        "status": "pending", "status_label": "Pendiente", "staff_response": "",
        "created_at": utc_now(), "resolved_at": None,
    }
    result = db.stay_service_requests.insert_one(doc)
    try:
        notify_staff_new_request(db, session, request_type)
    except Exception:
        pass
    return {"ok": True, "request_id": str(result.inserted_id), "dnd_was_active": dnd_was_active, "message": "Solicitud enviada."}


@guest_router.get("/requests")
def guest_list_requests(token: str = Query(..., min_length=1)):
    session = get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]
    items = list(db.stay_service_requests.find({"booking_id": booking_id}).sort("created_at", -1))
    return {"items": [{"_id": str(r["_id"]), "booking_id": r.get("booking_id", ""), "prop_id": r.get("prop_id", 0),
                       "room_label": r.get("room_label", ""), "request_type": r.get("request_type", ""),
                       "request_type_label": type_label(r.get("request_type", "")),
                       "description": r.get("description", ""), "status": r.get("status", ""),
                       "status_label": status_label(r.get("status", "")),
                       "staff_response": r.get("staff_response", ""),
                       "created_at": _iso(r.get("created_at")), "resolved_at": _iso(r.get("resolved_at"))} for r in items]}


@guest_router.post("/requests/{request_id}/cancel")
def guest_cancel_request(request_id: str, payload: dict = Body(...)):
    """Cancel a pending service request."""
    token = (payload.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")

    session = get_session_or_404(token)
    db = get_database()
    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de solicitud inválido.")

    req = db.stay_service_requests.find_one({"_id": oid, "booking_id": session["booking_id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if req.get("status") not in ("pending", "in_progress"):
        raise HTTPException(status_code=400, detail="Solo se pueden cancelar solicitudes pendientes o en proceso.")

    db.stay_service_requests.update_one(
        {"_id": oid},
        {"$set": {"status": "cancelled", "status_label": "Cancelado", "resolved_at": utc_now()}},
    )
    return {"ok": True, "message": "Solicitud cancelada."}


# ═══════════════════════════════════════════════════════════
# GUEST — Lost & Found
# ═══════════════════════════════════════════════════════════


@guest_router.get("/lost-items")
def guest_list_lost_items(token: str = Query(..., min_length=1)):
    """List lost & found items for the guest's booking."""
    session = get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]
    items = list(db.lost_and_found.find(
        {"booking_id": booking_id},
        {"description": 1, "status": 1, "location_found": 1, "reported_by": 1, "created_at": 1, "returned_to": 1}
    ).sort("created_at", -1))
    return {"items": [{
        "_id": str(item["_id"]),
        "description": item.get("description", ""),
        "status": item.get("status", "found"),
        "location_found": item.get("location_found", ""),
        "reported_by": item.get("reported_by", ""),
        "returned_to": item.get("returned_to", ""),
        "created_at": _iso(item.get("created_at")),
    } for item in items]}
