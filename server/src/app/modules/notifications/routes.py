"""Client-facing notification endpoints — notifications for the current user."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.app.security.dependencies import require_permission
from src.database.connection import get_database

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/my")
def my_notifications_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(require_permission("account.read")),
):
    """Return notifications for the current user, filtered by their email."""
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

    total = db.notification_log.count_documents(match)
    unread = db.notification_log.count_documents({**match, "status": "sent"})

    items = list(
        db.notification_log.find(match, {"_id": 0})
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


def _type_label(nt: str) -> str:
    labels = {
        "guest_confirmed": "Reserva confirmada",
        "guest_rejected": "Reserva rechazada",
        "guest_cancelled": "Reserva cancelada",
        "guest_modified": "Reserva modificada",
        "guest_checked_in": "Check-in realizado",
        "guest_checked_out": "Check-out realizado",
        "guest_invoice_issued": "Factura emitida",
        "guest_amenity_request": "Solicitud de servicio",
        "guest_review_approved": "Reseña publicada",
        "guest_review_rejected": "Reseña rechazada",
        "guest_other": "Notificación",
        "role_permissions_changed": "Permisos del rol actualizados",
        "shift_expired": "Turno de caja vencido",
        "shift_open_long": "Turno de caja abierto por mucho tiempo",
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
