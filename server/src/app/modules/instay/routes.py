"""In-Stay (Mi Estancia) API — guest portal + staff inbox.

Guest endpoints use a session token (embedded in QR code).
Staff endpoints use standard JWT authentication.

Fase #7 — Pydantic v2 *Response convention: every endpoint declares a
``response_model=`` and returns ``XResponse.model_validate(raw_dict)`` so
the wire shape is locked by Pydantic, not by ad-hoc dict construction.

Endpoints with ``response_model=StreamingResponse`` (SSE) are explicitly
excluded — they don't have a JSON wire shape.
"""

from __future__ import annotations

import asyncio
import logging
import secrets

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.app.security.permissions import user_has_permission

logger = logging.getLogger(__name__)

from src.app.core.resolvers import resolve_hotel_id
from src.app.modules.instay.routes_impl._event_manager import StayEventManager
from src.app.modules.instay.routes_impl._helpers import (
    _iso,
    get_session_or_404,
    notify_guest_new_message,
    notify_guest_request_completed,
    notify_staff_dnd_toggled,
    notify_staff_new_message,
    notify_staff_new_request,
    notify_staff_request_updated,
    resolve_hotel_room_id,
    serialize_session,
    session_expiry,
    status_label,
    type_label,
)
from src.app.modules.instay.schemas import (
    SERVICE_REQUEST_STATUSES,
    SERVICE_REQUEST_TYPES,
    ActionResponse,
    ChatMessageListResponse,
    CleanupSessionActionResponse,
    CompendiumInfo,
    ConversationListResponse,
    CreateRequestResponse,
    LostItemListResponse,
    ModuleStatusResponse,
    PortalDataResponse,
    ServiceRequestListResponse,
    ServiceRequestUpdateResponse,
    StaySessionCreate,
    StaySessionListResponse,
    StaySessionResponse,
    ToggleDndResponse,
    utc_now,
)
from src.app.security.dependencies import require_prop_permission
from src.database.connection import get_database

guest_router = APIRouter(prefix="/api/stay/guest", tags=["instay-guest"])
staff_router = APIRouter(prefix="/api/stay", tags=["instay-staff"])

_TOKEN_BYTES = 32


# ═══════════════════════════════════════════════════════════
# AUTHENTICATED GUEST ENDPOINT (JWT required — no token needed)
# ═══════════════════════════════════════════════════════════


@staff_router.post("/my-session", response_model=StaySessionResponse)
def get_my_stay_session(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    booking_id = (payload.get("booking_id") or "").strip()
    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id requerido.")

    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")
    # Cross-hotel (Migración E): la reserva debe pertenecer al hotel pedido.
    if booking.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    # ── Ownership (fix 2026-08) ────────────────────────────────────────────
    # Canonical check: the booking's ``user_id`` FK (BSON ObjectId) must equal
    # the current user's ``_id``. The previous code OR'ed with
    # ``booking.get("booking_id") == booking_id`` — always True because the
    # doc was found by that key — so ANY authenticated user holding
    # ``reservations.read`` (cliente included) could mint a guest-portal token
    # for ANY checked-in booking (guest PII + portal hijack). Hardening:
    # normalize legacy hex-string _ids on both sides so the ObjectId
    # comparison still matches (same pattern as queries.py / billing).
    user_id = current_user.get("_id")
    if isinstance(user_id, str) and ObjectId.is_valid(user_id):
        user_id = ObjectId(user_id)
    booking_user_id = booking.get("user_id")
    if isinstance(booking_user_id, str) and ObjectId.is_valid(booking_user_id):
        booking_user_id = ObjectId(booking_user_id)
    is_owner = user_id is not None and booking_user_id == user_id
    if not is_owner:
        # Legacy bookings created before the user_id FK migration may lack the
        # FK; fall back to email ownership (still scoped to the real owner —
        # never a self-confirming comparison).
        guest_email = booking.get("guest_email", "") or booking.get("email", "")
        user_email = current_user.get("email", "")
        is_owner = bool(guest_email) and guest_email.lower() == (user_email or "").lower()
    if not is_owner:
        # Staff override: any user holding ``reservations.manage`` may open a
        # guest's stay session (front-desk flow — recepcionista opens the
        # guest portal from the reservation modal; same capability the staff
        # ``create_stay_session`` endpoint requires). Permission-based (PBAC)
        # instead of a hardcoded role list so new front-desk roles never
        # regress. super_admin resolves ``*.*`` → always allowed.
        if not user_has_permission(db, current_user, "reservations.manage"):
            raise HTTPException(status_code=403, detail="No tienes acceso a esta reserva.")

    if booking.get("stay_status") != "checked_in":
        raise HTTPException(status_code=400, detail="La reserva no está en estancia activa. Debe tener estado 'checked_in'.")

    existing = db.stay_sessions.find_one({"booking_id": booking_id, "active": True})
    if existing:
        return StaySessionResponse.model_validate(serialize_session(existing))

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = utc_now()
    assigned_rooms = booking.get("assigned_rooms", [])
    room_label = ""
    if assigned_rooms:
        first_room = assigned_rooms[0]
        if isinstance(first_room, dict):
            # Legacy: dict with room_label/room_number keys
            room_label = first_room.get("room_label", "")
        elif isinstance(first_room, str):
            # Current: hotel_room_id string — resolve to room_label from hotel_rooms
            hotel_room = db.hotel_rooms.find_one(
                {"hotel_room_id": first_room},
                {"_id": 0, "room_label": 1},
            )
            if hotel_room:
                room_label = hotel_room.get("room_label", "")
            else:
                room_label = first_room

    # Resolve hotel_room_id from assigned_rooms for FK
    hotel_room_id = ""
    if assigned_rooms:
        first_room = assigned_rooms[0]
        if isinstance(first_room, str):
            hotel_room_id = first_room
        elif isinstance(first_room, dict):
            hotel_room_id = first_room.get("hotel_room_id", "")

    doc = {
        "token": token, "booking_id": booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "room_label": room_label,
        "hotel_room_id": hotel_room_id,
        "guest_name": booking.get("guest_name", ""),
        "check_in": str(booking.get("check_in_date", "")),
        "check_out": str(booking.get("check_out_date", "")),
        "created_at": now, "expires_at": session_expiry(), "active": True,
    }
    db.stay_sessions.insert_one(doc)
    return StaySessionResponse.model_validate(serialize_session(doc))


# ═══════════════════════════════════════════════════════════
# STAFF — Sessions
# ═══════════════════════════════════════════════════════════


@staff_router.post("/sessions", status_code=201, response_model=StaySessionResponse)
def create_stay_session(
    payload: StaySessionCreate = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.manage")),
):
    # Migración E: prop_id por QUERY + consistencia query↔body.
    if query_prop_id is None or payload.prop_id != query_prop_id:
        raise HTTPException(
            status_code=400, detail="prop_id del query y del body no coinciden"
        )
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    existing = db.stay_sessions.find_one({"booking_id": payload.booking_id, "active": True})
    if existing:
        return StaySessionResponse.model_validate(serialize_session(existing))

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = utc_now()
    # Resolve hotel_room_id from room_label for FK
    hotel_room_id = resolve_hotel_room_id(payload.prop_id, payload.room_label)

    doc = {
        "token": token, "booking_id": payload.booking_id,
        "prop_id": payload.prop_id,
        "hotel_id": resolve_hotel_id(payload.prop_id),
        "room_label": payload.room_label,
        "hotel_room_id": hotel_room_id,
        "guest_name": payload.guest_name, "check_in": payload.check_in,
        "check_out": payload.check_out, "created_at": now,
        "expires_at": payload.expires_at or session_expiry(), "active": True,
    }
    db.stay_sessions.insert_one(doc)
    return StaySessionResponse.model_validate(serialize_session(doc))


@staff_router.get("/sessions", response_model=StaySessionListResponse)
def list_stay_sessions(
    prop_id: int = Query(..., ge=1),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    db = get_database()
    query: dict = {"prop_id": prop_id}
    if active_only:
        query["active"] = True
    total = db.stay_sessions.count_documents(query)
    items = list(db.stay_sessions.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size))
    return StaySessionListResponse.model_validate({
        "items": [serialize_session(s) for s in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    })


@staff_router.post("/sessions/cleanup-expired", response_model=CleanupSessionActionResponse)
def cleanup_expired_stay_sessions(
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.manage")),
):
    """Deactivate stay sessions whose check-out date has already passed.

    Migración E: prop_id por QUERY obligatorio (por-hotel; ya no limpia
    todas las propiedades). Si el body trae prop_id debe coincidir.
    """
    db = get_database()
    body_prop = payload.get("prop_id")
    if body_prop is not None and int(body_prop) != query_prop_id:
        raise HTTPException(
            status_code=400, detail="prop_id del query y del body no coinciden"
        )
    prop_id = query_prop_id
    match: dict = {"active": True, "prop_id": prop_id}

    from src.app.core.timezone import local_today
    today = local_today()
    sessions = list(db.stay_sessions.find(match, {"token": 1, "booking_id": 1, "check_out": 1, "guest_name": 1, "prop_id": 1}))

    # Collect tokens for sessions whose check-out has passed
    expired_tokens: list[str] = []
    for s in sessions:
        check_out = str(s.get("check_out", ""))[:10]
        if not check_out:
            continue  # guard against missing check_out field
        if check_out < today:
            expired_tokens.append(s["token"])

    deactivated = 0
    if expired_tokens:
        result = db.stay_sessions.update_many(
            {"token": {"$in": expired_tokens}, "active": True},
            {"$set": {"active": False, "deactivated_at": utc_now()}},
        )
        deactivated = result.modified_count

    return CleanupSessionActionResponse.model_validate({
        "ok": True, "deactivated": deactivated, "total": len(sessions),
        "prop_id": prop_id, "message": f"Deactivadas {deactivated} sesiones.",
    })


@staff_router.get("/sessions/{token}", response_model=StaySessionResponse)
def get_stay_session(token: str, query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"), current_user: dict = Depends(require_prop_permission("reservations.read"))):
    db = get_database()
    session = db.stay_sessions.find_one({"token": token})
    if not session or session.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return StaySessionResponse.model_validate(serialize_session(session))


@staff_router.post("/sessions/{token}/deactivate", response_model=ActionResponse)
def deactivate_stay_session(token: str, query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"), current_user: dict = Depends(require_prop_permission("reservations.manage"))):
    db = get_database()
    session = db.stay_sessions.find_one({"token": token}, {"prop_id": 1})
    if not session or session.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    result = db.stay_sessions.update_one({"token": token}, {"$set": {"active": False, "deactivated_at": utc_now()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return ActionResponse.model_validate({"ok": True, "message": "Sesión desactivada."})


# ═══════════════════════════════════════════════════════════
# STAFF — Service Requests Inbox
# ═══════════════════════════════════════════════════════════


@staff_router.get("/requests", response_model=ServiceRequestListResponse)
def list_service_requests(
    prop_id: int = Query(..., ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    room_id: str | None = Query(default=None, description="hotel_room_id FK filter"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    db = get_database()
    query: dict = {"prop_id": prop_id}
    if status_filter:
        query["status"] = status_filter
    if room_id:
        query["hotel_room_id"] = room_id
    total = db.stay_service_requests.count_documents(query)
    items = list(db.stay_service_requests.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size))
    return ServiceRequestListResponse.model_validate({
        "items": [{
            "_id": r.get("_id"),
            "booking_id": r.get("booking_id", ""),
            "prop_id": r.get("prop_id", 0),
            "hotel_id": r.get("hotel_id"),
            "room_label": r.get("room_label", ""),
            "hotel_room_id": r.get("hotel_room_id", ""),
            "request_type": r.get("request_type", ""),
            "request_type_label": type_label(r.get("request_type", "")),
            "description": r.get("description", ""),
            "status": r.get("status", ""),
            "status_label": status_label(r.get("status", "")),
            "staff_response": r.get("staff_response", ""),
            "staff_name": r.get("staff_name", ""),
            "created_by": r.get("created_by", ""),
            "created_at": _iso(r.get("created_at")),
            "resolved_at": _iso(r.get("resolved_at")),
        } for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    })


@staff_router.get("/requests/analytics")
def service_requests_analytics(
    prop_id: int = Query(..., ge=1),
    request_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_prop_permission("reports.requests.read")),
):
    """Dashboard simple I1.1: solicitudes de servicio por estado y tipo (Mongo).

    Lee ``stay_service_requests`` directamente. Devuelve resumen (por estado y
    tiempo medio de resolución), serie de volumen por tipo/estado para el
    gráfico central y filas paginadas para la grilla del patrón Z.
    """
    from datetime import datetime, timezone

    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if request_type:
        query["request_type"] = request_type
    if status:
        query["status"] = status
    if date_from or date_to:
        date_q: dict = {}
        if date_from:
            date_q["$gte"] = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        if date_to:
            date_q["$lte"] = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
        query["created_at"] = date_q

    total = db.stay_service_requests.count_documents(query)
    all_items = list(
        db.stay_service_requests.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    )

    # ── Resumen por estado + tiempo medio de resolución (sobre todo el rango) ──
    status_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    raw_status = {r["_id"]: r["count"] for r in db.stay_service_requests.aggregate(status_pipeline)}
    by_status: dict[str, int] = {s: 0 for s in SERVICE_REQUEST_STATUSES}
    by_status.update(raw_status)
    pending = by_status.get("pending", 0)
    in_progress = by_status.get("in_progress", 0)
    completed = by_status.get("completed", 0)
    cancelled = by_status.get("cancelled", 0)

    resolution_pipeline = [
        {"$match": {**query, "status": "completed", "resolved_at": {"$ne": None}}},
        {"$project": {"minutes": {"$divide": [{"$subtract": ["$resolved_at", "$created_at"]}, 60000]}}},
        {"$group": {"_id": None, "avg": {"$avg": "$minutes"}, "n": {"$sum": 1}}},
    ]
    res_result = list(db.stay_service_requests.aggregate(resolution_pipeline))
    avg_minutes = round(res_result[0]["avg"], 1) if res_result else None
    resolved_count = res_result[0]["n"] if res_result else 0

    # ── Serie: volumen por tipo (gráfico central) ──
    type_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$request_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    type_counts = {r["_id"]: r["count"] for r in db.stay_service_requests.aggregate(type_pipeline)}
    type_keys = list(type_counts)
    type_labels = [type_label(t) for t in type_keys]
    type_data = [type_counts[t] for t in type_keys]

    # ── Serie de tendencia diaria por estado (opcional segundo dataset) ──
    daily_pipeline = [
        {"$match": query},
        {"$project": {"day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "status": 1}},
        {"$group": {"_id": {"day": "$day", "status": "$status"}, "count": {"$sum": 1}}},
        {"$sort": {"_id.day": 1}},
    ]
    daily_map: dict[str, dict[str, int]] = {}
    for r in db.stay_service_requests.aggregate(daily_pipeline):
        day = r["_id"]["day"]
        st = r["_id"]["status"]
        daily_map.setdefault(day, {})[st] = r["count"]
    daily_labels = sorted(daily_map)
    series = {
        "labels": type_labels,
        "keys": type_keys,
        "datasets": [{"label": "Solicitudes", "data": type_data}],
        "daily_labels": daily_labels,
        "daily_statuses": [
            {"label": status_label(s), "status": s, "data": [daily_map.get(d, {}).get(s, 0) for d in daily_labels]}
            for s in SERVICE_REQUEST_STATUSES
        ],
    }

    return {
        "available": True,
        "source": "mongodb",
        "prop_id": prop_id,
        "summary": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
            "avg_resolution_minutes": avg_minutes,
            "resolved_count": resolved_count,
        },
        "series": series,
        "rows": [{
            "_id": str(r.get("_id", "")),
            "booking_id": r.get("booking_id", ""),
            "prop_id": r.get("prop_id", 0),
            "room_label": r.get("room_label", ""),
            "request_type": r.get("request_type", ""),
            "request_type_label": type_label(r.get("request_type", "")),
            "description": r.get("description", ""),
            "status": r.get("status", ""),
            "status_label": status_label(r.get("status", "")),
            "created_at": _iso(r.get("created_at")),
            "resolved_at": _iso(r.get("resolved_at")),
        } for r in all_items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


@staff_router.post("/requests", status_code=201, response_model=CreateRequestResponse)
def staff_create_request(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.manage")),
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
    # Cross-hotel (Migración E): la sesión (y su reserva) deben pertenecer al
    # hotel pedido.
    if session.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=404, detail="No hay sesión activa para esta reserva.")

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
            # DND is metadata only; do not create a second status event.
            db.room_status_log.update_one(
                {"prop_id": prop_id, "room_label": room_label},
                {"$set": {"dnd": False, "dnd_updated_at": utc_now()}},
            )
            # Push SSE notification about the auto-deactivation
            try:
                notify_staff_dnd_toggled(db, session, False)
            except Exception:
                logger.exception("Failed to notify staff DND toggled for prop_id=%s", prop_id)
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
                logger.exception("Failed to insert DND deactivation message for prop_id=%s room=%s", prop_id, room_label)

    doc = {
        "booking_id": booking_id,
        "prop_id": session.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(session.get("prop_id", 0)),
        "room_label": session.get("room_label", ""),
        "hotel_room_id": resolve_hotel_room_id(session.get("prop_id", 0), session.get("room_label", "")),
        "request_type": request_type,
        "description": description,
        "status": "pending",
        "staff_response": "",
        "created_by": "staff",
        "staff_name": current_user.get("display_name") or current_user.get("username", "Staff"),
        "created_at": utc_now(),
        "resolved_at": None,
    }
    result = db.stay_service_requests.insert_one(doc)
    return CreateRequestResponse.model_validate({
        "ok": True,
        "request_id": str(result.inserted_id),
        "message": "Solicitud creada.",
        "dnd_was_active": None,
    })


@staff_router.put("/requests/{request_id}", response_model=ServiceRequestUpdateResponse)
def update_service_request(
    request_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    """Update a service request status.

    Migración E: el request debe pertenecer al hotel pedido (404 cross-hotel).
    """
    db = get_database()
    # Fetch the request before updating to get its current state
    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de solicitud inválido.")
    existing = db.stay_service_requests.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    # Cross-hotel (Migración E): el request debe pertenecer al hotel pedido.
    if existing.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    new_status = (payload.get("status") or "").strip()
    staff_response = (payload.get("staff_response") or "").strip()
    new_check_out_date = (payload.get("new_check_out_date") or "").strip()

    if not new_status:
        raise HTTPException(status_code=400, detail="status es requerido.")

    # ── Mid-stay operations: execute real action BEFORE marking as completed ──
    mid_stay_result = None
    request_type = existing.get("request_type", "")
    booking_id = existing.get("booking_id", "")
    staff_name = current_user.get("display_name") or current_user.get("username", "staff")

    if new_status == "completed" and request_type in ("extend_stay", "early_checkout"):
        try:
            from src.app.modules.instay.routes_impl._midstay_handler import (
                process_early_checkout,
                process_extend_stay,
            )
            if request_type == "extend_stay":
                if not new_check_out_date:
                    mid_stay_result = {"ok": False, "error": "new_check_out_date requerido para extender estancia."}
                else:
                    mid_stay_result = process_extend_stay(
                        booking_id,
                        new_check_out_date=new_check_out_date,
                        changed_by=staff_name,
                    )
            elif request_type == "early_checkout":
                mid_stay_result = process_early_checkout(
                    booking_id,
                    changed_by=staff_name,
                )
        except ValueError as e:
            mid_stay_result = {"ok": False, "error": str(e)}
        except Exception:
            logger.exception("Mid-stay operation failed for request %s", request_id)
            mid_stay_result = {"ok": False, "error": "Error interno al procesar la operación."}

        # If the mid-stay operation failed, don't mark the request as completed
        if mid_stay_result and not mid_stay_result.get("ok"):
            return ServiceRequestUpdateResponse.model_validate({
                "ok": False,
                "request_id": request_id,
                "message": "Operación fallida.",
                "mid_stay": mid_stay_result,
            })

    update: dict = {"status": new_status, "staff_responded_at": utc_now()}
    if staff_response:
        update["staff_response"] = staff_response
    if new_status == "completed":
        update["resolved_at"] = utc_now()
    result = db.stay_service_requests.update_one({"_id": oid}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    # Push SSE event for real-time notification to all staff
    try:
        notify_staff_request_updated(db, existing, new_status)
    except Exception:
        logger.exception("Failed to push SSE notification for request %s status=%s", request_id, new_status)

    # Send email to guest when request is completed or cancelled (fire-and-forget in background)
    import threading
    threading.Thread(
        target=notify_guest_request_completed,
        args=(db, existing, new_status),
        daemon=True,
    ).start()

    return ServiceRequestUpdateResponse.model_validate({
        "ok": True,
        "request_id": request_id,
        "message": "Solicitud actualizada.",
        "mid_stay": mid_stay_result,
    })


# ═══════════════════════════════════════════════════════════
# STAFF — Chat Inbox
# ═══════════════════════════════════════════════════════════


@staff_router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
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
    sessions = list(db.stay_sessions.find({"room_label": {"$in": room_labels}, "active": True}, {"room_label": 1, "guest_name": 1, "check_in": 1, "check_out": 1, "booking_id": 1, "_id": 0}))
    session_map = {s["room_label"]: s for s in sessions}
    for c in conversations:
        session = session_map.get(c["_id"], {})
        c["guest_name"] = session.get("guest_name", "")
        c["check_in"] = str(session.get("check_in", ""))
        c["check_out"] = str(session.get("check_out", ""))
        # Look up stay_status + stay dates from booking_orders. The portal
        # session only exists while the stay is active; once the guest checks
        # out the session disappears, but the inbox still needs the reservation
        # dates to classify the chat as "active stay" vs "history" — NOT just
        # stay_status, which can stay `pending` even after the reservation ended.
        booking_id = session.get("booking_id") or c.get("booking_id", "")
        if booking_id:
            booking = db.booking_orders.find_one(
                {"booking_id": booking_id},
                {"_id": 0, "stay_status": 1, "check_in_date": 1, "check_out_date": 1, "guest_name": 1},
            )
            if booking:
                c["stay_status"] = booking.get("stay_status", "")
                if not c["check_in"]:
                    c["check_in"] = str(booking.get("check_in_date", "") or "")
                if not c["check_out"]:
                    c["check_out"] = str(booking.get("check_out_date", "") or "")
                if not c["guest_name"]:
                    c["guest_name"] = str(booking.get("guest_name", "") or "")
            else:
                c["stay_status"] = ""

    # ── DND status per room ──
    room_labels = [c["_id"] for c in conversations]
    dnd_docs = list(db.room_status_log.find(
        {"room_label": {"$in": room_labels}},
        {"room_label": 1, "dnd": 1, "_id": 0},
    )) if room_labels else []
    dnd_map = {d["room_label"]: bool(d.get("dnd", False)) for d in dnd_docs}
    for c in conversations:
        c["dnd"] = dnd_map.get(c["_id"], False)

    return ConversationListResponse.model_validate({
        "conversations": [{
            "room_label": c.get("_id", ""),
            "booking_id": c.get("booking_id", ""),
            "prop_id": c.get("prop_id", 0),
            "last_message": c.get("last_message", ""),
            "last_sender": c.get("last_sender", ""),
            "last_time": c.get("last_time", ""),
            "message_count": c.get("message_count", 0),
            "unread": c.get("unread", 0),
            "guest_name": c.get("guest_name", ""),
            "dnd": c.get("dnd", False),
            "check_in": c.get("check_in", ""),
            "check_out": c.get("check_out", ""),
            "stay_status": c.get("stay_status", ""),
        } for c in conversations],
    })


@staff_router.get("/conversations/{room_label}", response_model=ChatMessageListResponse)
def get_conversation_messages(room_label: str, prop_id: int = Query(..., ge=1), current_user: dict = Depends(require_prop_permission("reservations.read"))):
    db = get_database()
    query: dict = {"room_label": room_label}
    if prop_id:
        query["prop_id"] = prop_id
    messages = list(db.stay_messages.find(query).sort("created_at", 1))
    db.stay_messages.update_many({"room_label": room_label, "sender": "guest", "read": False}, {"$set": {"read": True}})
    return ChatMessageListResponse.model_validate({
        "messages": [{
            "_id": m.get("_id"),
            "booking_id": m.get("booking_id", ""),
            "prop_id": m.get("prop_id", 0),
            "room_label": m.get("room_label", ""),
            "sender": m.get("sender", ""),
            "staff_name": m.get("staff_name", ""),
            "message": m.get("message", ""),
            "created_at": _iso(m.get("created_at")),
            "read": bool(m.get("read", False)),
        } for m in messages],
    })


# ═══════════════════════════════════════════════════════════
# STAFF — Real-time Notifications (SSE — StreamingResponse, no response_model)
# ═══════════════════════════════════════════════════════════


@staff_router.get("/notifications/stream")
async def staff_notifications_stream(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
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
            yield "event: connected\ndata: {}\n\n"
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


@staff_router.post("/conversations/{room_label}/reply", response_model=ActionResponse)
def staff_reply(room_label: str, payload: dict = Body(...), query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"), current_user: dict = Depends(require_prop_permission("reservations.manage"))):
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    db = get_database()
    last_msg = db.stay_messages.find_one({"room_label": room_label}, sort=[("created_at", -1)])
    if not last_msg or last_msg.get("prop_id") != query_prop_id:
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
        logger.exception("Failed to notify guest reply for room %s", room_label)
    return ActionResponse.model_validate({"ok": True, "message": "Respuesta enviada."})


# ═══════════════════════════════════════════════════════════
# GUEST ENDPOINTS (token-based, no JWT)
# ═══════════════════════════════════════════════════════════


@guest_router.get("/ping", response_model=ModuleStatusResponse)
def stay_ping():
    return ModuleStatusResponse.model_validate({"ok": True, "module": "instay"})


@guest_router.get("/portal", response_model=PortalDataResponse)
def get_portal_data(token: str = Query(..., min_length=1)):
    session = get_session_or_404(token)
    db = get_database()
    prop_id = session["prop_id"]

    hotel = db.hotel_profile.find_one({"prop_id": prop_id})
    # Resolve display name from dim_hotels (canonical source), fall back to hotel_profile
    dim_hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "display_name": 1, "hotel_name": 1},
    )
    hotel_label = (
        (dim_hotel or {}).get("display_name")
        or (dim_hotel or {}).get("hotel_name")
        or (hotel or {}).get("display_name")
        or (hotel or {}).get("hotel_name", "")
        or ""
    )
    policies = list(db.hotel_policies.find({"prop_id": prop_id}, {"_id": 0}))
    amenities = list(db.hotel_amenities.find({"prop_id": prop_id}, {"_id": 0, "name": 1, "icon": 1}))

    compendium = CompendiumInfo(
        hotel_name=hotel_label,
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
    folio_charges_payload: list[dict] = []
    for c in charges:
        folio_charges_payload.append({
            "concept": c.get("concept", ""),
            "amount": round(float(c.get("amount", 0)), 2),
            "quantity": float(c.get("quantity", 1)),
            "total": round(float(c.get("total", 0)), 2),
            "category": c.get("category", ""),
            "note": c.get("note", ""),
            "created_at": _iso(c.get("created_at")),
        })

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
            from src.app.core.timezone import local_today
            today = date.fromisoformat(local_today())
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

    return PortalDataResponse.model_validate({
        "session": serialize_session(session),
        "compendium": compendium.model_dump(),
        "charges": folio_charges_payload,
        "folio_balance": folio_balance,
        "folio_postings": folio_postings,
        "nights_remaining": nights_remaining,
        "dnd_active": dnd_active,
        "unread_messages": unread,
        "pending_requests": pending,
    })


@guest_router.post("/chat", response_model=ActionResponse)
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
        logger.exception("Failed to notify staff new message for room %s", session.get("room_label", ""))
    return ActionResponse.model_validate({"ok": True, "message": "Mensaje enviado."})


@guest_router.post("/dnd/toggle", response_model=ToggleDndResponse)
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
    # DND is metadata on the canonical room status document; preserve the
    # status transition rules while updating only the DND fields.
    db.room_status_log.update_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"$set": {"dnd": new_dnd, "dnd_updated_at": utc_now()}},
        upsert=True,
    )


    # Push SSE notification to staff
    try:
        notify_staff_dnd_toggled(db, session, new_dnd)
    except Exception:
        logger.exception("Failed to notify staff DND toggled for room %s", room_label)

    return ToggleDndResponse.model_validate({
        "ok": True, "dnd_active": new_dnd,
        "message": "DND " + ("activado" if new_dnd else "desactivado"),
    })


@guest_router.get("/chat", response_model=ChatMessageListResponse)
def guest_get_messages(token: str = Query(..., min_length=1)):
    session = get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]
    messages = list(db.stay_messages.find({"booking_id": booking_id}).sort("created_at", 1))
    db.stay_messages.update_many({"booking_id": booking_id, "sender": "staff", "read": False}, {"$set": {"read": True}})
    return ChatMessageListResponse.model_validate({
        "messages": [{
            "_id": m.get("_id"),
            "booking_id": m.get("booking_id", ""),
            "prop_id": m.get("prop_id", 0),
            "room_label": m.get("room_label", ""),
            "sender": m.get("sender", ""),
            "staff_name": m.get("staff_name", ""),
            "message": m.get("message", ""),
            "created_at": _iso(m.get("created_at")),
            "read": bool(m.get("read", False)),
        } for m in messages],
    })


@guest_router.post("/requests", response_model=CreateRequestResponse)
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
            # DND is metadata only; do not create a second status event.
            db.room_status_log.update_one(
                {"prop_id": prop_id, "room_label": room_label},
                {"$set": {"dnd": False, "dnd_updated_at": utc_now()}},
            )
            # Push SSE notification about the auto-deactivation
            try:
                notify_staff_dnd_toggled(db, session, False)
            except Exception:
                logger.exception("Failed to notify staff DND auto-deactivated for room %s", room_label)

    doc = {
        "booking_id": session["booking_id"], "prop_id": session["prop_id"],
        "hotel_id": resolve_hotel_id(session.get("prop_id", 0)),
        "room_label": session["room_label"],
        "hotel_room_id": resolve_hotel_room_id(session.get("prop_id", 0), session.get("room_label", "")),
        "request_type": request_type, "description": description,
        "status": "pending", "staff_response": "",
        "created_at": utc_now(), "resolved_at": None,
    }
    result = db.stay_service_requests.insert_one(doc)
    try:
        notify_staff_new_request(db, session, request_type)
    except Exception:
        logger.exception("Failed to notify staff new request '%s' for room %s", request_type, room_label)
    return CreateRequestResponse.model_validate({
        "ok": True, "request_id": str(result.inserted_id),
        "dnd_was_active": dnd_was_active,
        "message": "Solicitud enviada.",
    })


@guest_router.get("/requests", response_model=ServiceRequestListResponse)
def guest_list_requests(token: str = Query(..., min_length=1)):
    session = get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]
    items = list(db.stay_service_requests.find({"booking_id": booking_id}).sort("created_at", -1))
    return ServiceRequestListResponse.model_validate({
        "items": [{
            "_id": r.get("_id"),
            "booking_id": r.get("booking_id", ""),
            "prop_id": r.get("prop_id", 0),
            "hotel_id": r.get("hotel_id"),
            "room_label": r.get("room_label", ""),
            "hotel_room_id": r.get("hotel_room_id", ""),
            "request_type": r.get("request_type", ""),
            "request_type_label": type_label(r.get("request_type", "")),
            "description": r.get("description", ""),
            "status": r.get("status", ""),
            "status_label": status_label(r.get("status", "")),
            "staff_response": r.get("staff_response", ""),
            "staff_name": r.get("staff_name", ""),
            "created_by": r.get("created_by", ""),
            "created_at": _iso(r.get("created_at")),
            "resolved_at": _iso(r.get("resolved_at")),
        } for r in items],
        "total": len(items), "page": 1, "page_size": len(items), "total_pages": 1,
    })


@guest_router.post("/requests/{request_id}/cancel", response_model=ActionResponse)
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
        {"$set": {"status": "cancelled", "resolved_at": utc_now()}},
    )
    return ActionResponse.model_validate({"ok": True, "message": "Solicitud cancelada."})


# ═══════════════════════════════════════════════════════════
# GUEST — Lost & Found
# ═══════════════════════════════════════════════════════════


@guest_router.get("/lost-items", response_model=LostItemListResponse)
def guest_list_lost_items(token: str = Query(..., min_length=1)):
    """List lost & found items for the guest's booking."""
    session = get_session_or_404(token)
    db = get_database()
    booking_id = session["booking_id"]
    items = list(db.lost_and_found.find(
        {"booking_id": booking_id},
        {"description": 1, "status": 1, "location_found": 1, "reported_by": 1, "created_at": 1, "returned_to": 1}
    ).sort("created_at", -1))
    return LostItemListResponse.model_validate({
        "items": [{
            "_id": item.get("_id"),
            "description": item.get("description", ""),
            "status": item.get("status", "found"),
            "location_found": item.get("location_found", ""),
            "reported_by": item.get("reported_by", ""),
            "returned_to": item.get("returned_to", ""),
            "created_at": _iso(item.get("created_at")),
        } for item in items],
    })


# ── Re-export ensure_stay_collections so callers can import it from
#    `instay.routes` (as `instay/__init__.py` and `app/main.py` lifespan
#    do). The canonical home stays in `routes_impl/_helpers.py` — this
#    is just a re-export for module-level access. ───────────────────────────
from src.app.modules.instay.routes_impl._helpers import (
    ensure_stay_collections,  # noqa: F401
)
