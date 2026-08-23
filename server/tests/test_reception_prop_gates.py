"""Invariante de migración E (2026-08): reception opera POR HOTEL.

Las rutas de OPERACIÓN del módulo ``reception`` (turnos de un hotel) deben
gatear con ``require_prop_permission`` — el rol del hotel (role_assignments →
hotel_roles) es la única fuente de capacidad dentro del hotel; el rol GLOBAL
ya no basta (deny-by-default sin asignación).

Excepciones documentadas (vistas de GERENCIA multi-hotel, sin prop_id): se
quedan con ``require_permission("shifts.manage")`` global porque cruzan
hoteles a propósito (gerencia/plataforma). Si alguien reintroduce un gate
global en una ruta de operación — o una ruta nueva sin clasificar — este test
falla.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación: deben usar require_prop_permission.
EXPECTED_PROP_ROUTES = frozenset({
    ("GET", "/shifts/active"),
    ("POST", "/shifts/open"),
    ("GET", "/shifts/config"),
    ("PUT", "/shifts/config"),
    ("POST", "/shifts/{shift_id}/close"),
    ("GET", "/shifts/{shift_id}"),
    ("GET", "/shifts"),
})

# Excepciones de gerencia multi-hotel (ruta → código global exigido).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("GET", "/shifts/manager-control"): "shifts.manage",
    ("GET", "/shifts/open-overview"): "shifts.manage",
}


def _route_gates() -> dict[tuple[str, str], tuple[str, str]]:
    """(método, path) → (dependency, código) del primer Depends en la firma."""
    text = (SERVER_ROOT / "src/app/modules/reception/routes.py").read_text(encoding="utf-8")
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
    assert not missing, f"rutas reception sin parsear: {missing}"
    diffs = {
        f"{m} {p}": actual.get((m, p))
        for (m, p) in EXPECTED_PROP_ROUTES
        if actual.get((m, p)) != ("require_prop_permission", None) and actual.get((m, p))[0] != "require_prop_permission"
    }
    assert not diffs, f"rutas de operación sin gate por-hotel: {diffs}"


def test_management_exceptions_keep_global_gate() -> None:
    actual = _route_gates()
    for (m, p), code in GLOBAL_EXCEPTIONS.items():
        gate = actual.get((m, p))
        assert gate == ("require_permission", code), f"excepción {m} {p} espera ({code}): {gate}"


def test_all_routes_classified() -> None:
    actual = _route_gates()
    known = EXPECTED_PROP_ROUTES | set(GLOBAL_EXCEPTIONS)
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"rutas reception sin clasificar en el invariante: {unclassified}"
