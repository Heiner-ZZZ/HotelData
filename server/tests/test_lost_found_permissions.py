"""Guard: the ``lost-found.*`` permission resource is grantable everywhere it
is referenced.

The "Lost & Found" navigation item (``/management/lost-and-found``) requires
``lost-found.read``. The lost_and_found API enforces ``lost-found.*``. These
tests keep the canonical catalog, the role maps and the navigation catalog in
sync so the permission is grantable from the role editor and super_admin sees
every nav item as visible.
"""

from scripts.init_security_model_ga03 import (
    NAVIGATION_CATALOG,
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
)

LOST_FOUND_CODES = {
    "lost-found.manage",
    "lost-found.create",
    "lost-found.read",
    "lost-found.update",
    "lost-found.delete",
}


def test_lost_found_codes_are_in_canonical_catalog() -> None:
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    missing = sorted(LOST_FOUND_CODES - catalog_codes)
    assert not missing, f"Faltan códigos lost-found.* en el catálogo canónico: {missing}"


def test_lost_found_nav_item_uses_catalog_code() -> None:
    item = next((i for i in NAVIGATION_CATALOG if i.get("href") == "/management/lost-and-found"), None)
    assert item is not None, "Falta el ítem de navegación Lost & Found en NAVIGATION_CATALOG"
    assert item["permission_code"] in LOST_FOUND_CODES


def test_roles_with_lost_and_found_access_have_the_codes() -> None:
    # housekeeping y maintenance gestionaban lost & found vía housekeeping.*;
    # al migrar el API a lost-found.* deben conservar el acceso equivalente.
    for role in ("housekeeping", "maintenance"):
        perms = set(ROLE_PERMISSION_CODES.get(role, []))
        assert "lost-found.read" in perms, f"El rol {role} perdió lost-found.read"


def test_super_admin_covers_lost_found() -> None:
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert LOST_FOUND_CODES <= super_codes
