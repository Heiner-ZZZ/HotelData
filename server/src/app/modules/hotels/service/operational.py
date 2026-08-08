"""Gates operativos para hoteles pendientes de aprobación (Fase A).

Design: `docs/APROBACION_HOTELES_Y_PRICING.md` §4. Un hotel creado por el
onboarding público nace con ``published=false`` / ``is_operational=false``
hasta que el super admin lo aprueba en la cola
(``property_approval.approve_registration`` lo activa a True). Toda
superficie pública y toda operación por prop_id debe excluir/rechazar esos
hoteles:

- ``published == False`` → hotel pendiente o rechazado: NO visible.
- ``published`` ausente    → hotel legado (pre-gate): visible (backward
  compat — la migración de catálogo no tocó la dimensión).

``is_operational`` y ``published`` se escriben juntos (approve / onboarding);
publicamos el gate sobre ``published`` para no duplicar semánticas.
"""
from __future__ import annotations

from typing import Any

# Match de hoteles publicados: excluye SOLO los que tienen published=false
# explícito (los legados sin campo quedan incluidos).
PUBLISHED_QUERY: dict[str, Any] = {"published": {"$ne": False}}

# Prefijos que operan LEGÍTIMAMENTE sobre hoteles no operativos — el gate NO
# aplica ahí:
# - ``/api/auth/*``  → estado/edición del dueño pendiente (registration-status,
#   register-property/me).
# - ``/api/admin/property-registrations`` → cola de aprobación del super admin
#   (aprueba/rechaza EXACTAMENTE los hoteles pendientes).
OPERATIONAL_BYPASS_PREFIXES: tuple[str, ...] = (
    "/api/auth/",
    "/api/admin/property-registrations",
)


def is_operational_gate_bypassed(path: str) -> bool:
    """True cuando *path* pertenece a un flujo que opera sobre hoteles
    no operativos (estado del dueño o cola del admin)."""
    return path.startswith(OPERATIONAL_BYPASS_PREFIXES)


def non_operational_hotel(db, prop_id: int) -> dict[str, Any] | None:
    """Devuelve la fila de ``dim_hotels`` si el hotel EXISTE pero NO está
    publicado (``published=false`` explícito). Fila ausente o sin el campo
    (legado) → ``None`` (el gate no aplica; backward compat)."""
    hotel = db.dim_hotels.find_one({"prop_id": int(prop_id)}, {"published": 1})
    if hotel is not None and hotel.get("published") is False:
        return hotel
    return None


def published_prop_ids(db) -> list[int]:
    """Todos los prop_id publicados (incluye legados sin el campo)."""
    docs = db.dim_hotels.find(PUBLISHED_QUERY, {"_id": 0, "prop_id": 1})
    return [int(d["prop_id"]) for d in docs if d.get("prop_id") is not None]
