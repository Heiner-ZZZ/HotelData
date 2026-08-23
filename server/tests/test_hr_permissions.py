"""Invariante del desglose granular HR (2026-08).

Antes el módulo HR era un solo recurso ``hr.*`` (manage/create/read/update/
delete) para 4 interfaces distintas (Mi Portal, Directorio, Onboarding,
Turnos). Ahora cada interfaz tiene su permiso granular:

  - ``hr.portal.read``        → Mi Portal (auto-servicio del empleado)
  - ``hr.directory.read``     → Directorio: ver empleados/departamentos/documentos
  - ``hr.directory.manage``   → Directorio: crear/editar/eliminar
  - ``hr.onboarding.create``  → Onboarding: crear empleados + transferir permisos
  - ``hr.shifts.read``        → Turnos: ver
  - ``hr.shifts.manage``      → Turnos: crear/editar/eliminar/check-in/check-out

Invariantes:
  1. Cada ruta de ``hr/routes.py`` exige un código EXISTENTE en el
     ``PERMISSION_CATALOG`` canónico.
  2. Cada ruta usa el código GRANULAR correcto para su interfaz (espejo del
     mapeo de abajo) — si alguien cambia un guard a un código equivocado o
     reintroduce ``hr.read`` genérico en una ruta de interfaz, este test falla.
  3. Los ítems de navegación RRHH apuntan a los códigos granulares.
  4. Los roles con ``hr.*`` reciben los grants granulares equivalentes.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Ruta → código(s) granular(es) esperado(s). Clave: (método, ruta).
# Una tupla de 1 elemento = require_permission exacto; de 2+ =
# require_any_permission (cualquiera de ellos).
EXPECTED_ROUTE_PERMISSIONS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    # Valor: (dependency, códigos). require_prop_permission = gate con
    # contexto de hotel (Fase 1 RBAC por hotel — rol_assignments → hotel_roles).
    ("GET", "/dashboard"): ("require_permission", ("hr.read",)),  # landing RRHH (umbrella)
    # ── Mi Portal ──
    ("GET", "/my-portal"): ("require_permission", ("hr.portal.read",)),
    # Auto-servicio del empleado: el payload se deriva del propio user_id,
    # sin exposición cross-hotel → gate global basta.
    ("GET", "/portal/{employee_id}"): ("require_prop_permission", ("hr.portal.read",)),
    # Portal de un empleado CONCRETO: feature por-hotel → exige prop_id
    # (query) + rol del hotel (deny-by-default) + pertenencia del empleado
    # al hotel (404 cross-hotel). Fix B 2026-08.
    ("GET", "/portal/{employee_id}/tasks"): ("require_prop_permission", ("hr.portal.read",)),
    # ── Directorio ──
    ("GET", ""): ("require_permission", ("hr.directory.read",)),
    ("GET", "/{employee_id}"): ("require_permission", ("hr.directory.read",)),
    ("GET", "/{employee_id}/attendance"): ("require_permission", ("hr.directory.read",)),
    ("GET", "/departments"): ("require_permission", ("hr.directory.read",)),
    ("GET", "/documents"): ("require_permission", ("hr.directory.read",)),
    ("GET", "/documents/{document_id}"): ("require_permission", ("hr.directory.read",)),
    ("POST", "/departments"): ("require_permission", ("hr.directory.manage",)),
    ("POST", "/documents"): ("require_permission", ("hr.directory.manage",)),
    ("DELETE", "/documents/{document_id}"): ("require_permission", ("hr.directory.manage",)),
    ("PUT", "/{employee_id}"): ("require_permission", ("hr.directory.manage",)),
    ("DELETE", "/{employee_id}"): ("require_permission", ("hr.directory.manage",)),
    # ── Onboarding ──
    ("POST", ""): ("require_permission", ("hr.onboarding.create",)),
    ("GET", "/replacement-candidates"): ("require_permission", ("hr.onboarding.create",)),
    # ── Turnos ──
    ("GET", "/shifts"): ("require_permission", ("hr.shifts.read",)),
    ("POST", "/shifts"): ("require_permission", ("hr.shifts.manage",)),
    ("PUT", "/shifts/{shift_id}"): ("require_permission", ("hr.shifts.manage",)),
    ("DELETE", "/shifts/{shift_id}"): ("require_permission", ("hr.shifts.manage",)),
    # Check-in/out: el gerente los registra (shifts.manage) PERO el
    # auto-servicio del Mi Portal también (portal.read) — el empleado
    # registra su propia asistencia. require_any_prop_permission (Fase 1
    # RBAC por hotel): prop_id obligatorio (query), deny-by-default sin
    # role_assignment y 404 si el turno no pertenece al hotel pedido.
    ("POST", "/shifts/{shift_id}/check-in"): ("require_any_prop_permission", ("hr.shifts.manage", "hr.portal.read")),
    ("POST", "/shifts/{shift_id}/check-out"): ("require_any_prop_permission", ("hr.shifts.manage", "hr.portal.read")),
}

GRANULAR_CODES = sorted(
    {
        "hr.portal.read",
        "hr.directory.read",
        "hr.directory.manage",
        "hr.onboarding.create",
        "hr.shifts.read",
        "hr.shifts.manage",
    }
)

# Roles con hr.* → grants granulares equivalentes (paridad de acceso).
ROLE_HR_GRANTS: dict[str, list[str]] = {
    "admin_sistema": GRANULAR_CODES,
    "gerente_hotel": GRANULAR_CODES,
    "maintenance": ["hr.portal.read", "hr.directory.read"],
    "recepcionista": ["hr.portal.read", "hr.directory.read"],
    "housekeeping": ["hr.portal.read", "hr.directory.read"],
    "concierge": ["hr.portal.read", "hr.directory.read"],
}


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, SERVER_ROOT / rel)
    assert spec and spec.loader, f"no se pudo cargar {rel}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canon():
    return _load("init_security_model_ga03_hr_audit", "scripts/init_security_model_ga03.py")


def _route_permissions() -> dict[tuple[str, str], tuple[str, tuple[str, ...]]]:
    """Parse de hr/routes.py: decorador @api_router.<method>("<path>") seguido
    del primer Depends(require_permission(...)) / require_any_permission(...) /
    require_prop_permission(...) en la firma de la función. Devuelve
    (dependency, tupla de códigos exigidos)."""
    text = (SERVER_ROOT / "src/app/modules/hr/routes.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@api_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
    perm_re = re.compile(r"Depends\((require_any_prop_permission|require_any_permission|require_permission|require_prop_permission)\((.*?)\)\)")
    mapping: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {}
    current: tuple[str, str] | None = None
    for line in text.splitlines():
        m = route_re.search(line)
        if m:
            current = (m.group(1).upper(), m.group(2))
            continue
        p = perm_re.search(line)
        if p and current is not None and current not in mapping:
            codes = tuple(re.findall(r'"([^"]+)"', p.group(2)))
            mapping[current] = (p.group(1), codes)
    return mapping


def test_hr_routes_use_exact_granular_permissions() -> None:
    actual = _route_permissions()
    missing = sorted(set(EXPECTED_ROUTE_PERMISSIONS) - set(actual))
    assert not missing, f"rutas HR sin parsear: {missing}"
    diffs = {
        f"{method} {path}": (expected, actual.get((method, path)))
        for (method, path), expected in EXPECTED_ROUTE_PERMISSIONS.items()
        if actual.get((method, path)) != expected
    }
    assert not diffs, f"rutas HR con permiso incorrecto: {diffs}"


def test_hr_route_permissions_exist_in_canonical_catalog() -> None:
    canon = _canon()
    perm_codes = {code for code, _ in canon.PERMISSION_CATALOG}
    used = {code for _, codes in _route_permissions().values() for code in codes}
    orphans = sorted(used - perm_codes)
    assert not orphans, f"permisos de rutas HR fuera del catálogo canónico: {orphans}"


def test_granular_hr_codes_in_canonical_catalog() -> None:
    canon = _canon()
    perm_codes = {code for code, _ in canon.PERMISSION_CATALOG}
    missing = [code for code in GRANULAR_CODES if code not in perm_codes]
    assert not missing, f"códigos HR granulares ausentes del PERMISSION_CATALOG: {missing}"


def test_hr_navigation_items_use_granular_codes() -> None:
    canon = _canon()
    by_href = {item["href"]: item for item in canon.NAVIGATION_CATALOG}
    expected_nav = {
        "/management/hr/my-portal": "hr.portal.read",
        "/management/hr/directory": "hr.directory.read",
        "/management/hr/onboarding": "hr.onboarding.create",
        "/management/hr/shifts": "hr.shifts.read",
    }
    for href, perm in expected_nav.items():
        item = by_href.get(href)
        assert item is not None, f"ítem RRHH {href} no está en NAVIGATION_CATALOG"
        assert item["permission_code"] == perm, (
            f"{href}: permission_code {item['permission_code']!r} != {perm!r}"
        )


def test_roles_with_hr_get_granular_grants() -> None:
    canon = _canon()
    for role_name, grants in ROLE_HR_GRANTS.items():
        role_codes = set(canon.ROLE_PERMISSION_CODES.get(role_name, []))
        missing = [code for code in grants if code not in role_codes]
        assert not missing, f"rol {role_name} sin grants HR granulares: {missing}"
