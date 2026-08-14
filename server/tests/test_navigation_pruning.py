"""T12 — Pruning top-down del árbol de navegación (payload por permisos).

``get_all_navigation_items()`` computa ``visible`` de arriba hacia abajo: un
container oculto oculta a sus hijos. Invariantes de negocio:

1. Un rol OPERATIVO (códigos de módulo, sin ningún ``reports.*``) NO recibe el
   container "Informes" ni sus hojas de dashboard — el menú no puede
   "desbloquearse" desde devtools porque el backend nunca los envía.
2. El container "Informes" exige el código de área ``reports.tactical.read``:
   un código fino sin el área NO basta para ver el container ni la hoja.
3. Con el área + el código fino, la hoja SÍ se recibe (pruning no sobre-poda).
"""

from __future__ import annotations

import pytest

from scripts.init_security_model_ga03 import seed_navigation
from src.app.security.navigation import get_all_navigation_items

# Códigos operativos de módulo, SIN ningún reports.*
OPERATIONAL_CODES = {
    "rates.read",
    "reservations.read",
    "housekeeping.read",
    "billing.read",
    "maintenance.read",
    "charges.read",
    "inventory.read",
    "properties.read",
}

INFORMES_CONTAINERS = (
    "gestion.reservas.informes",
    "gestion.housekeeping.informes",
    "gestion.billing.informes",
)

INFORMES_LEAVES = (
    "gestion.reservas.informes.adr",
    "gestion.reservas.informes.calendario",
    "gestion.reservas.informes.solicitudes",
    "gestion.housekeeping.informes.dashboard",
    "gestion.housekeeping.informes.operaciones",
    "gestion.housekeeping.informes.matriz",
    "gestion.billing.informes.facturas",
    "gestion.billing.informes.pagos",
)


@pytest.fixture
def seeded_nav(db):
    seed_navigation(db["navigation"])


def test_operational_role_does_not_receive_informes_container_or_children(db, seeded_nav):
    items = get_all_navigation_items(OPERATIONAL_CODES)
    by_slug = {i["slug"]: i for i in items}

    for slug in INFORMES_CONTAINERS + INFORMES_LEAVES:
        assert by_slug[slug]["visible"] is False, f"{slug} visible para rol operativo"

    # Los ítems operativos SÍ siguen visibles (el pruning no rompe el menú).
    assert by_slug["gestion.reservas.tarifas"]["visible"] is True
    assert by_slug["gestion.housekeeping.mantenimiento"]["visible"] is True


def test_fine_codes_without_tactical_area_still_hide_container(db, seeded_nav):
    """El código fino NO basta: el container exige reports.tactical.read."""
    items = get_all_navigation_items({"reports.rates.adr.read"})
    by_slug = {i["slug"]: i for i in items}

    assert by_slug["gestion.reservas.informes"]["visible"] is False
    assert by_slug["gestion.reservas.informes.adr"]["visible"] is False


def test_tactical_area_plus_fine_code_receives_leaf(db, seeded_nav):
    """Área táctica + código fino ⇒ hoja visible; hoja sin código fino queda oculta."""
    codes = {
        "reservations.read",  # ancestro: gestion.reservas
        "reports.tactical.read",
        "reports.rates.adr.read",
        "reports.rates.calendar.read",
    }
    items = get_all_navigation_items(codes)
    by_slug = {i["slug"]: i for i in items}

    assert by_slug["gestion.reservas.informes"]["visible"] is True
    assert by_slug["gestion.reservas.informes.adr"]["visible"] is True
    assert by_slug["gestion.reservas.informes.calendario"]["visible"] is True
    # hoja sin su código fino (solicitudes) oculta
    assert by_slug["gestion.reservas.informes.solicitudes"]["visible"] is False
    # otro dominio sin su área/código queda oculto
    assert by_slug["gestion.housekeeping.informes"]["visible"] is False
