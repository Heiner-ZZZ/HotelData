"""Guard: the "Mis Reservas" nav item is gated by its own guest permission
(``account.bookings.read``) instead of the staff permission ``reservations.read``.

Historically ``/account/bookings`` required ``reservations.read``, so the
Cliente box in the role editor could not control it — the toggle lived in
"Gestión · Reservas" (CRS). This migration introduces the dedicated guest code
``account.bookings.read`` and flips the nav item to it, so "Mis Reservas" is
grantable from the Cliente box. ``cliente`` keeps ``reservations.read`` because
the guest bookings API still enforces ``reservations.*``.

Invariants:
1. The nav item href=/account/bookings requires ``account.bookings.read``
   (never ``reservations.read``).
2. ``account.bookings.read`` exists in the canonical catalog and super_admin
   covers it.
3. ``cliente`` holds ``account.bookings.read`` in both the canonical role map
   and the sync map (no-regression: re-seeding with sync_role_permissions.py
   must not strip the code).
4. Staff roles (``revenue_manager``, ``concierge``) do NOT hold the guest code:
   "Mis Reservas" es auto-servicio del huésped, no del personal (decisión
   2026-08 — el ítem HUÉSPED no debe aparecer en sus menús).
"""

from scripts.init_security_model_ga03 import (
    NAVIGATION_CATALOG,
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
)
from scripts.sync_role_permissions import ROLE_PERMISSIONS

BOOKINGS_NAV_HREF = "/account/bookings"
BOOKINGS_CODE = "account.bookings.read"


def _bookings_nav_item() -> dict:
    item = next((i for i in NAVIGATION_CATALOG if i.get("href") == BOOKINGS_NAV_HREF), None)
    assert item is not None, f"Falta el ítem de navegación Mis Reservas ({BOOKINGS_NAV_HREF}) en NAVIGATION_CATALOG"
    return item


def test_bookings_nav_item_requires_account_bookings_read() -> None:
    item = _bookings_nav_item()
    assert item["required_permission"] == BOOKINGS_CODE, (
        f"El ítem Mis Reservas exige {item['required_permission']!r}; debe ser "
        f"{BOOKINGS_CODE!r} para que la vista quede ligada a su propio recurso de huésped."
    )


def test_bookings_nav_item_does_not_require_reservations_read() -> None:
    item = _bookings_nav_item()
    assert item["required_permission"] != "reservations.read"


def test_account_bookings_read_is_in_canonical_catalog() -> None:
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert BOOKINGS_CODE in catalog_codes


def test_super_admin_covers_account_bookings_read() -> None:
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert BOOKINGS_CODE in super_codes


def test_cliente_has_bookings_code_in_canonical_map() -> None:
    perms = set(ROLE_PERMISSION_CODES.get("cliente", []))
    assert BOOKINGS_CODE in perms, (
        f"cliente no tiene {BOOKINGS_CODE} en ROLE_PERMISSION_CODES — sin él, "
        f"el huésped no vería el ítem Mis Reservas tras el re-seed canónico."
    )


def test_cliente_keeps_reservations_read_for_the_api() -> None:
    """El API del huésped (/account/bookings) sigue gateando con
    reservations.read: no quitarlo al migrar el ítem de navegación."""
    perms = set(ROLE_PERMISSION_CODES.get("cliente", []))
    assert "reservations.read" in perms


def test_staff_roles_do_not_hold_the_guest_code() -> None:
    """"Mis Reservas" es auto-servicio del huésped: revenue_manager y concierge
    NO deben tener account.bookings.read (su menú HUÉSPED queda sin el ítem)."""
    for role in ("revenue_manager", "concierge"):
        perms = set(ROLE_PERMISSION_CODES.get(role, []))
        assert BOOKINGS_CODE not in perms, f"El rol staff {role} tiene el código de huésped {BOOKINGS_CODE}"


def test_sync_does_not_regress_bookings_code() -> None:
    """Re-seedar con sync_role_permissions.py no debe quitarle
    account.bookings.read a los roles gestionados por el sync tool
    (cliente y super_admin; los roles staff no lo gestionan ni lo tienen)."""
    for role in ("cliente", "super_admin"):
        sync_codes = set(ROLE_PERMISSIONS.get(role, []))
        assert BOOKINGS_CODE in sync_codes, (
            f"sync_role_permissions.py regresaría {BOOKINGS_CODE} para {role} "
            f"(código faltante en ROLE_PERMISSIONS)"
        )


def test_sync_map_does_not_grant_staff_the_guest_code() -> None:
    """El sync map tampoco debe otorgar el código a revenue_manager (el único
    rol staff gestionado por el sync tool que lo llegó a tener)."""
    sync_codes = set(ROLE_PERMISSIONS.get("revenue_manager", []))
    assert BOOKINGS_CODE not in sync_codes
