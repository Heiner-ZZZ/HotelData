"""User search — find registered GUESTS for fast guest data prefill."""

from __future__ import annotations

import re
from typing import Any

from pymongo import ASCENDING

# Roles considerados huéspedes para el prefill de recepción. El rol canónico
# es ``cliente``; se toleran variantes legacy (huesped/huésped) por robustez.
GUEST_ROLES: tuple[str, ...] = ("cliente", "huesped", "huésped")


def search_users(
    q: str,
    limit: int = 10,
    db=None,
) -> list[dict[str, Any]]:
    """Search registered GUESTS by name or email for quick guest data prefill.

    Solo devuelve usuarios con rol de huésped (``cliente``); el staff y los
    roles de plataforma quedan fuera — el autocompletado de recepción no debe
    sugerir empleados ni admins. La cédula viaja como ``cedula`` tomada de
    ``id_document_number`` (campo real de la cuenta; ``cedula`` legacy suele
    estar vacío).
    """
    regex = {"$regex": re.escape(q), "$options": "i"}
    users = list(
        db.users.find(
            {
                "primary_role": {"$in": list(GUEST_ROLES)},
                "$or": [{"display_name": regex}, {"email": regex}],
            },
            {
                "_id": 0,
                "display_name": 1,
                "email": 1,
                "phone": 1,
                "cedula": 1,
                "id_document_number": 1,
                "id_document_type": 1,
            },
        )
        .sort([("display_name", ASCENDING)])
        .limit(limit)
    )
    return [
        {
            "name": u.get("display_name", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone", ""),
            "cedula": u.get("id_document_number") or u.get("cedula", ""),
            "document_type": u.get("id_document_type", ""),
        }
        for u in users
    ]
