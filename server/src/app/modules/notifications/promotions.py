"""Promotional (marketing) notifications — only for opted-in guests.

Fase 2 del consentimiento de marketing: el flag ``marketing_opt_in`` del
perfil del huésped (sección "Publicidad y promociones") controla si recibe
comunicaciones promocionales (publicidad, promociones, novedades, ofertas).

Reglas de este módulo:

- Escribe filas ``notification_type="guest_promotional"`` en
  ``notification_log`` SOLO para usuarios con rol ``cliente`` (por
  ``primary_role`` string o ``primary_role_id`` FK) y ``marketing_opt_in``
  en True. Un huésped sin opt-in NUNCA recibe una fila promocional.
- El ``status`` de la fila es ``"sent"`` porque la notificación SÍ se
  entregó a la campanita del huésped (``/api/notifications/my``); el correo
  es best-effort y su resultado se registra aparte en ``email_status``.
- NO toca las notificaciones transaccionales: esas viven en
  ``src.app.modules.reservations.notifications.guest`` con sus propios tipos
  ``guest_*`` y siempre salen (confirmación, factura, etc.). Este módulo
  solo escribe ``guest_promotional``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from bson import ObjectId
from pymongo import ASCENDING, IndexModel

from src.app.core.timezone import local_today
from src.app.email.service import send_email
from src.app.email.templates import base_layout
from src.app.modules.revenue.services.promotions import create_promotion_campaign
from src.database.collections import ensure_collection
from src.database.connection import get_database

logger = logging.getLogger(__name__)

PROMOTIONAL_TYPE = "guest_promotional"

PUBLIC_OFFERS_LIMIT = 20

# ── Entidad ``promotions`` (Fase 2: oferta atada a tarifas + cupones) ─────
# El marketing compone una OFERTA (documento de negocio): qué se ofrece
# (applies_to → rate_plans), cuándo vale (validity), a quién (segment),
# la mecánica (promo_code + discount_percent) y el mensaje público de la
# página del hotel. Cuando hay código + descuento se crea además la campaña
# de cupones de Tarifas (``promotion_campaigns`` + ``coupon_codes`` — la
# sección «Promociones» que ya existía) y se enlaza vía ``coupon_campaign_id``.

PROMOTIONS_COLLECTION = "promotions"

# Estado de la ENTIDAD (el de la fila de la campanita sigue siendo sent/read).
OFFER_STATUS_PENDING = "pending"     # transitorio entre el POST y el envío inmediato
OFFER_STATUS_SCHEDULED = "scheduled"  # send_at futuro, esperando al worker
OFFER_STATUS_ACTIVE = "active"       # enviada y vigente → pública
OFFER_STATUS_PAUSED = "paused"       # pausada por el marketing: fuera de la página pública
OFFER_STATUS_CANCELED = "canceled"

SEGMENT_LABELS = {
    "all": "Todos los huéspedes",
    "families": "Familias",
    "couples": "Parejas",
    "business": "Negocios",
}

PROMOTIONS_INDEXES = [
    IndexModel(
        [("prop_id", ASCENDING), ("created_at", ASCENDING)],
        name="idx_promotions_prop_created",
    ),
    IndexModel(
        [("campaign_id", ASCENDING)],
        name="idx_promotions_campaign",
    ),
]


def ensure_promotions_collection() -> None:
    ensure_collection(PROMOTIONS_COLLECTION, PROMOTIONS_INDEXES)


def _legacy_public_offers(db, prop_id: int, hotel_label: str) -> list[dict[str, Any]]:
    """Fallback Fase 1: campañas enviadas agrupadas por ``campaign_id``.

    Hoteles que aún no tienen entidad ``promotions`` (ofertas creadas antes
    de Fase 2) siguen anunciando sus envíos: título + fecha, sin el
    ``message`` (guard PII).
    """
    rows = list(
        db.notification_log.find(
            {"notification_type": PROMOTIONAL_TYPE, "prop_id": int(prop_id)}
        )
        .sort([("created_at", -1)])
        .limit(2000)
    )
    groups: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for r in rows:
        # Filas legacy sin campaign_id: cada una es su propio envío (no
        # colapsar envíos distintos bajo una clave vacía compartida).
        key = r.get("campaign_id") or str(r["_id"])
        if key not in groups:
            groups[key] = {
                "campaign_id": r.get("campaign_id") or "",
                "title": r.get("title", ""),
                "_created": r.get("created_at"),
            }
            order.append(key)
    items = [groups[k] for k in order]
    items.sort(
        key=lambda it: it.get("_created") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    for it in items[:PUBLIC_OFFERS_LIMIT]:
        created = it.pop("_created")
        it["sent_at_iso"] = (
            created.isoformat() if hasattr(created, "isoformat") else str(created)
        )
    return items[:PUBLIC_OFFERS_LIMIT]


def _entity_public_offers(db, prop_id: int) -> list[dict[str, Any]]:
    """Ofertas públicas desde la entidad ``promotions`` (Fase 2).

    Solo las ``active`` (enviadas) y NO vencidas (``validity.end_date``
    ausente o >= hoy) se anuncian. Incluye la descripción pública (sin PII),
    la ventana de validez, el segmento, el código promocional + descuento y
    a qué planes tarifarios aplica (``applies_to_label``).
    """
    today = local_today()
    offers = list(
        db.promotions.find({"prop_id": int(prop_id)})
        .sort([("created_at", -1)])
        .limit(50)
    )
    if not offers:
        return []
    plan_names: dict[str, str] = {}
    for p in db.rate_plans.find(
        {"prop_id": int(prop_id)}, {"_id": 0, "rate_plan_id": 1, "name": 1}
    ):
        plan_names[p["rate_plan_id"]] = p.get("name") or p["rate_plan_id"]

    items: list[dict[str, Any]] = []
    for o in offers:
        if o.get("status") != OFFER_STATUS_ACTIVE:
            continue
        validity = o.get("validity") or {}
        end = validity.get("end_date")
        if end and str(end) < today:
            continue  # vencida
        applies_to = o.get("applies_to") or {}
        if applies_to.get("scope") == "rate_plans":
            ids = applies_to.get("rate_plan_ids") or []
            labels = [plan_names.get(i, i) for i in ids]
            applies_to_label = ", ".join(labels) if labels else "Planes seleccionados"
        else:
            applies_to_label = "Toda la propiedad"
        sent_at = o.get("sent_at")
        items.append(
            {
                "campaign_id": o.get("campaign_id", ""),
                "promotion_id": o.get("promotion_id", ""),
                "title": o.get("title", ""),
                "public_message": o.get("public_message", ""),
                "promo_code": o.get("promo_code"),
                "discount_percent": o.get("discount_percent"),
                "validity": validity or None,
                "applies_to_label": applies_to_label,
                "segment_label": SEGMENT_LABELS.get(
                    (o.get("segment") or {}).get("audience"), "Todos los huéspedes"
                ),
                "sent_at_iso": (
                    sent_at.isoformat()
                    if hasattr(sent_at, "isoformat")
                    else (str(sent_at) if sent_at else None)
                ),
            }
        )
    return items[:PUBLIC_OFFERS_LIMIT]


def list_public_offers(prop_id: int) -> dict[str, Any] | None:
    """Public "active offers" of a hotel.

    Fase 2 (entity-first): si el hotel tiene entidad ``promotions``, la
    página pública anuncia sus ofertas vigentes (enviadas y no vencidas)
    con descripción pública, código y a qué tarifas aplica. Si aún no tiene
    entidad, cae al fallback Fase 1: campañas enviadas agrupadas por envío.
    Devuelve ``None`` cuando el hotel no existe (404 en la ruta).

    Guard de privacidad: el ``message`` crudo NUNCA se expone — marketing
    puede haberlo personalizado con el nombre del huésped (p.ej. «¡Hola
    Horuz!»). Solo ``public_message`` (escrita a propósito para el público).
    """
    db = get_database()
    hotel = db.dim_hotels.find_one(
        {"prop_id": int(prop_id)}, {"_id": 0, "display_name": 1, "hotel_name": 1}
    )
    if hotel is None:
        return None
    hotel_label = hotel.get("display_name") or hotel.get("hotel_name") or ""

    entity_items = _entity_public_offers(db, int(prop_id))
    if entity_items:
        return {
            "prop_id": int(prop_id),
            "hotel_name": hotel_label,
            "items": entity_items,
        }
    # Fallback legacy solo si el hotel NO tiene entidad promotions.
    if db.promotions.count_documents({"prop_id": int(prop_id)}) > 0:
        return {
            "prop_id": int(prop_id),
            "hotel_name": hotel_label,
            "items": [],
        }
    return {
        "prop_id": int(prop_id),
        "hotel_name": hotel_label,
        "items": _legacy_public_offers(db, int(prop_id), hotel_label),
    }


# ── Cola de envíos programados ────────────────────────────────────────────
# Un marketing hotelero puede agendar la promoción para una fecha/hora
# futura: el POST guarda un doc en ``scheduled_promotions`` (status
# ``pending``) y un worker en segundo plano (mismo patrón daemon que el
# outbox) la envía cuando ``send_at`` vence.

SCHEDULED_COLLECTION = "scheduled_promotions"

SCHEDULED_STATUS_PENDING = "pending"
SCHEDULED_STATUS_SENT = "sent"
SCHEDULED_STATUS_CANCELED = "canceled"
SCHEDULED_STATUS_ERROR = "error"

SCHEDULED_MAX_RETRIES = 3

SCHEDULED_INDEXES = [
    IndexModel(
        [("status", ASCENDING), ("send_at", ASCENDING)],
        name="idx_scheduled_status_send_at",
    ),
]


def ensure_scheduled_promotions_collection() -> None:
    ensure_collection(SCHEDULED_COLLECTION, SCHEDULED_INDEXES)


def _new_campaign_id(prop_id: int | None) -> str:
    """Unique id per send batch, shared by all its notification_log rows.

    The history endpoint groups rows by ``campaign_id`` so one send (which
    writes one row per recipient) shows as a single item.
    """
    return f"PROMO-{int(prop_id) if prop_id is not None else 0}-{uuid4().hex[:8].upper()}"


def _build_offer(
    db,
    *,
    prop_id: int,
    title: str,
    message: str,
    public_message: str,
    validity: dict[str, str] | None,
    segment: dict[str, str] | None,
    applies_to: dict[str, Any] | None,
    promo_code: str,
    discount_percent: int | None,
    coupon_campaign_id: str | None,
    campaign_id: str,
    send_at: datetime | None,
    created_by: str,
) -> str:
    """Create the ``promotions`` entity (Fase 2) for a marketing send.

    Validations before any write:
    - The hotel must exist (``prop_id`` is required for offers).
    - ``rate_plan_ids`` (scope=rate_plans) must ALL belong to this hotel —
      a plan from another property never applies (400).
    - ``segment`` must be one of ``SEGMENT_LABELS``.
    - A ``promo_code`` requires ``discount_percent`` (1-100) — the code is
      the coupon that actually applies in reservations.

    The coupon has ONE source of truth (``promotion_campaigns`` +
    ``coupon_codes``, the «Promociones» section of Tarifas) with two ways to
    attach it:
    - **Vincular** (``coupon_campaign_id``): the offer references an
      EXISTING campaign of Tarifas (must belong to this hotel). Code and
      discount are derived from the campaign — nothing is created.
    - **Crear** (``promo_code`` + ``discount_percent``): reuses
      ``create_promotion_campaign`` to create the campaign; a code that
      already belongs to another campaign is rejected (400) instead of
      being stolen.

    Both at once is rejected (400). Returns the new ``promotion_id``.
    """
    hotel = db.dim_hotels.find_one(
        {"prop_id": int(prop_id)}, {"_id": 0, "display_name": 1, "hotel_name": 1}
    )
    if hotel is None:
        raise ValueError("Hotel no encontrado.")

    clean_segment = (segment or {}).get("audience")
    if clean_segment and clean_segment not in SEGMENT_LABELS:
        raise ValueError("Segmento inválido.")

    clean_scope = (applies_to or {}).get("scope")
    if clean_scope and clean_scope not in ("property", "rate_plans"):
        raise ValueError("Alcance de «aplica a» inválido.")
    rate_plan_ids: list[str] = []
    if clean_scope == "rate_plans":
        rate_plan_ids = [
            str(i) for i in (applies_to or {}).get("rate_plan_ids") or [] if str(i)
        ]
        if rate_plan_ids:
            found = db.rate_plans.count_documents(
                {"prop_id": int(prop_id), "rate_plan_id": {"$in": rate_plan_ids}}
            )
            if found != len(set(rate_plan_ids)):
                raise ValueError(
                    "Uno o más planes tarifarios no pertenecen a este hotel."
                )

    clean_code = (promo_code or "").strip().upper()
    clean_coupon_campaign_id = (coupon_campaign_id or "").strip()
    disc = int(discount_percent) if discount_percent is not None else None
    coupon_campaign_id: str | None = None
    if clean_code and clean_coupon_campaign_id:
        raise ValueError(
            "Elige vincular una campaña de Tarifas existente o crear una nueva, no ambas."
        )
    if clean_coupon_campaign_id:
        # VINCULAR: la campaña ya existe (Tarifas es la única fuente).
        campaign = db.promotion_campaigns.find_one(
            {"campaign_id": clean_coupon_campaign_id},
            {"_id": 0, "prop_id": 1, "name": 1, "discount_percent": 1},
        )
        if campaign is None:
            raise ValueError("La campaña de Tarifas a vincular no existe.")
        if int(campaign.get("prop_id") or 0) != int(prop_id):
            raise ValueError("La campaña de Tarifas a vincular pertenece a otro hotel.")
        disc = int(campaign.get("discount_percent") or 0)
        if not (1 <= disc <= 100):
            raise ValueError("La campaña vinculada tiene un descuento inválido.")
        coupon = db.coupon_codes.find_one(
            {"campaign_id": clean_coupon_campaign_id, "is_deleted": {"$ne": True}},
            sort=[("is_primary", -1), ("created_at", 1)],
        )
        clean_code = (coupon or {}).get("coupon_code", "") or ""
        coupon_campaign_id = clean_coupon_campaign_id
    elif clean_code:
        # CREAR: solo si el código no pertenece a otra campaña (guard en
        # ``create_promotion_campaign`` — nunca se roba un cupón existente).
        if disc is None or not (1 <= disc <= 100):
            raise ValueError("El código promocional requiere un descuento entre 1% y 100%.")
        campaign = create_promotion_campaign(
            prop_id=int(prop_id),
            name=(title or "")[:80],
            description=(public_message or message or "")[:200],
            discount_percent=disc,
            start_date=(validity or {}).get("start_date", ""),
            end_date=(validity or {}).get("end_date", ""),
            coupon_count=1,
            coupon_code=clean_code,
            is_active=True,
        )
        coupon_campaign_id = campaign["campaign_id"]

    now = datetime.now(timezone.utc)
    promotion_id = f"OFFER-{int(prop_id)}-{uuid4().hex[:8].upper()}"
    db.promotions.insert_one(
        {
            "promotion_id": promotion_id,
            "prop_id": int(prop_id),
            "title": title,
            "message": message,
            "public_message": (public_message or "").strip(),
            "status": (
                OFFER_STATUS_SCHEDULED
                if send_at is not None
                else OFFER_STATUS_PENDING
            ),
            "validity": validity or None,
            "segment": {"audience": clean_segment} if clean_segment else None,
            "applies_to": (
                {"scope": clean_scope, "rate_plan_ids": rate_plan_ids}
                if clean_scope
                else None
            ),
            "promo_code": clean_code or None,
            "discount_percent": disc,
            "coupon_campaign_id": coupon_campaign_id,
            "campaign_id": campaign_id,
            "send_at": _utc(send_at) if send_at is not None else None,
            "sent_at": None,
            "created_by": created_by,
            "created_at": now,
        }
    )
    return promotion_id

_GUEST_ROLE_NAME = "cliente"


def _cliente_role_id(db) -> ObjectId | None:
    """The ``roles._id`` for the guest role (FK-based users), if present."""
    role = db.roles.find_one({"role_name": _GUEST_ROLE_NAME}, {"_id": 1})
    return role["_id"] if role else None


def _collect_opted_in_guests(
    db, prop_id: int | None = None
) -> list[dict[str, str]]:
    """Guests with ``marketing_opt_in`` True (optional ``prop_id`` scope).

    Returns ``[{"email": ..., "name": ...}]``. Covers both role encodings:
    legacy ``primary_role: "cliente"`` and FK ``primary_role_id`` → roles.
    With ``prop_id``, only guests that booked at that hotel (hoteles
    asociados) are targeted — never the whole catalog.
    """
    role_id = _cliente_role_id(db)
    role_clause: list[dict[str, Any]] = [{"primary_role": _GUEST_ROLE_NAME}]
    if role_id is not None:
        role_clause.append({"primary_role_id": role_id})

    match: dict[str, Any] = {
        "marketing_opt_in": True,
        "email": {"$exists": True, "$ne": ""},
        "$or": role_clause,
    }
    if prop_id is not None:
        guest_emails = db.booking_orders.distinct(
            "guest_email",
            {"prop_id": int(prop_id), "guest_email": {"$exists": True, "$ne": ""}},
        )
        match["email"] = {"$in": list(guest_emails)}

    guests: list[dict[str, str]] = []
    for user in db.users.find(
        match, {"_id": 0, "email": 1, "display_name": 1, "username": 1}
    ):
        email = (user.get("email") or "").strip()
        if not email:
            continue
        name = (user.get("display_name") or user.get("username") or email).strip()
        guests.append({"email": email, "name": name})
    return guests


def _promotional_html(
    hotel_label: str, title: str, message: str, opt_out_note: str
) -> str:
    """A branded, simple promotional email built on the shared layout."""
    hotel_line = (
        f"<p style=\"margin:0 0 16px;font-size:14px;color:#3f484c\">"
        f"{hotel_label}</p>\n"
        if hotel_label
        else ""
    )
    body_content = (
        f"<p style=\"margin:0 0 16px;font-size:14px;color:#3f484c\">Hola,</p>\n"
        f"{hotel_line}"
        f"<p style=\"margin:0 0 16px;font-size:13px;color:#6f797d;line-height:1.6\">"
        f"{message}</p>\n"
    )
    return base_layout(
        headline=title,
        body_content=body_content,
        footer_note=opt_out_note,
    )


def send_promotion(
    *,
    title: str,
    message: str,
    prop_id: int | None = None,
    campaign_id: str | None = None,
    promotion_id: str | None = None,
) -> dict[str, Any]:
    """Send a promotional notification to opted-in guests only.

    Writes one ``guest_promotional`` row to ``notification_log`` per
    recipient (the guest's bell via ``GET /api/notifications/my``) and,
    best-effort, emails the same content. Transactional notification types
    are never written here.

    ``campaign_id`` is optional: the scheduler passes the id it already
    stamped when queuing the promotion, so the sent batch keeps the same
    id the history endpoint uses to group it.

    ``promotion_id`` (Fase 2) links the batch to the ``promotions`` entity:
    rows carry the reference and, after the send, the offer flips to
    ``active`` (public) with its ``sent_at`` and the batch ``campaign_id``.

    Returns ``{"notification_type", "sent", "skipped", "recipients",
    "campaign_id"}``.
    """
    db = get_database()

    hotel_label = ""
    if prop_id is not None:
        hotel = db.dim_hotels.find_one(
            {"prop_id": int(prop_id)}, {"_id": 0, "display_name": 1}
        )
        if hotel:
            hotel_label = hotel.get("display_name") or ""

    guests = _collect_opted_in_guests(db, prop_id)
    opt_out_note = (
        "Recibiste este mensaje porque aceptaste recibir publicidad, "
        "promociones, novedades y ofertas. Puedes desactivarlo en "
        "tu perfil en cualquier momento."
    )

    campaign_id = campaign_id or _new_campaign_id(prop_id)
    sent = 0
    recipients: list[str] = []
    for guest in guests:
        email_status = "sent"
        email_error = ""
        try:
            html = _promotional_html(hotel_label, title, message, opt_out_note)
            ok = send_email(guest["email"], title, html)
            if not ok:
                email_status = "failed"
                email_error = "send_email returned False"
        except Exception as exc:  # noqa: BLE001 — best-effort email
            logger.exception("Error sending promotional email to %s", guest["email"])
            email_status = "error"
            email_error = str(exc)

        row: dict[str, Any] = {
            "notification_type": PROMOTIONAL_TYPE,
            "recipient_email": guest["email"],
            "recipient_name": guest["name"],
            "booking_id": "",
            "prop_id": int(prop_id) if prop_id is not None else 0,
            "campaign_id": campaign_id,
            "status": "sent",  # entregada a la campanita del huésped
            "email_status": email_status,
            "error_message": email_error,
            "title": title,
            "message": message,
            "created_at": datetime.now(timezone.utc),
        }
        if promotion_id:
            row["promotion_id"] = promotion_id
        db.notification_log.insert_one(row)
        sent += 1
        recipients.append(guest["email"])

    if promotion_id:
        # La oferta pasó a enviada: activa (pública) con su campaña de envío.
        db.promotions.update_one(
            {"promotion_id": promotion_id},
            {
                "$set": {
                    "status": OFFER_STATUS_ACTIVE,
                    "sent_at": datetime.now(timezone.utc),
                    "campaign_id": campaign_id,
                }
            },
        )

    logger.info(
        "Promotional notification sent: %d recipient(s) (type=%s, prop_id=%s)",
        len(guests),
        PROMOTIONAL_TYPE,
        prop_id,
    )
    return {
        "notification_type": PROMOTIONAL_TYPE,
        "sent": sent,
        "skipped": 0,
        "recipients": recipients,
        "campaign_id": campaign_id,
    }


def get_promotion_recipients(db, campaign_id: str) -> dict[str, Any] | None:
    """Full detail of one campaign: full message + per-recipient read status.

    Sent campaigns read their ``notification_log`` rows (one per recipient)
    and expose ``is_read`` per guest (the bell dot). Queued ones (pending /
    canceled / error, or sent-to-zero) have no rows yet: their data lives in
    ``scheduled_promotions`` and the recipient list is empty (only the
    estimate taken at scheduling time). Returns ``None`` when the campaign
    id is unknown anywhere.
    """
    rows = list(
        db.notification_log.find({"campaign_id": campaign_id}).sort(
            [("created_at", -1)]
        )
    )
    prop_id: int | None = None
    if rows:
        first = rows[0]
        prop_id = int(first.get("prop_id", 0) or 0) or None
        recipients: list[dict[str, Any]] = []
        for r in rows:
            read_at = r.get("read_at")
            recipients.append(
                {
                    "email": r.get("recipient_email", ""),
                    "name": (r.get("recipient_name") or r.get("recipient_email") or "").strip(),
                    "is_read": r.get("status") == "read",
                    "read_at_iso": (
                        read_at.isoformat()
                        if hasattr(read_at, "isoformat")
                        else (str(read_at) if read_at else None)
                    ),
                }
            )
        return _promotion_detail_payload(
            db,
            campaign_id=campaign_id,
            title=first.get("title", ""),
            message=first.get("message", ""),
            prop_id=prop_id,
            status=SCHEDULED_STATUS_SENT,
            sent_at=first.get("created_at"),
            send_at=None,
            recipient_count=len(recipients),
            email_sent=sum(1 for r in rows if r.get("email_status") == "sent"),
            recipients=recipients,
        )

    sched = db.scheduled_promotions.find_one({"campaign_id": campaign_id})
    if sched is None:
        return None
    prop_id = int(sched.get("prop_id") or 0) or None
    return _promotion_detail_payload(
        db,
        campaign_id=campaign_id,
        title=sched.get("title", ""),
        message=sched.get("message", ""),
        prop_id=prop_id,
        status=sched.get("status", SCHEDULED_STATUS_PENDING),
        sent_at=sched.get("sent_at"),
        send_at=sched.get("send_at"),
        recipient_count=int(sched.get("estimated_recipients") or 0),
        email_sent=0,
        recipients=[],
    )


def _stamp_offer_fields(db, payload: dict[str, Any]) -> dict[str, Any]:
    """Stamp the ``promotions`` entity fields onto a campaign payload.

    Used by the history and the campaign detail so the frontend can render
    the offer state (``offer_status``: active/paused/scheduled/canceled) and
    pre-fill the edit modal without an extra fetch. Legacy campaigns without
    an entity keep the payload as-is (no ``offer_status`` key).
    """
    cid = payload.get("campaign_id") or ""
    if not cid:
        return payload
    offer = db.promotions.find_one({"campaign_id": cid})
    if offer is None:
        return payload
    payload["offer_status"] = offer.get("status", "")
    for key in (
        "public_message",
        "validity",
        "applies_to",
        "segment",
        "promo_code",
        "discount_percent",
        "coupon_campaign_id",
    ):
        if offer.get(key) is not None:
            payload[key] = offer[key]
    return payload


def _offer_entity_wire(offer: dict[str, Any]) -> dict[str, Any]:
    """Wire shape of the ``promotions`` entity for edit/toggle responses."""
    return {
        "promotion_id": offer.get("promotion_id", ""),
        "campaign_id": offer.get("campaign_id", ""),
        "prop_id": int(offer.get("prop_id") or 0),
        "title": offer.get("title", ""),
        "public_message": offer.get("public_message", ""),
        "offer_status": offer.get("status", ""),
        "validity": offer.get("validity"),
        "segment": offer.get("segment"),
        "applies_to": offer.get("applies_to"),
        "promo_code": offer.get("promo_code"),
        "discount_percent": offer.get("discount_percent"),
        "coupon_campaign_id": offer.get("coupon_campaign_id"),
    }


def update_offer_entity(
    db,
    campaign_id: str,
    *,
    public_message: str | None = None,
    validity_start: str | None = None,
    validity_end: str | None = None,
    segment: str | None = None,
    applies_to_scope: str | None = None,
    rate_plan_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    """Edit the ``promotions`` entity WITHOUT re-sending.

    Marketing can adjust the public description, the validity window, the
    segment and the «aplica a» (scope + rate plans) of an already-sent
    offer. The ``notification_log`` rows (already in the guests' bells) are
    NEVER touched — the edit only affects the public hotel page and future
    state. Returns the updated entity or ``None`` when the campaign has no
    entity (legacy send → 404 in the route).

    Validations mirror ``_build_offer``: segment must be known and, for
    scope=rate_plans, every plan must belong to this hotel (400 otherwise).
    """
    offer = db.promotions.find_one({"campaign_id": campaign_id})
    if offer is None:
        return None
    prop_id = int(offer.get("prop_id") or 0)

    if segment is not None and segment not in SEGMENT_LABELS:
        raise ValueError("Segmento inválido.")

    updates: dict[str, Any] = {}
    if public_message is not None:
        updates["public_message"] = (public_message or "").strip()

    if validity_start is not None or validity_end is not None:
        prev = offer.get("validity") or {}
        new_validity = {
            "start_date": validity_start if validity_start is not None else prev.get("start_date", ""),
            "end_date": validity_end if validity_end is not None else prev.get("end_date", ""),
        }
        new_validity = {k: v for k, v in new_validity.items() if v}
        updates["validity"] = new_validity or None

    if segment is not None:
        updates["segment"] = {"audience": segment}

    if applies_to_scope is not None:
        if applies_to_scope not in ("property", "rate_plans"):
            raise ValueError("Alcance de «aplica a» inválido.")
        clean_ids = [str(i) for i in rate_plan_ids or [] if str(i)]
        if applies_to_scope == "rate_plans" and clean_ids:
            found = db.rate_plans.count_documents(
                {"prop_id": prop_id, "rate_plan_id": {"$in": clean_ids}}
            )
            if found != len(set(clean_ids)):
                raise ValueError("Uno o más planes tarifarios no pertenecen a este hotel.")
        updates["applies_to"] = {"scope": applies_to_scope, "rate_plan_ids": clean_ids}

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        db.promotions.update_one({"_id": offer["_id"]}, {"$set": updates})
    return db.promotions.find_one({"_id": offer["_id"]})


def set_offer_public_status(db, campaign_id: str, *, active: bool) -> dict[str, Any] | None:
    """Pause (hide from the public hotel page) or resume an active offer.

    Pausing only flips the ENTITY status — the already-sent bell rows stay
    untouched (guests keep their notification). Resume restores the offer to
    the public page unless its validity window already expired (400 — you
    can't announce something expired). Returns the updated entity, or
    ``None`` when the campaign has no entity (legacy send → 404).
    """
    offer = db.promotions.find_one({"campaign_id": campaign_id})
    if offer is None:
        return None
    now = datetime.now(timezone.utc)
    if not active:
        if offer.get("status") != OFFER_STATUS_ACTIVE:
            raise ValueError("Solo las ofertas activas pueden pausarse.")
        db.promotions.update_one(
            {"_id": offer["_id"]},
            {
                "$set": {
                    "status": OFFER_STATUS_PAUSED,
                    "paused_at": now,
                    "updated_at": now,
                }
            },
        )
    else:
        if offer.get("status") != OFFER_STATUS_PAUSED:
            raise ValueError("La oferta no está pausada.")
        validity = offer.get("validity") or {}
        end = validity.get("end_date")
        if end and str(end) < local_today():
            raise ValueError("La oferta ya venció y no puede reactivarse.")
        db.promotions.update_one(
            {"_id": offer["_id"]},
            {
                "$set": {
                    "status": OFFER_STATUS_ACTIVE,
                    "paused_at": None,
                    "updated_at": now,
                }
            },
        )
    return db.promotions.find_one({"_id": offer["_id"]})


def _promotion_detail_payload(
    db,
    *,
    campaign_id: str,
    title: str,
    message: str,
    prop_id: int | None,
    status: str,
    sent_at: Any,
    send_at: Any,
    recipient_count: int,
    email_sent: int,
    recipients: list[dict[str, Any]],
) -> dict[str, Any]:
    """Wire shape shared by sent and queued campaign details."""
    hotel_label = ""
    if prop_id is not None:
        hotel = db.dim_hotels.find_one(
            {"prop_id": prop_id}, {"_id": 0, "display_name": 1, "hotel_name": 1}
        )
        if hotel:
            hotel_label = hotel.get("display_name") or hotel.get("hotel_name") or ""
    payload: dict[str, Any] = {
        "campaign_id": campaign_id,
        "title": title,
        "message": message,
        "prop_id": prop_id if prop_id is not None else 0,
        "hotel_name": hotel_label,
        "status": status,
        "recipient_count": recipient_count,
        "email_sent": email_sent,
        "recipients": recipients,
    }
    if sent_at is not None:
        payload["sent_at_iso"] = (
            sent_at.isoformat() if hasattr(sent_at, "isoformat") else str(sent_at)
        )
    if send_at is not None:
        payload["send_at_iso"] = (
            send_at.isoformat() if hasattr(send_at, "isoformat") else str(send_at)
        )
    return _stamp_offer_fields(db, payload)


def list_promotion_history(
    db,
    prop_id: int | None = None,
    prop_ids: list[int] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Promotions history: sent (grouped per campaign) + queued ones.

    Sent rows are read from ``notification_log`` (one per recipient) and
    grouped by ``campaign_id`` into a single item with ``recipient_count``.
    Queued promotions come from ``scheduled_promotions`` with status
    ``pending`` / ``canceled`` / ``error`` (they have no ``notification_log``
    rows yet); already-sent scheduled campaigns are excluded to avoid
    duplicates — their rows already group under the same ``campaign_id``.

    Scope: ``prop_id`` (single hotel) or ``prop_ids`` (hotel list — the
    marketing user's assigned hotels; ``prop_ids=[]`` matches nothing,
    deny-by-default). ``prop_ids`` wins over ``prop_id``.

    Every item carries ``status`` ("sent" | "pending" | "canceled" |
    "error"), ``sent_at_iso`` for sent ones and ``send_at_iso`` for queued
    ones. Sorted newest-first by the relevant timestamp.
    """
    if prop_ids is not None:
        prop_clause: dict[str, Any] = {
            "prop_id": {"$in": [int(p) for p in prop_ids]}
        }
    elif prop_id is not None:
        prop_clause = {"prop_id": int(prop_id)}
    else:
        prop_clause = {}

    match: dict[str, Any] = {"notification_type": PROMOTIONAL_TYPE, **prop_clause}

    rows = list(
        db.notification_log.find(match).sort([("created_at", -1)]).limit(2000)
    )

    groups: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for r in rows:
        cid = r.get("campaign_id")
        if not cid:
            cid = (
                f"legacy:{r.get('title')}|{r.get('message')}|"
                f"{r.get('prop_id')}|{r.get('created_at')}"
            )
        group = groups.get(cid)
        if group is None:
            group = {
                "campaign_id": r.get("campaign_id") or "",
                "title": r.get("title", ""),
                "message": r.get("message", ""),
                "prop_id": int(r.get("prop_id", 0) or 0),
                "status": SCHEDULED_STATUS_SENT,
                "_display_at": r.get("created_at"),
                "sent_at": r.get("created_at"),
                "recipients": [],
                "email_sent": 0,
            }
            groups[cid] = group
            order.append(cid)
        email = (r.get("recipient_email") or "").strip()
        if email and email not in group["recipients"]:
            group["recipients"].append(email)
        if r.get("email_status") == "sent":
            group["email_sent"] += 1

    # Promociones de la cola (pendientes / canceladas / error) + las enviadas
    # a 0 destinatarios: estas últimas NO tienen filas en notification_log
    # (nadie recibió), así que sin este doc desaparecerían del historial.
    # Las enviadas con destinatarios se excluyen: sus filas ya agrupan bajo
    # el mismo campaign_id en ``groups`` (no duplicar).
    row_campaign_ids = {r.get("campaign_id") for r in rows if r.get("campaign_id")}
    sched_match: dict[str, Any] = {**prop_clause}
    queued_items: list[dict[str, Any]] = []
    for s in db.scheduled_promotions.find(sched_match):
        status = s.get("status", SCHEDULED_STATUS_PENDING)
        if status == SCHEDULED_STATUS_SENT and s.get("campaign_id") in row_campaign_ids:
            continue  # ya está representado por sus filas en notification_log
        queued_items.append(
            {
                "campaign_id": s.get("campaign_id", ""),
                "title": s.get("title", ""),
                "message": s.get("message", ""),
                "prop_id": int(s.get("prop_id") or 0) if s.get("prop_id") else 0,
                "status": status,
                "_display_at": s.get("send_at"),
                "sent_at": s.get("sent_at") if status == SCHEDULED_STATUS_SENT else None,
                "send_at": s.get("send_at"),
                "recipients": [],
                "recipient_count": int(s.get("estimated_recipients") or 0),
                "email_sent": 0,
            }
        )

    all_items = [groups[cid] for cid in order] + queued_items
    all_items.sort(key=lambda it: it.get("_display_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    total = len(all_items)
    start = (page - 1) * page_size
    page_items = all_items[start : start + page_size]

    # Enriquecer con el nombre del hotel.
    prop_ids = {it["prop_id"] for it in page_items if it["prop_id"]}
    hotels: dict[int, str] = {}
    if prop_ids:
        for h in db.dim_hotels.find(
            {"prop_id": {"$in": list(prop_ids)}},
            {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1},
        ):
            hotels[int(h["prop_id"])] = (
                h.get("display_name") or h.get("hotel_name") or ""
            )

    for it in page_items:
        it["hotel_name"] = hotels.get(it["prop_id"], "")
        if "recipient_count" not in it:
            it["recipient_count"] = len(it["recipients"])
        created = it.pop("sent_at", None)
        if created is not None:
            it["sent_at_iso"] = (
                created.isoformat() if hasattr(created, "isoformat") else str(created)
            )
        queued = it.pop("send_at", None)
        if queued is not None:
            it["send_at_iso"] = (
                queued.isoformat() if hasattr(queued, "isoformat") else str(queued)
            )
        it.pop("_display_at", None)
        # Entidad ``promotions`` (Fase 2): estado de la oferta + campos
        # editables para pre-llenar el modal sin un fetch extra.
        cid = it.get("campaign_id") or ""
        if cid:
            offer = db.promotions.find_one({"campaign_id": cid})
            if offer is not None:
                it["offer_status"] = offer.get("status", "")
                for key in (
                    "public_message",
                    "validity",
                    "applies_to",
                    "segment",
                    "promo_code",
                    "discount_percent",
                    "coupon_campaign_id",
                ):
                    if offer.get(key) is not None:
                        it[key] = offer[key]


    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


# ── Cola de envíos programados ────────────────────────────────────────────


def _utc(dt: datetime) -> datetime:
    """Normalize to an aware UTC datetime (project convention)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def schedule_promotion(
    *,
    title: str,
    message: str,
    prop_id: int | None,
    send_at: datetime,
    created_by: str,
    campaign_id: str | None = None,
    promotion_id: str | None = None,
) -> dict[str, Any]:
    """Queue a promotion to be sent when ``send_at`` arrives.

    Stores one doc in ``scheduled_promotions`` (status ``pending``) with the
    recipient estimate taken at scheduling time. The background worker
    (``process_due_scheduled_promotions``) sends it once due. Nothing is
    written to ``notification_log`` yet.

    ``campaign_id`` / ``promotion_id`` (Fase 2) let the caller reuse the
    batch id it already stamped on the ``promotions`` entity, so history,
    detail and the entity stay linked.

    Returns ``{"campaign_id", "send_at_iso", "estimated_recipients"}``.
    """
    db = get_database()
    send_at = _utc(send_at)
    campaign_id = campaign_id or _new_campaign_id(prop_id)
    estimated = len(_collect_opted_in_guests(db, prop_id))
    now = datetime.now(timezone.utc)
    doc: dict[str, Any] = {
        "campaign_id": campaign_id,
        "title": title,
        "message": message,
        "prop_id": int(prop_id) if prop_id is not None else None,
        "send_at": send_at,
        "estimated_recipients": estimated,
        "created_by": created_by,
        "status": SCHEDULED_STATUS_PENDING,
        "retries": 0,
        "created_at": now,
        "sent_at": None,
        "canceled_at": None,
        "last_error": None,
    }
    if promotion_id:
        doc["promotion_id"] = promotion_id
    db.scheduled_promotions.insert_one(doc)
    logger.info(
        "Promotional notification scheduled for %s (campaign_id=%s, prop_id=%s)",
        send_at.isoformat(),
        campaign_id,
        prop_id,
    )
    return {
        "campaign_id": campaign_id,
        "send_at_iso": send_at.isoformat(),
        "estimated_recipients": estimated,
    }


def send_or_schedule_promotion(
    *,
    title: str,
    message: str,
    prop_id: int | None,
    send_at: datetime | None,
    created_by: str,
    offer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Immediate send, or queue for later when ``send_at`` is in the future.

    ``send_at`` in the past or missing falls back to the immediate send
    (graceful — the clock may tick between picking the time and submitting,
    and sending now is always less surprising than failing).

    ``offer`` (Fase 2) carries the offer entity fields (public_message,
    validity, segment, applies_to, promo_code, discount_percent). When
    present, the ``promotions`` entity is created first (coupon campaign of
    Tarifas included when there's a code) and the send/schedule is stamped
    with its ``promotion_id``. The response then includes ``promotion_id``.
    """
    if offer is not None:
        if not prop_id:
            raise ValueError("La promoción debe pertenecer a un hotel.")
        campaign_id = _new_campaign_id(prop_id)
        promotion_id = _build_offer(
            db=get_database(),
            prop_id=prop_id,
            title=title,
            message=message,
            campaign_id=campaign_id,
            send_at=send_at,
            created_by=created_by,
            **offer,
        )
        if send_at is not None:
            send_at = _utc(send_at)
            if send_at > datetime.now(timezone.utc):
                scheduled = schedule_promotion(
                    title=title,
                    message=message,
                    prop_id=prop_id,
                    send_at=send_at,
                    created_by=created_by,
                    campaign_id=campaign_id,
                    promotion_id=promotion_id,
                )
                return {
                    "notification_type": PROMOTIONAL_TYPE,
                    "sent": 0,
                    "skipped": 0,
                    "recipients": [],
                    "scheduled": True,
                    "campaign_id": scheduled["campaign_id"],
                    "send_at_iso": scheduled["send_at_iso"],
                    "promotion_id": promotion_id,
                }
        result = send_promotion(
            title=title,
            message=message,
            prop_id=prop_id,
            campaign_id=campaign_id,
            promotion_id=promotion_id,
        )
        result["scheduled"] = False
        result["send_at_iso"] = None
        result["promotion_id"] = promotion_id
        return result

    if send_at is not None:
        send_at = _utc(send_at)
        if send_at > datetime.now(timezone.utc):
            scheduled = schedule_promotion(
                title=title,
                message=message,
                prop_id=prop_id,
                send_at=send_at,
                created_by=created_by,
            )
            return {
                "notification_type": PROMOTIONAL_TYPE,
                "sent": 0,
                "skipped": 0,
                "recipients": [],
                "scheduled": True,
                "campaign_id": scheduled["campaign_id"],
                "send_at_iso": scheduled["send_at_iso"],
                "promotion_id": None,
            }
    result = send_promotion(title=title, message=message, prop_id=prop_id)
    result["scheduled"] = False
    result["send_at_iso"] = None
    result["promotion_id"] = None
    return result


def cancel_scheduled_promotion(db, campaign_id: str) -> bool:
    """Cancel a queued promotion (only while still ``pending``).

    Atomic ``update_one`` on (campaign_id, status=pending): if the worker
    already sent it between the fetch and this call, nothing is canceled
    and ``False`` is returned (the caller turns that into a 404).
    """
    result = db.scheduled_promotions.update_one(
        {"campaign_id": campaign_id, "status": SCHEDULED_STATUS_PENDING},
        {
            "$set": {
                "status": SCHEDULED_STATUS_CANCELED,
                "canceled_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.modified_count == 1:
        # La entidad promotions programada también queda cancelada.
        db.promotions.update_one(
            {"campaign_id": campaign_id, "status": OFFER_STATUS_SCHEDULED},
            {
                "$set": {
                    "status": OFFER_STATUS_CANCELED,
                    "canceled_at": datetime.now(timezone.utc),
                }
            },
        )
    return result.modified_count == 1


def process_due_scheduled_promotions(db, *, now: datetime | None = None) -> int:
    """Send every queued promotion whose ``send_at`` has arrived.

    Called periodically by the daemon worker (and on startup to catch up).
    Follows the outbox retry pattern: transient failures keep the campaign
    ``pending`` and increment ``retries``; after ``SCHEDULED_MAX_RETRIES``
    it is marked ``error`` (surfaced in the history) and not retried.

    Returns the number of campaigns actually sent.
    """
    now = now or datetime.now(timezone.utc)
    due = list(
        db.scheduled_promotions.find(
            {"status": SCHEDULED_STATUS_PENDING, "send_at": {"$lte": now}}
        )
    )
    processed = 0
    for doc in due:
        try:
            send_promotion(
                title=doc["title"],
                message=doc["message"],
                prop_id=doc.get("prop_id"),
                campaign_id=doc["campaign_id"],
                promotion_id=doc.get("promotion_id"),
            )
        except Exception as exc:  # noqa: BLE001 — transient failures retry
            retries = int(doc.get("retries", 0)) + 1
            status = (
                SCHEDULED_STATUS_ERROR
                if retries >= SCHEDULED_MAX_RETRIES
                else SCHEDULED_STATUS_PENDING
            )
            db.scheduled_promotions.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "status": status,
                        "retries": retries,
                        "last_error": str(exc)[:500],
                    }
                },
            )
            logger.exception(
                "Scheduled promotion %s failed (retry %d/%d)",
                doc["campaign_id"],
                retries,
                SCHEDULED_MAX_RETRIES,
            )
            continue
        db.scheduled_promotions.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": SCHEDULED_STATUS_SENT,
                    "sent_at": datetime.now(timezone.utc),
                }
            },
        )
        processed += 1
    return processed


def process_due_scheduled_promotions_forever(
    db,
    *,
    interval_seconds: int = 30,
) -> None:
    """Periodic background worker for the scheduled-promotions queue.

    Daemon thread (same pattern as the outbox drainer) so uvicorn shutdown
    tears it down naturally. Polls for due campaigns every
    ``interval_seconds``.
    """
    import threading

    def worker() -> None:
        logger.info(
            "Starting scheduled-promotions worker (interval=%ss)", interval_seconds
        )
        while True:
            try:
                processed = process_due_scheduled_promotions(db)
                if processed:
                    logger.info(
                        "Scheduled-promotions worker sent %d campaign(s)", processed
                    )
            except Exception:
                logger.exception(
                    "Scheduled-promotions sweep failed; will retry on next interval"
                )
            threading.Event().wait(interval_seconds)

    t = threading.Thread(target=worker, daemon=True, name="ScheduledPromotionsWorker")
    t.start()
