"""Invariante de migración E (2026-08): INSTAY (staff) opera POR HOTEL.

Las rutas del staff (``staff_router``, prefix ``/api/stay``) — sesiones,
service requests, conversaciones, stream, reply — deben gatear con
``require_prop_permission``: el rol del hotel es la única fuente de
capacidad; el rol GLOBAL ya no basta. ``prop_id`` llega por QUERY
(obligatorio; las escrituras lo llevan además en el body y el handler valida
consistencia query↔body).

Excepciones/no incluidas:
- Rutas de HUÉSPED (``guest_router``, ``/api/stay/guest/*``) son token-based
  sin gate — auto-servicio, no operación del staff → no aparecen en el mapa.
- ``GET /notifications/stream`` ya exige ``prop_id`` en query.

Si alguien reintroduce un gate global en una ruta de operación — o una ruta
nueva del staff con gate sin clasificar — este test falla.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_ROUTES = frozenset({
    ("POST", "/my-session"),
    ("POST", "/sessions"),
    ("GET", "/sessions"),
    ("POST", "/sessions/cleanup-expired"),
    ("GET", "/sessions/{token}"),
    ("POST", "/sessions/{token}/deactivate"),
    ("GET", "/requests"),
    ("GET", "/requests/analytics"),
    ("POST", "/requests"),
    ("PUT", "/requests/{request_id}"),
    ("GET", "/conversations"),
    ("GET", "/conversations/{room_label}"),
    ("GET", "/notifications/stream"),
    ("POST", "/conversations/{room_label}/reply"),
})


def _route_gates() -> dict[tuple[str, str], tuple[str, str]]:
    text = (SERVER_ROOT / "src/app/modules/instay/routes.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@staff_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
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


def test_staff_routes_use_prop_gate() -> None:
    actual = _route_gates()
    missing = sorted(EXPECTED_PROP_ROUTES - set(actual))
    assert not missing, f"rutas instay staff sin parsear: {missing}"
    diffs = {
        f"{m} {p}": actual.get((m, p))
        for (m, p) in EXPECTED_PROP_ROUTES
        if actual.get((m, p))[0] != "require_prop_permission"
    }
    assert not diffs, f"rutas staff sin gate por-hotel: {diffs}"


def test_all_staff_routes_classified() -> None:
    actual = _route_gates()
    unclassified = sorted(set(actual) - EXPECTED_PROP_ROUTES)
    assert not unclassified, f"rutas instay staff sin clasificar: {unclassified}"
