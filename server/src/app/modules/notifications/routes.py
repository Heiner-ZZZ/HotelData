"""Client-facing notification endpoints — notifications for the current user."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from src.app.modules.notifications.promotions import (
    OFFER_STATUS_ACTIVE,
    PROMOTIONAL_TYPE,
    _collect_opted_in_guests,
    _offer_entity_wire,
    cancel_scheduled_promotion,
    get_promotion_recipients,
    list_promotion_history,
    send_or_schedule_promotion,
    set_offer_public_status,
    update_offer_entity,
)
from src.app.modules.revenue.services.promotions import CouponCodeExistsError
from src.app.security.dependencies import require_permission
from src.app.security.hotel_filter import assigned_hotels_for_user
from src.database.connection import get_database

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class PromotionSendRequest(BaseModel):
    """Body for ``POST /api/notifications/promotions`` (staff-only).

    Fase 2: los campos opcionales de oferta (public_message, ventana de
    validez, segmento, aplica-a, código + descuento) crean la entidad
    ``promotions`` y —cuando hay código + descuento— la campaña de cupones
    de Tarifas (``promotion_campaigns`` / ``coupon_codes``).
    """

    title: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=2000)
    prop_id: int | None = Field(default=None, ge=1)
    send_at: datetime | None = Field(
        default=None,
        description=(
            "Optional schedule time (ISO). Future → queued and sent by the "
            "worker; missing or past → sent immediately."
        ),
    )
    # ── Fase 2: detalles de la oferta (opcionales) ──
    public_message: str | None = Field(default=None, max_length=2000)
    validity_start: str | None = Field(
        default=None, description="Inicio de la ventana de validez (YYYY-MM-DD)."
    )
    validity_end: str | None = Field(
        default=None, description="Fin de la ventana de validez (YYYY-MM-DD)."
    )
    segment: str | None = Field(
        default=None,
        description="Segmento: all | families | couples | business.",
    )
    applies_to_scope: str | None = Field(
        default=None, description="Alcance: property | rate_plans."
    )
    rate_plan_ids: list[str] | None = Field(
        default=None, max_length=50, description="Planes tarifarios a los que aplica."
    )
    promo_code: str | None = Field(
        default=None,
        max_length=40,
        description="Código promocional (crea el cupón en Tarifas junto al descuento).",
    )
    discount_percent: int | None = Field(default=None, ge=1, le=100)
    coupon_campaign_id: str | None = Field(
        default=None,
        max_length=80,
        description=(
            "Campaña de cupones de Tarifas a VINCULAR (no crea cupones): "
            "código y descuento se derivan de la campaña existente. "
            "Mutualmente excluyente con promo_code + discount_percent."
        ),
    )

    model_config = ConfigDict(populate_by_name=True)


class PromotionSendResponse(BaseModel):
    """Wire shape of a promotional send (mirror of ``send_or_schedule_promotion``)."""

    notification_type: str
    sent: int
    skipped: int
    recipients: list[str]
    scheduled: bool = False
    campaign_id: str | None = None
    send_at_iso: str | None = None
    promotion_id: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class OfferEditRequest(BaseModel):
    """Body for ``PUT /promotions/{campaign_id}/offer`` — edit the entity
    (public message, validity window, segment, «aplica a») without re-sending.
    Fields are optional: only the ones present are updated.
    """

    public_message: str | None = Field(default=None, max_length=2000)
    validity_start: str | None = Field(
        default=None, description="Nuevo inicio de validez (YYYY-MM-DD)."
    )
    validity_end: str | None = Field(
        default=None, description="Nuevo fin de validez (YYYY-MM-DD)."
    )
    segment: str | None = Field(
        default=None, description="Segmento: all | families | couples | business."
    )
    applies_to_scope: str | None = Field(
        default=None, description="Alcance: property | rate_plans."
    )
    rate_plan_ids: list[str] | None = Field(
        default=None, max_length=50, description="Planes tarifarios a los que aplica."
    )

    model_config = ConfigDict(populate_by_name=True)


class OfferTogglePublicRequest(BaseModel):
    """Body for ``POST …/offer/toggle-public``: ``active=false`` pausa la
    oferta (fuera de la página pública), ``active=true`` la reactiva.
    """

    active: bool

    model_config = ConfigDict(populate_by_name=True)


PromotionSendRequest.model_rebuild()
PromotionSendResponse.model_rebuild()
OfferEditRequest.model_rebuild()
OfferTogglePublicRequest.model_rebuild()


@router.get("/my")
def my_notifications_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    notification_type: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("account.read")),
):
    """Return notifications for the current user, filtered by their email.

    ``notification_type`` (opcional) filtra por tipo — la pestaña
    "Promociones" del perfil pide ``guest_promotional`` y pagina solo esas,
    sin traer las transaccionales de la campanita.
    """
    db = get_database()
    user_email = (current_user.get("email") or current_user.get("username") or "").strip()
    if not user_email:
        return {
            "items": [], "total": 0, "unread_count": 0,
            "page": page, "page_size": page_size, "total_pages": 1,
        }

    match: dict[str, Any] = {
        "recipient_email": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"},
    }
    if notification_type:
        match["notification_type"] = notification_type

    total = db.notification_log.count_documents(match)
    unread = db.notification_log.count_documents({**match, "status": "sent"})

    items = list(
        db.notification_log.find(match)
        .sort([("created_at", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    # Enrich with human-readable labels
    for item in items:
        item["type_label"] = _type_label(item.get("notification_type", ""))
        item["status_label"] = _status_label(item.get("status", ""))
        item["status_tone"] = _status_tone(
            item.get("status", ""), item.get("notification_type", "")
        )
        item["is_unread"] = item.get("status") == "sent"
        # Mensaje específico del evento (p.ej. "Tus permisos en X cambiaron…")
        item["message"] = item.get("message", "")
        # Format created_at for frontend
        created = item.get("created_at")
        item["created_at_iso"] = created.isoformat() if hasattr(created, "isoformat") else str(created)

    return {
        "items": items,
        "total": total,
        "unread_count": unread,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


@router.post("/{notification_id}/read")
def mark_notification_read_api(
    notification_id: str,
    current_user: dict = Depends(require_permission("account.read")),
):
    """Mark one of the current user's notifications as read.

    Only rows whose ``recipient_email`` matches the authenticated user can
    be marked (404 otherwise). Idempotent: marking an already-read row is
    a no-op success. Used by the guest "Promociones" tab and the bell to
    clear the unread dot.
    """
    db = get_database()
    user_email = (
        current_user.get("email") or current_user.get("username") or ""
    ).strip()
    if not user_email:
        raise HTTPException(status_code=401, detail="Usuario no autenticado.")
    try:
        oid = ObjectId(notification_id)
    except Exception:  # noqa: BLE001 — malformed id
        raise HTTPException(status_code=422, detail="Id de notificación inválido.") from None

    result = db.notification_log.update_one(
        {
            "_id": oid,
            "recipient_email": {
                "$regex": f"^{re.escape(user_email)}$",
                "$options": "i",
            },
        },
        {"$set": {"status": "read", "read_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una notificación de este usuario con ese id.",
        )
    return {"id": notification_id, "read": True}


@router.get("/promotions/estimate")
def estimate_promotion_recipients(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Return how many opted-in guests would receive a promotion.

    Live recipient count for the marketing composer (Mailchimp-style). With
    ``prop_id`` it counts only guests with opt-in AND a booking at that
    hotel; without it, all opted-in guests in the system.
    """
    db = get_database()
    guests = _collect_opted_in_guests(db, prop_id)
    return {
        "count": len(guests),
        "prop_id": prop_id,
        "notification_type": PROMOTIONAL_TYPE,
    }


@router.get("/promotions/options")
def promotion_options_api(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Rate plans (con sus room types) del hotel para el selector «Aplica a».

    El composer de marketing elige si la oferta aplica a toda la propiedad o
    a planes tarifarios concretos. Cada plan ya conoce sus ``room_types``
    (``applicable_room_types``), así que la oferta se ata a la TARIFA y las
    habitaciones vienen junto con el plan — modelo de la industria (SiteMinder:
    el código promocional se enlaza a rate plans). Solo lectura.
    """
    db = get_database()
    plans = list(
        db.rate_plans.find(
            {"prop_id": prop_id},
            {"_id": 0, "rate_plan_id": 1, "name": 1, "base_rate": 1, "applicable_room_types": 1},
        )
        .sort([("name", 1)])
    )
    room_names = {
        r["room_type_id"]: r.get("name") or r["room_type_id"]
        for r in db.room_types.find(
            {"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1}
        )
    }
    for plan in plans:
        plan["room_type_labels"] = [
            room_names.get(rt, rt) for rt in (plan.get("applicable_room_types") or [])
        ]

    # Campañas de cupones del hotel (la sección «Promociones» de Tarifas) —
    # el composer puede VINCULAR una existente en vez de crear una duplicada.
    # El ``coupon_code`` mostrado es el principal de la campaña (is_primary),
    # si lo hay, o el primero de sus cupones.
    campaigns: list[dict[str, Any]] = []
    for c in db.promotion_campaigns.find(
        {"prop_id": prop_id},
        {"_id": 0, "campaign_id": 1, "name": 1, "discount_percent": 1, "is_active": 1},
    ).sort([("updated_at", -1)]):
        coupon = db.coupon_codes.find_one(
            {"campaign_id": c["campaign_id"], "is_deleted": {"$ne": True}},
            sort=[("is_primary", -1), ("created_at", 1)],
        )
        c["coupon_code"] = (coupon or {}).get("coupon_code", "") or ""
        campaigns.append(c)
    return {"prop_id": prop_id, "rate_plans": plans, "campaigns": campaigns}


@router.get("/promotions/history")
def promotion_history_api(
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Staff-only: history of sent promotions, grouped per send.

    Reads ``notification_log`` rows with type ``guest_promotional`` and
    groups them by ``campaign_id`` (one send → one item with the recipient
    count, hotel, title and date). Newest first.

    Scope (deny-by-default for restricted roles): a marketing hotelero sees
    ONLY its ``assigned_hotels`` — ``prop_id`` from the client can narrow
    within the assignment but NEVER expand it.
    """
    db = get_database()
    assigned = assigned_hotels_for_user(current_user)
    if assigned is None:
        # Sin restricción (super_admin / admin_sistema): respeta el filtro del cliente.
        prop_ids: list[int] | None = [prop_id] if prop_id else None
    elif not assigned:
        # Rol restringido sin hoteles asignados → no ve nada (deny-by-default).
        prop_ids = []
    elif prop_id and prop_id in assigned:
        prop_ids = [prop_id]
    else:
        # prop_id ausente o de otro hotel → siempre dentro de su alcance.
        prop_ids = assigned
    return list_promotion_history(
        db, prop_ids=prop_ids, page=page, page_size=page_size
    )


@router.post("/promotions", response_model=PromotionSendResponse)
def send_promotion_api(
    payload: PromotionSendRequest = Body(...),
    current_user: dict = Depends(require_permission("promotions.manage")),
) -> PromotionSendResponse:
    """Staff-only: send or schedule a promotional notification.

    Guarded by ``promotions.manage`` (marketing_hotelero, gerente, etc.).
    Only users with role ``cliente`` AND ``marketing_opt_in=True`` receive
    the ``guest_promotional`` row — transactional notifications are never
    touched.

    With a future ``send_at`` the promotion is queued (``scheduled: true``)
    and the background worker sends it when due; missing or past ``send_at``
    sends immediately (existing behavior).
    """
    user_email = (
        current_user.get("email") or current_user.get("username") or ""
    ).strip()

    # Fase 2: si llega cualquier detalle de oferta, armar el dict que crea la
    # entidad ``promotions`` (+ campaña de cupones de Tarifas si hay código).
    offer: dict[str, Any] | None = None
    has_offer = any(
        (
            payload.public_message,
            payload.validity_start,
            payload.validity_end,
            payload.segment,
            payload.applies_to_scope,
            payload.rate_plan_ids,
            payload.promo_code,
            payload.discount_percent,
            payload.coupon_campaign_id,
        )
    )
    if has_offer:
        validity: dict[str, str] = {}
        if payload.validity_start:
            validity["start_date"] = payload.validity_start
        if payload.validity_end:
            validity["end_date"] = payload.validity_end
        applies_to: dict[str, Any] | None = None
        if payload.applies_to_scope:
            applies_to = {
                "scope": payload.applies_to_scope,
                "rate_plan_ids": payload.rate_plan_ids or [],
            }
        offer = {
            "public_message": payload.public_message or "",
            "validity": validity or None,
            "segment": {"audience": payload.segment} if payload.segment else None,
            "applies_to": applies_to,
            "promo_code": payload.promo_code or "",
            "discount_percent": payload.discount_percent,
            "coupon_campaign_id": (payload.coupon_campaign_id or "").strip() or None,
        }

    try:
        result = send_or_schedule_promotion(
            title=payload.title,
            message=payload.message,
            prop_id=payload.prop_id,
            send_at=payload.send_at,
            created_by=user_email,
            offer=offer,
        )
    except CouponCodeExistsError as exc:
        # Error ESTRUCTURADO (contrato único en ``exc.detail``): el composer
        # de marketing detecta ``code == "COUPON_CODE_EXISTS"`` y ofrece
        # «Vincular esta campaña» con el ``campaign_id`` — sin parsear texto.
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PromotionSendResponse(**result)


@router.post("/promotions/{campaign_id}/cancel")
def cancel_scheduled_promotion_api(
    campaign_id: str,
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Staff-only: cancel a queued promotion before it is sent.

    Only works while the campaign is still ``pending`` (not yet sent by the
    worker). Returns 404 if the campaign does not exist or is no longer
    pending.
    """
    db = get_database()
    if not cancel_scheduled_promotion(db, campaign_id):
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontró una promoción programada pendiente con ese id."
            ),
        )
    return {"campaign_id": campaign_id, "canceled": True}


@router.put("/promotions/{campaign_id}/offer")
def edit_offer_api(
    campaign_id: str,
    payload: OfferEditRequest = Body(...),
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Edit the ``promotions`` entity of a sent campaign without re-sending.

    Marketing adjusts the public description, validity window, segment and
    «aplica a» of an already-delivered offer. The guests' bell rows are
    NEVER touched — only the public hotel page reflects the change.

    Scope: a restricted user can only edit offers of its ``assigned_hotels``
    (404 otherwise — the offer is invisible to them).
    """
    db = get_database()
    existing = db.promotions.find_one(
        {"campaign_id": campaign_id}, {"_id": 0, "prop_id": 1}
    )
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una oferta para esta campaña.",
        )
    assigned = assigned_hotels_for_user(current_user)
    if assigned is not None:
        if not assigned or int(existing["prop_id"]) not in assigned:
            raise HTTPException(
                status_code=404,
                detail="No se encontró una oferta para esta campaña.",
            )
    try:
        updated = update_offer_entity(
            db,
            campaign_id,
            public_message=payload.public_message,
            validity_start=payload.validity_start,
            validity_end=payload.validity_end,
            segment=payload.segment,
            applies_to_scope=payload.applies_to_scope,
            rate_plan_ids=payload.rate_plan_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="No se encontró una oferta para esta campaña.")
    return _offer_entity_wire(updated)


@router.post("/promotions/{campaign_id}/offer/toggle-public")
def toggle_offer_public_api(
    campaign_id: str,
    payload: OfferTogglePublicRequest = Body(...),
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Pause (``active=false``) or resume (``active=true``) a public offer.

    Pausing only hides the offer from the public hotel page — the already-
    sent bell notifications stay untouched. Resuming is rejected (400) when
    the validity window already expired.

    Scope: a restricted user can only toggle offers of its
    ``assigned_hotels`` (404 otherwise).
    """
    db = get_database()
    existing = db.promotions.find_one(
        {"campaign_id": campaign_id}, {"_id": 0, "prop_id": 1}
    )
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una oferta para esta campaña.",
        )
    assigned = assigned_hotels_for_user(current_user)
    if assigned is not None:
        if not assigned or int(existing["prop_id"]) not in assigned:
            raise HTTPException(
                status_code=404,
                detail="No se encontró una oferta para esta campaña.",
            )
    try:
        updated = set_offer_public_status(
            db, campaign_id, active=payload.active
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="No se encontró una oferta para esta campaña.")
    return {
        "campaign_id": campaign_id,
        "offer_status": updated.get("status", ""),
        "active": updated.get("status") == OFFER_STATUS_ACTIVE,
    }


@router.get("/promotions/{campaign_id}/recipients")
def promotion_recipients_api(
    campaign_id: str,
    current_user: dict = Depends(require_permission("promotions.manage")),
):
    """Full detail of one campaign: full message + per-recipient read status.

    Marketing opens a history row and sees who actually received (and read)
    the promotion. Queued campaigns (pending/canceled/error) return the
    estimate taken at scheduling time with an empty recipient list.

    Scope: a restricted user can only open campaigns of its ``assigned_hotels``
    (404 otherwise — the campaign is invisible to them).
    """
    db = get_database()
    detail = get_promotion_recipients(db, campaign_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Campaña no encontrada.")
    assigned = assigned_hotels_for_user(current_user)
    if assigned is not None:
        if not assigned or detail["prop_id"] not in assigned:
            raise HTTPException(status_code=404, detail="Campaña no encontrada.")
    return detail


def _type_label(nt: str) -> str:
    labels = {
        "guest_confirmed": "Reserva confirmada",
        "guest_rejected": "Reserva rechazada",
        "guest_cancelled": "Reserva cancelada",
        "guest_modified": "Reserva modificada",
        "guest_checked_in": "Check-in realizado",
        "guest_checked_out": "Check-out realizado",
        "guest_late_arrival": "Llegada tardía registrada",
        "guest_invoice_issued": "Factura emitida",
        "guest_amenity_request": "Solicitud de servicio",
        "guest_review_approved": "Reseña publicada",
        "guest_review_rejected": "Reseña rechazada",
        "guest_promotional": "Promoción",
        "guest_other": "Notificación",
        "role_permissions_changed": "Permisos del rol actualizados",
        "shift_expired": "Turno de caja vencido",
        "shift_open_long": "Turno de caja abierto por mucho tiempo",
        "housekeeping_check_in": "Check-in — habitación ocupada",
        "no_show_reopen": "No-show reabierto",
        "late_checkout_approved": "Late check-out aprobado",
        "late_checkout_courtesy": "Late check-out en cortesía",
        "early_checkin_approved": "Early check-in aprobado",
        "early_checkin_courtesy": "Early check-in en cortesía",
    }
    return labels.get(nt, nt.replace("guest_", "").replace("_", " ").title())


def _status_label(status: str) -> str:
    labels = {"sent": "Enviado", "failed": "Fallido", "error": "Error"}
    return labels.get(status, status)


def _status_tone(status: str, notification_type: str = "") -> str:
    # Shift alerts are warnings even though they are delivered (sent) —
    # an expired / long-open cash register deserves amber, not green.
    if notification_type in ("shift_expired", "shift_open_long"):
        return "warning"
    tones = {"sent": "success", "failed": "warning", "error": "danger"}
    return tones.get(status, "neutral")
