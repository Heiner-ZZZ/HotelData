#!/usr/bin/env python3
"""
Valida que la matriz de navegación por rol sea coherente entre:

- sidebar-nav.ts (frontend)
- access-nav.ts (frontend)
- app.routes.ts (frontend — guards de shell)
- system-admin.routes.ts (frontend — guards individuales)
- route_permissions.py (backend)

Uso:
    python scripts/validate_role_navigation_matrix.py

Requiere Node.js 18+ y Python 3.10+.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─── Roles conocidos ────────────────────────────────────────────────
ALL_ROLES = {
    "super_admin",
    "admin_sistema",
    "hotel_partner",
    "gerente_hotel",
    "revenue_manager",
    "marketing_hotelero",
    "operador_datos",
    "auditor_datos",
    "cliente",
}

# ─── Matriz esperada: rol -> {rutas que DEBE ver, rutas que NO DEBE ver} ──
# Formato: (ruta_absoluta, razón)
EXPECTED_VISIBLE: dict[str, set[str]] = {
    "super_admin": {
        "/management",
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/properties",
        "/management/rooms",
        "/management/rates",
        "/management/policies",
        "/management/amenities",
        "/management/reports",
        "/management/settings",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "admin_sistema": {
        "/management",
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/properties",
        "/management/rooms",
        "/management/rates",
        "/management/policies",
        "/management/amenities",
        "/management/reports",
        "/management/settings",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "hotel_partner": {
        "/management",
        "/management/reservations",
        "/management/availability",
        "/management/properties",
        "/management/rooms",
        "/management/rates",
        "/management/policies",
        "/management/amenities",
        "/management/reports",
        "/management/settings",
    },
    "gerente_hotel": {
        "/management",
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/rooms",
        "/management/policies",
        "/management/reports",
    },
    "revenue_manager": {
        "/management",
        "/management/reservations",
        "/management/availability",
        "/management/properties",
        "/management/rates",
        "/management/reports",
    },
    "marketing_hotelero": {
        "/management",
        "/management/properties",
        "/management/policies",
        "/management/amenities",
        "/management/reports",
    },
    "operador_datos": {
        "/management/reports",
        "/system/audit",
        "/system/monitoring",
    },
    "auditor_datos": {
        "/management/reports",
        "/system/audit",
        "/system/monitoring",
    },
    "cliente": set(),
}

EXPECTED_HIDDEN: dict[str, set[str]] = {
    "cliente": {
        "/management",
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/properties",
        "/management/rooms",
        "/management/rates",
        "/management/policies",
        "/management/amenities",
        "/management/reports",
        "/management/settings",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "hotel_partner": {
        "/management/check-ins",
        "/management/check-outs",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "gerente_hotel": {
        "/management/rates",
        "/management/amenities",
        "/management/settings",
        "/management/properties",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "revenue_manager": {
        "/management/check-ins",
        "/management/check-outs",
        "/management/rooms",
        "/management/policies",
        "/management/amenities",
        "/management/settings",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "marketing_hotelero": {
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/rooms",
        "/management/rates",
        "/management/settings",
        "/system/users",
        "/system/permissions",
        "/system/audit",
        "/system/monitoring",
    },
    "operador_datos": {
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/properties",
        "/management/rooms",
        "/management/rates",
        "/management/policies",
        "/management/amenities",
        "/management/settings",
        "/system/users",
        "/system/permissions",
    },
    "auditor_datos": {
        "/management/reservations",
        "/management/availability",
        "/management/check-ins",
        "/management/check-outs",
        "/management/properties",
        "/management/rooms",
        "/management/rates",
        "/management/policies",
        "/management/amenities",
        "/management/settings",
        "/system/users",
        "/system/permissions",
    },
    "super_admin": set(),
    "admin_sistema": set(),
}


# ─── Utilidades de parseo ──────────────────────────────────────────

def _extract_role_arrays_ts(source: str) -> list[list[str]]:
    """Extrae listas de strings de arrays TS como ['a', 'b']"""
    results: list[list[str]] = []

    def _replacer(m: re.Match) -> str:
        content = m.group(1)
        items = re.findall(r"'([^']+)'", content)
        if items:
            results.append(items)
        return ""

    re.sub(r"allowedRoles:\s*\[([^\]]*)\]", _replacer, source)
    return results


def _extract_allowed_roles_ts(source: str, item_href: str) -> list[str]:
    """
    Encuentra allowedRoles para un item específico (por href) en un archivo TS.
    Retorna lista vacía si no hay restricción (significa: todos los roles del section/shell).
    """
    # Patrón: href: '...', ... allowedRoles: [...]
    pattern = re.escape(item_href) + r"'[^}]*?allowedRoles:\s*\[([^\]]*)\]"
    m = re.search(pattern, source)
    if not m:
        return []
    return re.findall(r"'([^']+)'", m.group(1))


def _extract_shell_allowed_roles(source: str, shell_path: str) -> list[str]:
    """Extrae allowedRoles de un shell route definition."""
    pattern = r"path:\s*'" + re.escape(shell_path) + r"'[^}]*?allowedRoles:\s*\[([^\]]*)\]"
    m = re.search(pattern, source)
    if not m:
        return []
    return re.findall(r"'([^']+)'", m.group(1))


# ─── Validaciones ───────────────────────────────────────────────────

def validate_shell_guards() -> list[str]:
    """Verifica que cada rol esté en el shell correcto."""
    errors: list[str] = []
    app_routes_path = REPO_ROOT / "frontend/src/app/app.routes.ts"
    source = app_routes_path.read_text(encoding="utf-8")

    management_roles = set(_extract_shell_allowed_roles(source, "management"))
    system_roles = set(_extract_shell_allowed_roles(source, "system"))
    account_roles = set(_extract_shell_allowed_roles(source, "account"))

    # Roles que DEBEN estar en management
    must_be_in_management = {"super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos"}
    for r in must_be_in_management:
        if r not in management_roles:
            errors.append(f"[SHELL] {r} debería estar en management allowedRoles pero no está.")

    # Roles que NO DEBEN estar en management
    forbidden_in_management = {"cliente"}
    for r in forbidden_in_management:
        if r in management_roles:
            errors.append(f"[SHELL] {r} NO debería estar en management allowedRoles.")

    # Roles que DEBEN estar en system
    must_be_in_system = {"super_admin", "admin_sistema", "operador_datos", "auditor_datos"}
    for r in must_be_in_system:
        if r not in system_roles:
            errors.append(f"[SHELL] {r} debería estar en system allowedRoles pero no está.")

    # Roles que NO DEBEN estar en system
    forbidden_in_system = {"cliente", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero"}
    for r in forbidden_in_system:
        if r in system_roles:
            errors.append(f"[SHELL] {r} NO debería estar en system allowedRoles.")

    # Roles que DEBEN estar en account
    if "cliente" not in account_roles:
        errors.append("[SHELL] cliente debería estar en account allowedRoles.")

    return errors


def validate_system_route_guards() -> list[str]:
    """Verifica que las rutas individuales de system tengan guards correctos."""
    errors: list[str] = []
    source = (REPO_ROOT / "frontend/src/app/features/system-admin/system-admin.routes.ts").read_text(encoding="utf-8")

    checks = {
        "users": {"expected_roles": {"super_admin", "admin_sistema"}},
        "permissions": {"expected_roles": {"super_admin", "admin_sistema"}},
        "audit": {"expected_roles": None},
        "monitoring": {"expected_roles": None},
    }
    for route_name, cfg in checks.items():
        marker = f"path: '{route_name}'"
        idx = source.find(marker)
        if idx == -1:
            errors.append(f"[SYSTEM-ROUTES] No se encontró ruta /system/{route_name}.")
            continue

        # Texto desde este path hasta el siguiente path: o '];' (final del array)
        rest = source[idx + len(marker):]
        next_path = re.search(r"path:\s*'", rest)
        next_idx = next_path.start() if next_path else rest.find("];")
        block = rest[:next_idx]

        has_guard = "roleGuard" in block
        roles_m = re.search(r"allowedRoles:\s*\[([^\]]*)\]", block)
        actual = set(re.findall(r"'([^']+)'", roles_m.group(1))) if roles_m else set()

        if not has_guard:
            errors.append(f"[SYSTEM-ROUTES] /system/{route_name} debería tener roleGuard.")

        if cfg["expected_roles"] is not None and actual != cfg["expected_roles"]:
            errors.append(f"[SYSTEM-ROUTES] /system/{route_name} roles esperados {cfg['expected_roles']}, actual {actual}")

    return errors


def validate_sidebar_roles() -> list[str]:
    """Verifica consistencia del sidebar-nav."""
    errors: list[str] = []
    sidebar_path = REPO_ROOT / "frontend/src/app/shared/ui/sidebar-nav/sidebar-nav.ts"
    source = sidebar_path.read_text(encoding="utf-8")

    # Extraer items con sus allowedRoles
    item_pattern = re.compile(
        r"label:\s*'([^']+)'[^}]*?href:\s*'([^']+)'[^}]*?(?:allowedRoles:\s*\[([^\]]*)\])?"
    )
    sidebar_map: dict[str, list[str]] = {}
    for m in item_pattern.finditer(source):
        href = m.group(2)
        roles_str = m.group(3)
        roles = re.findall(r"'([^']+)'", roles_str) if roles_str else []
        sidebar_map[href] = roles

    # Verificar items esperados por rol
    for role, expected_routes in EXPECTED_VISIBLE.items():
        for route in expected_routes:
            if route not in sidebar_map:
                continue  # ruta no definida en sidebar (ej: /management es el panel, ok)
            allowed = set(sidebar_map[route])
            if allowed and role not in allowed:
                errors.append(f"[SIDEBAR] {role} debería ver {route} pero no está en allowedRoles.")

    for role, forbidden_routes in EXPECTED_HIDDEN.items():
        for route in forbidden_routes:
            if route not in sidebar_map:
                continue
            allowed = set(sidebar_map[route])
            if not allowed:
                continue  # sin restricción -> todos ven
            if role in allowed:
                errors.append(f"[SIDEBAR] {role} NO debería ver {route} pero está en allowedRoles.")

    return errors


def validate_backend_permissions() -> list[str]:
    """Verifica que route_permissions.py tenga reglas coherentes."""
    errors: list[str] = []
    perms_path = REPO_ROOT / "src/app/security/route_permissions.py"
    source = perms_path.read_text(encoding="utf-8")

    reglas = re.findall(
        r"AccessRule\(([^)]+)\)",
        source.replace("\n", " ").replace("    ", " "),
    )

    for regla_str in reglas:
        if "permission=\"users.manage\"" in regla_str or "permission='users.manage'" in regla_str:
            if "roles=" not in regla_str:
                errors.append(f"[BACKEND] Regla con users.manage sin roles explícitos: {regla_str[:80]}")
            elif "auditor_datos" in regla_str or "operador_datos" in regla_str:
                errors.append(f"[BACKEND] Regla users.manage incluye rol no autorizado: {regla_str[:80]}")

    # Verificar que /api/management incluye los roles correctos
    for regla_str in reglas:
        if '"/api/management"' in regla_str or "'/api/management'" in regla_str:
            if "auditor_datos" not in regla_str or "operador_datos" not in regla_str:
                errors.append("[BACKEND] /api/management debería incluir auditor_datos y operador_datos.")
            if "gerente_hotel" not in regla_str:
                errors.append("[BACKEND] /api/management debería incluir gerente_hotel.")

    return errors


def main() -> int:
    errors: list[str] = []

    print("🔍 Validando matriz de navegación por rol...\n")

    try:
        errors.extend(validate_shell_guards())
    except Exception as e:
        errors.append(f"[ERROR] validate_shell_guards falló: {e}")

    try:
        errors.extend(validate_system_route_guards())
    except Exception as e:
        errors.append(f"[ERROR] validate_system_route_guards falló: {e}")

    try:
        errors.extend(validate_sidebar_roles())
    except Exception as e:
        errors.append(f"[ERROR] validate_sidebar_roles falló: {e}")

    try:
        errors.extend(validate_backend_permissions())
    except Exception as e:
        errors.append(f"[ERROR] validate_backend_permissions falló: {e}")

    if not errors:
        print("✅ Todas las validaciones pasaron.")
        return 0

    print(f"❌ Se encontraron {len(errors)} problemas:\n")
    for err in errors:
        print(f"  • {err}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
