"""Guard: ``properties.approve`` (cola de aprobación de hoteles) es otorgable.

El módulo ``property_approval`` (``/api/admin/property-registrations``) gatea
TODAS sus rutas con ``require_permission("properties.approve")``. El código
nace en el catálogo canónico y debe ser otorgable desde el editor de roles:
``super_admin`` (bypass ``*.*``), ``admin_sistema`` (que opera la cola) y
``gerente_hotel`` (que puede gestionar propiedades). Estos tests mantienen en
sync el catálogo canónico, los mapas de roles, el tool de sync y la BD dev.

Invariants:
1. ``properties.approve`` existe en el catálogo canónico y super_admin lo
   cubre (via ``*.*`` / la comprensión de PERMISSION_CATALOG).
2. ``admin_sistema`` y ``gerente_hotel`` lo tienen en ROLE_PERMISSION_CODES y
   en ROLE_PERMISSIONS (no-regresión: re-seedar con sync_role_permissions.py
   no debe quitárselo).
3. TODAS las rutas del módulo property_approval usan SOLO códigos del
   catálogo — concretamente ``properties.approve``.
"""

import re
from pathlib import Path

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS

APPROVE_CODE = "properties.approve"

# Roles que deben poder aprobar/rechazar la cola de registros.
APPROVE_HOLDER_ROLES = ("admin_sistema", "gerente_hotel")

ROUTES_FILE = Path(__file__).resolve().parents[1] / "src/app/modules/property_approval/routes.py"


def test_approve_code_is_in_canonical_catalog() -> None:
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert APPROVE_CODE in catalog_codes, (
        f"{APPROVE_CODE} falta en PERMISSION_CATALOG — sin catálogo, el editor "
        f"de roles no puede otorgarlo."
    )


def test_super_admin_covers_approve() -> None:
    super_codes = set(ROLE_PERMISSION_CODES["super_admin"])
    assert APPROVE_CODE in super_codes


def test_holder_roles_have_approve_in_canonical_map() -> None:
    for role in APPROVE_HOLDER_ROLES:
        perms = set(ROLE_PERMISSION_CODES.get(role, []))
        assert APPROVE_CODE in perms, (
            f"El rol {role} no tiene {APPROVE_CODE} en ROLE_PERMISSION_CODES — "
            f"sin él, un re-seed con init_security_model_ga03.py no le daría "
            f"acceso a la cola de aprobación."
        )


def test_sync_does_not_regress_approve_for_holder_roles() -> None:
    """Re-seedar con sync_role_permissions.py no debe quitarle properties.approve
    a los roles que operan la cola (ni a super_admin)."""
    for role in (*APPROVE_HOLDER_ROLES, "super_admin"):
        sync_codes = set(ROLE_PERMISSIONS.get(role, []))
        assert APPROVE_CODE in sync_codes, (
            f"sync_role_permissions.py regresaría {APPROVE_CODE} para {role} "
            f"(código faltante en ROLE_PERMISSIONS)"
        )


def test_all_property_approval_routes_use_only_catalog_codes() -> None:
    """Cada permiso que exigen las rutas de property_approval debe ser
    otorgable desde el catálogo.

    Drift guard: si una ruta nueva usa ``require_permission("properties.x")``
    sin añadir el código al catálogo, este test falla en lugar de dejar un
    permiso que ningún rol puede tener.
    """
    route_text = ROUTES_FILE.read_text(encoding="utf-8")
    required = set(re.findall(r'require_permission\("([^"]+)"\)', route_text))
    assert required, "No se encontraron require_permission en property_approval/routes.py"
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    missing = sorted(required - catalog_codes)
    assert not missing, (
        f"Rutas de property_approval exigen permisos fuera del catálogo: {missing}"
    )


def test_property_approval_routes_all_gate_on_approve() -> None:
    """Todas las rutas del módulo gatean con el mismo código: properties.approve."""
    route_text = ROUTES_FILE.read_text(encoding="utf-8")
    required = set(re.findall(r'require_permission\("([^"]+)"\)', route_text))
    assert required == {APPROVE_CODE}, (
        f"El módulo debe gatear uniformemente con {APPROVE_CODE!r}; encontrados: "
        f"{sorted(required)}"
    )
