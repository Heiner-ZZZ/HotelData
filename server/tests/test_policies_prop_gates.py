"""Invariante de migración E (2026-08): POLICIES opera POR HOTEL.

Las rutas de ESCRITURA del módulo (``PUT /policies``) deben gatear con
``require_prop_permission`` — el rol del hotel (role_assignments →
hotel_roles) es la única fuente de capacidad; el rol GLOBAL ya no basta
(deny-by-default sin asignación). ``prop_id`` llega por QUERY (nunca solo
por body — el hueco del middleware) y el handler valida consistencia
query↔body.

Excepciones documentadas: ``GET /policies/options`` (selector de propiedades
cross-hotel) se queda global con ``properties.read``. Las rutas de LECTURA
``GET /policies`` y ``GET /policies/room-types`` son PÚBLICAS (sin gate —
booking engine/partner), por lo que no aparecen en el mapa de gates.

Si alguien reintroduce un gate global en una ruta de operación — o una ruta
nueva con gate sin clasificar — este test falla.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación: deben usar require_prop_permission.
EXPECTED_PROP_ROUTES = frozenset({
    ("PUT", "/policies"),
})

# Excepciones globales documentadas (ruta → código global exigido).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("GET", "/policies/options"): "properties.read",
}


def _route_gates() -> dict[tuple[str, str], tuple[str, str]]:
    """(método, path) → (dependency, código) del primer Depends en la firma."""
    text = (SERVER_ROOT / "src/app/modules/partner/routes/policies.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@api_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
    gate_re = re.compile(
        r"Depends\((require_prop_permission|require_permission)\(\s*\"([^\"]+)\"\s*\)\)"
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
    assert not missing, f"rutas policies sin parsear: {missing}"
    diffs = {
        f"{m} {p}": actual.get((m, p))
        for (m, p) in EXPECTED_PROP_ROUTES
        if actual.get((m, p))[0] != "require_prop_permission"
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
    assert not unclassified, f"rutas policies sin clasificar en el invariante: {unclassified}"
