"""Invariante de migración E (2026-08): AMENITIES opera POR HOTEL.

Las rutas de OPERACIÓN de amenities (CRUD por hotel + fotos + stock) deben
gatear con ``require_prop_permission`` — el rol del hotel es la única fuente
de capacidad; el rol GLOBAL ya no basta (deny-by-default sin asignación).
``prop_id`` llega por QUERY (las escrituras lo tienen además en el body y el
handler valida consistencia query↔body — el hueco del middleware).

Excepciones documentadas:
- ``GET /amenities`` es PÚBLICA (sin gate — booking engine/partner).
- ``GET /amenities/options`` (selector) es LOGIN-ONLY (Opción 2, 2026-08): sin
  códigos globales; el scope sale de ``assigned_hotels`` y con ``prop_id`` el
  catálogo se restringe por asignación (cross-hotel → 403).
- ``GET/PUT /amenities/default-prices`` son catálogo MAESTRO global (no
  per-hotel) — se quedan globales.
- ``GET /api/amenities/stock`` (vista admin multi-hotel, prop_id opcional)
  se queda global ``amenities.read``.

Si alguien reintroduce un gate global en una ruta de operación — o una ruta
nueva con gate sin clasificar — este test falla.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación: deben usar require_prop_permission. (método, path)
EXPECTED_PROP_ROUTES = frozenset({
    ("PUT", "/amenities"),
    ("PUT", "/amenities/special-requests"),
    ("POST", "/amenities/photos"),
    ("GET", "/amenities/photos"),
    ("DELETE", "/amenities/photos/{photo_id}"),
})

# Excepciones globales documentadas (ruta → código global exigido).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("GET", "/amenities/default-prices"): "amenities.read",
    ("PUT", "/amenities/default-prices"): "amenities.manage",
}

# Selectores de scope (Opción 2): sin códigos — login-only + scope por
# asignación; el invariante exige ``require_login`` exacto.
LOGIN_ONLY_SELECTORS: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/amenities/options"),
})

# Rutas del módulo stock (prefix /api/amenities/stock → paths vacíos en el
# decorador "@admin_router.get(\"\")"): lectura multi-hotel global por diseño,
# escritura por-hotel.
STOCK_PROP_ROUTES = frozenset({("PUT", "")})
STOCK_GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("GET", ""): "amenities.read",
}


def _route_gates(path: str, router_name: str = "api_router") -> dict[tuple[str, str], tuple[str, str]]:
    """(método, path) → (dependency, código) del primer Depends en la firma."""
    text = (SERVER_ROOT / path).read_text(encoding="utf-8")
    route_re = re.compile(rf"@{router_name}\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
    gate_re = re.compile(
        r"Depends\((require_login|require_prop_permission|require_permission)"
        r"(?:\(\s*\"([^\"]+)\"\s*\))?\)"
    )
    mapping: dict[tuple[str, str], tuple[str, str | None]] = {}
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


def _assert_prop_and_exceptions(
    actual,
    prop_routes,
    global_exceptions,
    login_only,
    label: str,
) -> None:
    missing = sorted(prop_routes - set(actual))
    assert not missing, f"rutas {label} sin parsear: {missing}"
    diffs = {
        f"{m} {p}": actual.get((m, p))
        for (m, p) in prop_routes
        if actual.get((m, p))[0] != "require_prop_permission"
    }
    assert not diffs, f"rutas {label} de operación sin gate por-hotel: {diffs}"
    for (m, p), code in global_exceptions.items():
        gate = actual.get((m, p))
        assert gate == ("require_permission", code), f"excepción {label} {m} {p} espera ({code}): {gate}"
    for (m, p) in login_only:
        gate = actual.get((m, p))
        assert gate == ("require_login", None), f"selector {label} {m} {p} espera require_login: {gate}"
    known = prop_routes | set(global_exceptions) | set(login_only)
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"rutas {label} sin clasificar en el invariante: {unclassified}"


def test_operation_routes_use_prop_gate() -> None:
    _assert_prop_and_exceptions(
        _route_gates("src/app/modules/partner/routes/amenities.py"),
        EXPECTED_PROP_ROUTES,
        GLOBAL_EXCEPTIONS,
        LOGIN_ONLY_SELECTORS,
        "amenities",
    )


def test_stock_routes_classified() -> None:
    _assert_prop_and_exceptions(
        _route_gates("src/app/modules/amenities/routes.py", router_name="admin_router"),
        STOCK_PROP_ROUTES,
        STOCK_GLOBAL_EXCEPTIONS,
        frozenset(),
        "amenities-stock",
    )
