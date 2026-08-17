"""Owner registration-status endpoints (UX-1 backend).

Spec: `docs/EXPERIENCIA_DUENO_PENDIENTE.md` §2.1 (wire shape), §3.4 (edición).

- ``GET /api/auth/registration-status``  → contract of the pending-owner
  screen: approval status, declared data, suggested pricing band and the
  timeline read from ``audit_log`` (entity_type="hotel_registration").
- ``PATCH /api/auth/register-property/me`` → owner edits the declared
  property data while pending (in-place) or after changes_requested
  (resubmits → back to pending_approval; suggested band recalculated).

Both are reachable by non-approved owners via the middleware approval
allowlist (``security/approval.py``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from src.app.core.outbox import enqueue_audit_log
from src.app.modules.auth.routes.register_property import (
    _validate_property_edit_payload,
)
from src.app.modules.property_approval.pricing import suggested_band_for
from src.app.modules.subscriptions.payment_methods import available_payment_methods
from src.app.modules.subscriptions.service import INITIAL_GRACE_DAYS
from src.app.security.dependencies import require_login
from src.app.security.session import utc_now
from src.database.connection import get_database

api_router = APIRouter(prefix="/api/auth", tags=["auth-registration-status"])

PENDING = "pending_approval"
CHANGES_REQUESTED = "changes_requested"

# Fallback detail when the audit entry has no summary.
_EVENT_DETAILS: dict[str, str] = {
    "submitted": "Registro recibido",
    "resubmitted": "Registro reenviado",
    "changes_requested": "Cambios solicitados por el administrador",
    "rejected": "Rechazado por el administrador",
    "approved": "Aprobado",
}


def _build_timeline(db, prop_id: int, hotel: dict[str, Any]) -> list[dict[str, Any]]:
    """Timeline from audit_log (entity_type=hotel_registration), chronological.

    Pre-audit registrations (no entries) get a synthesized "submitted" event
    so the screen never renders an empty history.
    """
    entries = list(
        db.audit_log.find(
            {"entity_type": "hotel_registration", "entity_id": str(prop_id)},
            {"_id": 0, "timestamp": 1, "action": 1, "summary": 1},
        ).sort("timestamp", 1)
    )
    if not entries:
        return [
            {
                "event": "submitted",
                "at": hotel.get("created_at"),
                "detail": _EVENT_DETAILS["submitted"],
            }
        ]
    # Contrato del doc §2.1: detail es el label humano del evento; el texto
    # rico (reason/feedback) viaja en los campos de nivel superior.
    return [
        {
            "event": e.get("action", ""),
            "at": e.get("timestamp"),
            "detail": _EVENT_DETAILS.get(e.get("action", "")) or e.get("summary") or "",
        }
        for e in entries
    ]


@api_router.get("/registration-status")
def registration_status(current_user: dict = Depends(require_login)):
    """Contract of the pending-owner screen (docs §2.1)."""
    db = get_database()
    user = current_user
    hotel = db.dim_hotels.find_one({"owner_user_id": user["_id"]})
    if not hotel:
        raise HTTPException(
            status_code=404,
            detail="No hay un registro de alojamiento asociado a esta cuenta.",
        )
    approval_status = hotel.get("approval_status") or user.get("approval_status") or PENDING
    return {
        "approval_status": approval_status,
        "rejected_reason": hotel.get("rejected_reason"),
        "feedback": hotel.get("feedback"),
        "submitted_at": hotel.get("created_at"),
        "status_changed_at": hotel.get("approval_status_changed_at"),
        "property": {
            "name": hotel.get("hotel_name") or hotel.get("display_name") or "",
            "type": hotel.get("property_type", ""),
            "city": hotel.get("city", ""),
            "country": hotel.get("display_country_label", ""),
            "total_rooms": hotel.get("total_rooms_declared", 0),
            "currency": hotel.get("currency", ""),
            "contact_phone": hotel.get("contact_phone", ""),
        },
        "suggested_band": suggested_band_for(db, hotel.get("total_rooms_declared", 0)),
        # Bloque de pago (Fase 3 UI): la pantalla del dueño muestra el
        # vencimiento informativo (gracia inicial tras la aprobación) y los
        # métodos de pago manuales del catálogo (sin pasarela bancaria).
        "initial_grace_days": INITIAL_GRACE_DAYS,
        "payment_methods": [
            {k: v for k, v in m.items() if k != "_id"}
            for m in available_payment_methods(db)
        ],
        "timeline": _build_timeline(db, hotel.get("prop_id"), hotel),
    }


@api_router.patch("/register-property/me")
def patch_register_property_me(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Owner edits the declared property data (pending / changes_requested)."""
    db = get_database()
    user = current_user
    approval_status = user.get("approval_status") or "approved"
    if approval_status not in (PENDING, CHANGES_REQUESTED):
        raise HTTPException(
            status_code=409,
            detail=(
                "Tu registro ya no admite edición de datos "
                f"(estado actual: {approval_status})."
            ),
        )

    hotel = db.dim_hotels.find_one({"owner_user_id": user["_id"]})
    if not hotel:
        raise HTTPException(
            status_code=404,
            detail="No hay un registro de alojamiento asociado a esta cuenta.",
        )

    clean = _validate_property_edit_payload(payload)
    now = utc_now()

    set_fields: dict[str, Any] = {
        "hotel_name": clean["property_name"],
        "display_name": clean["property_name"],
        "property_type": clean["property_type"],
        "contact_phone": clean["contact_phone"],
        "city": clean["city"],
        "total_rooms_declared": clean["total_rooms"],
        "description": clean["description"],
        "updated_at": now,
    }
    # Semántica por estado (docs §3.4):
    # - pending_approval → actualiza in situ, el estado no cambia.
    # - changes_requested → resubmite: vuelve a pending_approval.
    resubmitting = approval_status == CHANGES_REQUESTED
    if resubmitting:
        set_fields["approval_status"] = PENDING
        set_fields["approval_status_changed_at"] = now

    db.dim_hotels.update_one({"_id": hotel["_id"]}, {"$set": set_fields})
    if resubmitting:
        db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "approval_status": PENDING,
                    "approval_status_changed_at": now,
                    "updated_at": now,
                }
            },
        )

    action = "resubmitted" if resubmitting else "edited"
    enqueue_audit_log(
        db,
        {
            "timestamp": now,
            "prop_id": int(hotel.get("prop_id", 0)),
            "entity_type": "hotel_registration",
            "entity_id": str(hotel.get("prop_id", "")),
            "action": action,
            "summary": (
                f"Registro de «{clean['property_name']}» "
                f"{'reenviado tras cambios' if resubmitting else 'actualizado por el dueño'} "
                f"({clean['total_rooms']} habitaciones)."
            ),
            "changed_by": user.get("username", "owner"),
            "diff": {
                "total_rooms": {
                    "old": hotel.get("total_rooms_declared"),
                    "new": clean["total_rooms"],
                },
                "property_name": {
                    "old": hotel.get("hotel_name"),
                    "new": clean["property_name"],
                },
            },
        },
    )

    return {
        "ok": True,
        "approval_status": PENDING if resubmitting else approval_status,
        "suggested_band": suggested_band_for(db, clean["total_rooms"]),
        "message": (
            "Datos actualizados y registro reenviado para revisión."
            if resubmitting
            else "Datos del registro actualizados."
        ),
    }
