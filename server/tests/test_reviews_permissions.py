"""Guard: the ``reviews.*`` permission resource is grantable everywhere it is
referenced.

``PATCH/DELETE /api/reviews/{id}`` enforce ``reviews.moderate`` (moderate +
delete). Before this resource existed in the catalog, no non-super_admin role
could moderate reviews (403), even though the UI showed the button to
``marketing_hotelero``. These tests keep the canonical catalog, the role maps
and the sync tool in sync so the permission is grantable from the role editor
and ``marketing_hotelero`` can actually moderate.

The read-dependency invariant: the role editor's save path
(``role_update.py``) refuses to grant a non-read action whose ``<resource>.read``
does not exist in the catalog — hence ``reviews.read`` MUST ship together with
``reviews.moderate``.
"""

import re
from pathlib import Path

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS

REVIEWS_CODES = {"reviews.read", "reviews.moderate"}

ROUTES_FILE = Path(__file__).resolve().parents[1] / "src/app/modules/reviews/routes.py"


def test_reviews_codes_are_in_canonical_catalog() -> None:
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    missing = sorted(REVIEWS_CODES - catalog_codes)
    assert not missing, f"Faltan códigos reviews.* en el catálogo canónico: {missing}"


def test_reviews_moderate_has_read_dependency_in_catalog() -> None:
    """El editor de roles exige reviews.read para poder otorgar reviews.moderate."""
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert "reviews.read" in catalog_codes
    assert "reviews.moderate" in catalog_codes


def test_marketing_hotelero_can_moderate_reviews() -> None:
    """marketing_hotelero (canónico) debe poder leer y moderar reseñas."""
    perms = set(ROLE_PERMISSION_CODES.get("marketing_hotelero", []))
    missing = sorted(REVIEWS_CODES - perms)
    assert not missing, f"marketing_hotelero no tiene códigos reviews.*: {missing}"


def test_super_admin_covers_reviews() -> None:
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert REVIEWS_CODES <= super_codes


def test_sync_does_not_regress_reviews_for_marketing_hotelero() -> None:
    """Re-seedar con sync_role_permissions.py no debe quitarle reviews.* a
    marketing_hotelero (ni a super_admin)."""
    for role in ("marketing_hotelero", "super_admin"):
        sync_codes = set(ROLE_PERMISSIONS.get(role, []))
        missing = sorted(REVIEWS_CODES - sync_codes)
        assert not missing, (
            f"sync_role_permissions.py regresaría reviews.* para {role} "
            f"(códigos faltantes: {missing})"
        )


def test_all_reviews_api_required_codes_exist_in_catalog() -> None:
    """Cada permiso que exigen las rutas del módulo reviews debe ser otorgable.

    Drift guard: si una ruta nueva usa ``require_permission("reviews.x")`` sin
    añadir el código al catálogo, este test falla en lugar de dejar un permiso
    que ningún rol puede tener.
    """
    route_text = ROUTES_FILE.read_text(encoding="utf-8")
    required = set(
        re.findall(r'require_(?:prop_)?permission\("([^"]+)"\)', route_text)
    )
    assert required, "No se encontraron require_permission en reviews/routes.py"
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    missing = sorted(required - catalog_codes)
    assert not missing, f"Rutas de reviews exigen permisos fuera del catálogo: {missing}"
