"""Invariante de migración E (2026-08): housekeeping opera POR HOTEL.

Todas las rutas de operación del módulo (room-status, tasks, maintenance,
charges, cleaning, analytics, staff…) gatean con ``require_prop_permission``
— el rol del hotel es la única fuente de capacidad dentro del hotel; el rol
GLOBAL ya no basta.

Excepción documentada: ``POST /room-status/cleanup-orphans`` es una
operación de MANTENIMIENTO multi-hotel (si se omite prop_id limpia todos los
hoteles) → se queda global con ``housekeeping.delete``.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación: deben usar require_prop_permission.
EXPECTED_PROP_ROUTES = frozenset({
    ("PUT", "/room-status"),
    ("GET", "/room-status"),
    ("GET", "/room-status/history"),
    ("GET", "/room-status/analytics"),
    ("GET", "/room-status/{record_id}"),
    ("POST", "/room-status/bulk"),
    ("POST", "/room-status/sync"),
    ("POST", "/tasks"),
    ("GET", "/tasks"),
    ("POST", "/tasks/{task_id}/complete"),
    ("PUT", "/tasks/{task_id}"),
    ("DELETE", "/tasks/{task_id}"),
    ("POST", "/maintenance"),
    ("GET", "/maintenance"),
    ("POST", "/maintenance/{task_id}/reconcile-no-cost"),
    ("PUT", "/maintenance/{task_id}"),
    ("POST", "/maintenance/{task_id}/complete"),
    ("DELETE", "/maintenance/{task_id}"),
    ("POST", "/charges"),
    ("GET", "/charges"),
    ("POST", "/charges/{charge_id}/repair-posting"),
    ("POST", "/charges/{charge_id}/recover"),
    ("GET", "/charges/{charge_id}"),
    ("DELETE", "/charges/{charge_id}"),
    ("PUT", "/charges/{charge_id}"),
    ("GET", "/room-status/transitions"),
    ("POST", "/cleaning/start"),
    ("POST", "/cleaning/complete"),
    ("POST", "/cleaning/approve"),
    ("GET", "/operations/analytics"),
    ("GET", "/dashboard"),
    ("GET", "/calendar-week"),
    ("GET", "/staff"),
    ("GET", "/upcoming-events"),
})

# Excepción de mantenimiento multi-hotel (ruta → código global exigido).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("POST", "/room-status/cleanup-orphans"): "housekeeping.delete",
}


def _route_gates() -> dict[tuple[str, str], tuple[str, str]]:
    text = (SERVER_ROOT / "src/app/modules/housekeeping/routes.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@api_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
    gate_re = re.compile(
        r"Depends\((require_prop_permission|require_permission|require_any_permission)\(\s*\"([^\"]+)\"\s*\)\)"
    )
    mapping: dict[tuple[str, str], tuple[str, str]] = {}
    current: tuple[str, str] | None = None
    for line in text.splitlines():
        m = route_re.search(line)
        if m:
            current = (m.group(1).upper(), m.group(2))
            continue
        g = gate_re.search(line)
        if g and current is not None and current not in mapping:
            mapping[current] = (g.group(1), g.group(2))
    return mapping


def test_operation_routes_use_prop_gate() -> None:
    actual = _route_gates()
    missing = sorted(EXPECTED_PROP_ROUTES - set(actual))
    assert not missing, f"rutas housekeeping sin parsear: {missing}"
    bad = {
        f"{m} {p}": actual.get((m, p))
        for (m, p) in EXPECTED_PROP_ROUTES
        if actual.get((m, p)) is None or actual[(m, p)][0] != "require_prop_permission"
    }
    assert not bad, f"rutas de operación sin gate por-hotel: {bad}"


def test_management_exception_keeps_global_gate() -> None:
    actual = _route_gates()
    gate = actual.get(("POST", "/room-status/cleanup-orphans"))
    assert gate == ("require_permission", "housekeeping.delete"), (
        f"cleanup-orphans espera (require_permission, housekeeping.delete): {gate}"
    )


def test_all_routes_classified() -> None:
    actual = _route_gates()
    known = EXPECTED_PROP_ROUTES | set(GLOBAL_EXCEPTIONS)
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"rutas housekeeping sin clasificar: {unclassified}"
