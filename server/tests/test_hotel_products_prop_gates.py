"""Invariante de migración E (2026-08): HOTEL PRODUCTS opera POR HOTEL.

Rutas de operación (CRUD por hotel, restock, reports por hotel, line-items de
reserva) deben gatear con ``require_prop_permission`` — el rol del hotel es la
única fuente de capacidad; el rol GLOBAL ya no basta (deny-by-default sin
``role_assignments``). ``prop_id`` viene del PATH (``/products/hotels/{prop_id}``)
o del QUERY (reports, line-items).

Excepciones de PLATAFORMA (no se migran — siguen globales por diseño):
- ``GET /products/earnings*`` y ``PUT /products/earnings/{booking_id}/pay``
  portan ``users.manage`` (código SYSTEM_SCOPE) — comisiones/ganancias de
  plataforma, no operación del hotel.

Si alguien reintroduce un gate global en una ruta de operación — o una ruta
nueva con gate sin clasificar — este test falla.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_ROUTES = frozenset({
    ("GET", "/products/hotels/{prop_id}"),
    ("POST", "/products/hotels/{prop_id}"),
    ("PUT", "/products/hotels/{prop_id}/{product_id}"),
    ("DELETE", "/products/hotels/{prop_id}/{product_id}"),
    ("POST", "/products/hotels/{prop_id}/{product_id}/restock"),
    ("GET", "/products/reports/margin"),
    ("GET", "/products/reports/cogs"),
    ("GET", "/products/reports/stock-value"),
    ("GET", "/products/bookings/{booking_id}/line-items"),
    ("POST", "/products/bookings/{booking_id}/line-items"),
    ("DELETE", "/products/bookings/{booking_id}/line-items/{item_id}"),
})

GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("GET", "/products/earnings/summary"): "users.manage",
    ("GET", "/products/earnings"): "users.manage",
    ("GET", "/products/earnings/weekly"): "users.manage",
    ("PUT", "/products/earnings/{booking_id}/pay"): "users.manage",
}


def _route_gates() -> dict[tuple[str, str], tuple[str, str]]:
    text = (SERVER_ROOT / "src/app/modules/partner/routes/hotel_products.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
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
    assert not missing, f"rutas hotel_products sin parsear: {missing}"
    diffs = {
        f"{m} {p}": actual.get((m, p))
        for (m, p) in EXPECTED_PROP_ROUTES
        if actual.get((m, p))[0] != "require_prop_permission"
    }
    assert not diffs, f"rutas de operación sin gate por-hotel: {diffs}"


def test_platform_exceptions_keep_global_gate() -> None:
    actual = _route_gates()
    for (m, p), code in GLOBAL_EXCEPTIONS.items():
        gate = actual.get((m, p))
        assert gate == ("require_permission", code), f"excepción {m} {p} espera ({code}): {gate}"


def test_all_routes_classified() -> None:
    actual = _route_gates()
    known = EXPECTED_PROP_ROUTES | set(GLOBAL_EXCEPTIONS)
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"rutas hotel_products sin clasificar: {unclassified}"
