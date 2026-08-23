"""Invariante de migración E (2026-08): expenses opera POR HOTEL.

Rutas de OPERACIÓN (dashboard, facturas, pagos, presupuesto, libro mayor,
estados financieros, folios): gatean con ``require_prop_permission``
(``revenue.read`` para lecturas, ``revenue.manage`` para escrituras que
mueven dinero). El rol del hotel es la única fuente de capacidad dentro del
hotel (deny-by-default: sin role_assignment → 403; sin prop_id → 400).

Excepciones globales documentadas (catálogos/entidades de REFERENCIA que el
código trata como compartidas entre hoteles):
- GET/POST ``/categories`` — catálogo global de categorías de gasto
  (``find()`` sin filtro de prop; ``create_category`` no recibe prop_id).
- POST ``/budget`` — permite presupuestos GLOBALES legacy (body prop_id
  opcional por decisión explícita del módulo).
- GET ``/ledger/accounts`` y GET ``/ledger/chart-of-accounts`` — catálogo de
  cuentas contables (COA) global, consumido sin prop_id por el frontend.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación → (dependency, código).
EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/dashboard"): ("require_prop_permission", ("revenue.read",)),
    ("POST", "/invoices"): ("require_prop_permission", ("revenue.manage",)),
    ("GET", "/invoices"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/invoices/{invoice_id}"): ("require_prop_permission", ("revenue.read",)),
    ("POST", "/invoices/{invoice_id}/pay"): ("require_prop_permission", ("revenue.manage",)),
    ("PUT", "/invoices/{invoice_id}"): ("require_prop_permission", ("revenue.manage",)),
    ("DELETE", "/invoices/{invoice_id}"): ("require_prop_permission", ("revenue.manage",)),
    ("GET", "/budget"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/folios"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/folios/{folio_id}/postings"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/summary"): ("require_prop_permission", ("revenue.read",)),
    ("POST", "/ledger/folios/{folio_id}/payment"): ("require_prop_permission", ("revenue.manage",)),
    ("POST", "/ledger/folios/{folio_id}/transfer"): ("require_prop_permission", ("revenue.manage",)),
    ("GET", "/ledger/periods"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/trial-balance"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/income-statement"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/balance-sheet"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/{prop_id}/summary"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/{prop_id}/periods"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/{prop_id}/transactions"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/{prop_id}/trial-balance"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/{prop_id}/income-statement"): ("require_prop_permission", ("revenue.read",)),
    ("GET", "/ledger/{prop_id}/balance-sheet"): ("require_prop_permission", ("revenue.read",)),
}

# Excepciones globales documentadas (ruta → dependency/código).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/categories"): ("require_permission", ("revenue.read",)),
    ("POST", "/categories"): ("require_permission", ("revenue.manage",)),
    ("POST", "/budget"): ("require_permission", ("revenue.manage",)),
    ("GET", "/ledger/accounts"): ("require_permission", ("revenue.read",)),
    ("GET", "/ledger/chart-of-accounts"): ("require_permission", ("revenue.read",)),
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    """(método, path) → (dependency, códigos) del primer Depends en la firma."""
    text = (SERVER_ROOT / "src/app/modules/expenses/routes.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@api_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
    gate_re = re.compile(
        r"Depends\(\s*(require_any_prop_permission|require_prop_permission|require_any_permission|require_permission)"
        r"\(\s*(.*?)\s*\)\s*\)",
        re.S,
    )
    mapping: dict[tuple[str, str], tuple[str, frozenset[str]]] = {}
    current: tuple[str, str] | None = None
    block: list[str] = []
    for line in text.splitlines():
        m = route_re.search(line)
        if m:
            current = (m.group(1).upper(), m.group(2))
            block = []
            continue
        if current is None:
            continue
        block.append(line)
        if line.strip().startswith("):") or line.strip() == "):":
            g = gate_re.search("\n".join(block))
            if g and current not in mapping:
                codes = frozenset(re.findall(r'"([^"]+)"', g.group(2)))
                mapping[current] = (g.group(1), codes)
            current = None
    return mapping


def test_operation_routes_use_prop_gates() -> None:
    actual = _route_gates()
    missing = sorted(set(EXPECTED_PROP_ROUTES) - set(actual))
    assert not missing, f"rutas expenses sin parsear: {missing}"
    bad = {
        f"{m} {p}": (expected, actual.get((m, p)))
        for (m, p), expected in EXPECTED_PROP_ROUTES.items()
        if actual.get((m, p)) != (expected[0], frozenset(expected[1]))
    }
    assert not bad, f"rutas de operación sin gate por-hotel correcto: {bad}"


def test_global_exceptions_keep_global_gate() -> None:
    actual = _route_gates()
    for (m, p), expected in GLOBAL_EXCEPTIONS.items():
        gate = actual.get((m, p))
        assert gate == (expected[0], frozenset(expected[1])), f"excepción {m} {p}: {gate}"


def test_all_routes_classified() -> None:
    actual = _route_gates()
    known = set(EXPECTED_PROP_ROUTES) | set(GLOBAL_EXCEPTIONS)
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"rutas expenses sin clasificar: {unclassified}"
