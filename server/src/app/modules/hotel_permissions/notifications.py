"""Bandeja de notificaciones para la Fase 2 (per-hotel RBAC).

Escribe en ``notification_log`` — la misma colección que sirve
``GET /api/notifications/my`` — una fila por cada miembro asignado a un
``hotel_role`` cuyos permisos acaban de modificarse.

Sigue el patrón best-effort del resto de notificaciones del proyecto
(``amenities/notifications.py``, ``reviews/service/notifications.py``): un
fallo de notificación NUNCA debe revertir la mutación de permisos que el
admin acaba de hacer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

NOTIFICATION_TYPE = "role_permissions_changed"

MESSAGE_TEMPLATE = "Tus permisos en {hotel_label} cambiaron — revisa el historial"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hotel_label(db, prop_id: int) -> str:
    hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"display_name": 1, "hotel_name": 1},
    )
    return (
        (hotel or {}).get("display_name")
        or (hotel or {}).get("hotel_name")
        or f"Propiedad #{prop_id}"
    )


def notify_role_permissions_changed(
    db,
    *,
    prop_id: int,
    role_id: Any,
    role_name: str,
) -> None:
    """Insertar una notificación por miembro asignado a ``role_id`` en ``prop_id``.

    Solo los miembros con ``role_assignments`` para este rol/hotel reciben la
    notificación (el personal sin asignación no). Best-effort: nunca lanza.
    """
    try:
        message = MESSAGE_TEMPLATE.format(hotel_label=_hotel_label(db, prop_id))
        assignments = list(
            db.role_assignments.find(
                {"prop_id": prop_id, "role_id": role_id},
                {"user_id": 1},
            )
        )
        if not assignments:
            return
        user_ids = [a["user_id"] for a in assignments]

        written = 0
        # Solo miembros ACTIVOS: una cuenta desactivada tras la asignación no
        # puede leer la bandeja — no tiene sentido escribirle.
        for user in db.users.find(
            {"_id": {"$in": user_ids}, "is_active": True},
            {"email": 1, "display_name": 1, "username": 1},
        ):
            email = (user.get("email") or "").strip()
            if not email:
                continue
            db.notification_log.insert_one(
                {
                    "notification_type": NOTIFICATION_TYPE,
                    "recipient_email": email,
                    "recipient_name": user.get("display_name") or user.get("username", ""),
                    "prop_id": prop_id,
                    "role_id": str(role_id),
                    "role_name": role_name,
                    "status": "sent",
                    "message": message,
                    "created_at": _now(),
                }
            )
            written += 1
        logger.info(
            "role_permissions_changed notifications written=%d prop_id=%s role_id=%s",
            written, prop_id, role_id,
        )
    except Exception:
        logger.exception(
            "Failed to write role_permissions_changed notifications prop_id=%s role_id=%s",
            prop_id, role_id,
        )
