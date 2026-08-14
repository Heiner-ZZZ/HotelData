"""Guard: super_admin NO tiene permisos de huésped (sección "Cliente").

Decisión 2026-08: el administrador del sistema conserva el bypass ``*.*`` de
AUTH (``user_has_permission`` → True), pero el auto-servicio del huésped
(Buscar Hoteles / Mis Reservas / Mi Perfil — códigos ``account.*`` y
``search.*``) NO se le otorga: ni en el editor de roles, ni en el dashboard,
ni en su menú de navegación.

Invariants:
1. Los códigos de huésped siguen existiendo en el catálogo canónico
   (son otorgables al rol ``cliente``).
2. ``super_admin`` los excluye en el mapa canónico (ROLE_PERMISSION_CODES) y
   en el mapa de sync (ROLE_PERMISSIONS) — re-seedar no debe regresarlos.
3. ``cliente`` conserva los suyos.
4. La navegación por DB oculta los ítems de huésped bajo el bypass ``*.*``
   (sidebar real de super_admin) pero los muestra para códigos concretos
   (cliente).
5. El payload del editor de roles excluye los códigos de huésped para
   super_admin y marca sus ítems de navegación como Ocultos.
"""

from __future__ import annotations

from scripts.init_security_model_ga03 import (
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
    seed_navigation,
)
from scripts.sync_role_permissions import ROLE_PERMISSIONS

# Paridad exacta con GUEST_PERMISSION_CODES (src/app/security/permissions.py
# y scripts/init_security_model_ga03.py) — KEEP IN SYNC.
GUEST_CODES = frozenset({
    "account.manage",
    "account.read",
    "account.update",
    "account.bookings.read",
    "search.manage",
    "search.read",
})

GUEST_NAV_HREFS = ("/search", "/account/bookings", "/account/profile")


def test_guest_codes_remain_in_canonical_catalog() -> None:
    """Siguen en el catálogo: son otorgables al rol cliente (auto-servicio)."""
    catalog = {code for code, _ in PERMISSION_CATALOG}
    assert GUEST_CODES <= catalog


def test_super_admin_canonical_map_excludes_guest_codes() -> None:
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert not (GUEST_CODES & super_codes), (
        f"super_admin tiene permisos de huésped en ROLE_PERMISSION_CODES: "
        f"{sorted(GUEST_CODES & super_codes)}"
    )


def test_super_admin_sync_map_excludes_guest_codes() -> None:
    """Re-seedar con sync_role_permissions.py no debe regresar los códigos
    de huésped a super_admin."""
    super_codes = set(ROLE_PERMISSIONS["super_admin"])
    assert not (GUEST_CODES & super_codes), (
        f"sync_role_permissions.py regresaría permisos de huésped a super_admin: "
        f"{sorted(GUEST_CODES & super_codes)}"
    )


def test_super_admin_still_covers_staff_and_management_codes() -> None:
    """Solo se pierde el auto-servicio: todo lo operativo sigue presente."""
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert {
        "users.manage", "reservations.manage", "properties.read",
        "rooms.read", "audit.read", "revenue.read", "hotel.manage_roles",
    } <= super_codes


def test_cliente_keeps_guest_codes() -> None:
    perms = set(ROLE_PERMISSION_CODES["cliente"])
    assert {"search.read", "account.read", "account.update", "account.bookings.read"} <= perms


def test_navigation_hides_guest_items_for_superadmin_bypass(db) -> None:
    """El sidebar real de super_admin (``*.*``) no muestra el menú HUÉSPED."""
    from src.app.security.navigation import get_all_navigation_items

    seed_navigation(db["navigation"])
    items = get_all_navigation_items({"*.*"})
    by_href = {item["href"]: item for item in items}
    for href in GUEST_NAV_HREFS:
        assert href in by_href, f"Falta el ítem de navegación {href}"
        assert by_href[href]["visible"] is False, f"{href} visible bajo el bypass *.*"
    # /management/profile también exige account.read → oculto para super_admin
    assert by_href["/management/profile"]["visible"] is False
    # El resto del menú operativo sigue visible
    assert by_href["/system/users"]["visible"] is True
    assert by_href["/management/reservations"]["visible"] is True


def test_navigation_shows_guest_items_for_concrete_guest_codes(db) -> None:
    """cliente (códigos concretos, sin bypass) SÍ ve sus ítems de huésped."""
    from src.app.security.navigation import get_all_navigation_items

    seed_navigation(db["navigation"])
    items = get_all_navigation_items({"search.read", "account.read", "account.bookings.read"})
    by_href = {item["href"]: item for item in items}
    for href in GUEST_NAV_HREFS:
        assert by_href[href]["visible"] is True, f"{href} oculto para cliente"


def test_navigation_prunes_empty_guest_container_for_superadmin(db) -> None:
    """El container ``huesped`` (sin permiso propio y con TODOS sus hijos de
    auto-servicio) no debe aparecer en el sidebar de super_admin: una sección
    sin hojas visibles se poda. Para cliente sí se muestra, y los containers
    operativos con hojas visibles siguen visibles."""
    from src.app.security.navigation import get_all_navigation_items

    seed_navigation(db["navigation"])

    super_items = get_all_navigation_items({"*.*"})
    by_slug = {item["slug"]: item for item in super_items}
    assert by_slug["huesped"]["visible"] is False, (
        "sección HUÉSPED vacía (sin hojas visibles) aparece para super_admin"
    )
    # Los containers operativos con hojas visibles siguen visibles
    assert by_slug["gestion"]["visible"] is True
    assert by_slug["sistema"]["visible"] is True
    assert by_slug["propietario"]["visible"] is True

    # cliente sí ve la sección (sus hojas son visibles para él)
    client_items = get_all_navigation_items({"search.read", "account.read", "account.bookings.read"})
    client_by_slug = {item["slug"]: item for item in client_items}
    assert client_by_slug["huesped"]["visible"] is True


def test_editor_payload_excludes_guest_codes_for_super_admin(db) -> None:
    """El editor de roles muestra a super_admin sin la caja Cliente y con sus
    ítems de navegación de huésped en Oculto."""
    from src.app.modules.admin.service.roles import role_editor_payload_api

    for code, desc in PERMISSION_CATALOG:
        db.permissions.update_one(
            {"permission_code": code},
            {"$set": {"permission_code": code, "description": desc}},
            upsert=True,
        )
    db.roles.update_one(
        {"role_name": "super_admin"},
        {
            "$set": {
                "role_name": "super_admin",
                "description": "Super administrador",
                "permissions": [code for code, _ in PERMISSION_CATALOG],
            }
        },
        upsert=True,
    )
    seed_navigation(db["navigation"])

    payload = role_editor_payload_api("super_admin")
    assert payload is not None
    codes = set(payload["role"]["permission_codes"])
    assert not (GUEST_CODES & codes), (
        f"El editor otorga permisos de huésped a super_admin: {sorted(GUEST_CODES & codes)}"
    )
    by_href = {item["href"]: item for item in payload["role"]["navigation_catalog"]}
    for href in GUEST_NAV_HREFS:
        assert by_href[href]["visible"] is False, f"{href} visible en el editor de super_admin"
