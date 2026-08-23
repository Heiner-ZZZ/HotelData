"""Fase 5 (2026-08): el template canónico de ``gerente_hotel`` cubre las
OPERACIONES por-hotel que el gerente ejecuta en SU hotel.

``ROLE_PERMISSION_CODES`` alimenta tanto el rol global (``$set``) como los
clones de ``hotel_roles`` (``$addToSet`` aditivo). Los gates
``require_prop_permission`` de amenities, tarifas y habitaciones exigen estos
códigos en el HOTEL_ROLE del gerente. Sin ellos el gerente puede VER
(``rooms.read``/``rates.read``) pero no OPERAR en su propio hotel: guardar
amenities, crear/editar planes de tarifa y crear/editar tipos de habitación
devuelven 403 — el hueco que esta batería cierra.

RED: falla hoy; el template no otorga ninguno de estos códigos.
"""
from __future__ import annotations

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES

# Códigos que los gates prop de los módulos operativos del gerente exigen en
# el hotel_role (verificado contra partner/routes/{amenities,rates,rooms}.py).
_REQUIRED_BY_PROP_GATES = {
    "amenities.read", "amenities.manage",  # CRUD amenities + special-requests
    "rates.manage", "rates.update",  # planes de tarifa + calendario
    "rooms.manage", "rooms.update",  # CRUD tipos de habitación + fotos
}


def test_gerente_template_covers_hotel_operations() -> None:
    """El gerente opera SU hotel: el template debe portar los códigos por-hotel."""
    granted = set(ROLE_PERMISSION_CODES["gerente_hotel"])
    missing = sorted(_REQUIRED_BY_PROP_GATES - granted)
    assert not missing, (
        "el template gerente_hotel no otorga códigos que los gates por-hotel "
        f"exigen para operar SU hotel: {missing}"
    )


def test_gerente_hotel_role_operations_granted() -> None:
    """Sinergia con el sync de hotel_roles: los códigos de operación por-hotel
    deben existir en el catálogo canónico (los clones los reciben por
    ``$addToSet``; un código que no está en PERMISSION_CATALOG no puede
    sembrarse)."""
    catalog = {code for code, _ in PERMISSION_CATALOG}
    unknown = sorted(_REQUIRED_BY_PROP_GATES - catalog)
    assert not unknown, f"códigos sin catálogo canónico: {unknown}"
