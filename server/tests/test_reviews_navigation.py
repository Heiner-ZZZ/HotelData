"""Guard: the \"Reseñas\" nav item is gated by ``reviews.read`` and the roles
that can see reviews today hold that code.

Historically ``/management/reviews`` required ``properties.read``, so
``hotel_partner``, ``gerente_hotel`` and ``recepcionista`` saw it by accident
of having ``properties.read`` — not because they were granted review access.
This migration flips the nav item to its real resource (``reviews.read``) and
explicitly grants ``reviews.read`` to those three roles so nobody loses the
menu. These tests keep the canonical catalog, the role maps, the sync tool and
the navigation catalog in sync.

Invariants:
1. The nav item href=/management/reviews requires ``reviews.read`` (never
   ``properties.read``).
2. ``reviews.read`` exists in the canonical catalog and super_admin covers it.
3. The three roles that see reviews (hotel_partner, gerente_hotel,
   recepcionista) hold ``reviews.read`` in both the canonical role map and the
   sync map (no-regression: re-seeding with sync_role_permissions.py must not
   strip the code).
"""

from scripts.init_security_model_ga03 import (
    NAVIGATION_CATALOG,
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
)
from scripts.sync_role_permissions import ROLE_PERMISSIONS

REVIEWS_NAV_HREF = "/management/reviews"

REVIEW_VIEWER_ROLES = ("hotel_partner", "gerente_hotel", "recepcionista")


def _reviews_nav_item() -> dict:
    item = next((i for i in NAVIGATION_CATALOG if i.get("href") == REVIEWS_NAV_HREF), None)
    assert item is not None, f"Falta el ítem de navegación Reseñas ({REVIEWS_NAV_HREF}) en NAVIGATION_CATALOG"
    return item


def test_reviews_nav_item_requires_reviews_read() -> None:
    item = _reviews_nav_item()
    assert item["required_permission"] == "reviews.read", (
        f"El ítem Reseñas exige {item['required_permission']!r}; debe ser 'reviews.read' "
        f"para que la vista quede ligada a su propio recurso."
    )


def test_reviews_nav_item_does_not_require_properties_read() -> None:
    item = _reviews_nav_item()
    assert item["required_permission"] != "properties.read"


def test_reviews_read_is_in_canonical_catalog() -> None:
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert "reviews.read" in catalog_codes


def test_super_admin_covers_reviews_read() -> None:
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert "reviews.read" in super_codes


def test_review_viewer_roles_have_reviews_read_in_canonical_map() -> None:
    """Los roles que hoy ven reseñas deben tener reviews.read en el catálogo
    canónico — si no, al cambiar el ítem nav perderían el menú."""
    for role in REVIEW_VIEWER_ROLES:
        perms = set(ROLE_PERMISSION_CODES.get(role, []))
        assert "reviews.read" in perms, (
            f"El rol {role} ve reseñas (hoy vía properties.read) pero no tiene "
            f"reviews.read en ROLE_PERMISSION_CODES"
        )


def test_sync_does_not_regress_reviews_read_for_viewer_roles() -> None:
    """Re-seedar con sync_role_permissions.py no debe quitarle reviews.read a
    los roles que ven reseñas (ni a super_admin)."""
    for role in (*REVIEW_VIEWER_ROLES, "super_admin"):
        sync_codes = set(ROLE_PERMISSIONS.get(role, []))
        assert "reviews.read" in sync_codes, (
            f"sync_role_permissions.py regresaría reviews.read para {role} "
            f"(código faltante en ROLE_PERMISSIONS)"
        )


def test_sync_map_matches_canonical_for_recepcionista() -> None:
    """Drift guard: la lista del sync map para recepcionista debe ser EXACTA-
    MENTE la del catálogo canónico — si divergen, un sync posterior haría
    $set y borraría códigos (p. ej. reviews.read) o personalizaciones."""
    canonical = ROLE_PERMISSION_CODES.get("recepcionista")
    sync = ROLE_PERMISSIONS.get("recepcionista")
    assert canonical is not None, "Falta recepcionista en ROLE_PERMISSION_CODES"
    assert sync is not None, "Falta recepcionista en ROLE_PERMISSIONS (sync)"
    assert sorted(sync) == sorted(canonical), (
        f"Sync y canónico divergen para recepcionista: \n"
        f"  solo en sync: {sorted(set(sync) - set(canonical))} \n"
        f"  solo en canónico: {sorted(set(canonical) - set(sync))}"
    )
