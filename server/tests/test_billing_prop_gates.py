"""Invariante de migración E (2026-08): billing opera POR HOTEL.

Rutas de OPERACIÓN (facturas, pagos, folios, servicios, analytics): gatean con
``require_prop_permission`` / ``require_any_prop_permission`` (combos
billing.manage+check-outs.manage para emisión fiscal, y
billing.manage+billing.write_off.approve para settle/close de folios). El rol
del hotel es la única fuente de capacidad dentro del hotel.

Excepciones documentadas (globales por diseño):
- GET/POST ``/my-invoices*`` — auto-servicio del HUÉSPED (account.read/update,
  self-scoped por user_id).
- POST ``/folios/cleanup-expired`` — limpieza global multi-hotel (billing.manage).
- GET ``/folios/categories`` — catálogo de referencia (billing.read).
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación → (dependency, código o conjunto).
# require_any_prop_permission = cualquiera de los códigos, con contexto de hotel.
EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("POST", "/invoices"): ("require_any_prop_permission", ("billing.manage", "check-outs.manage")),
    ("POST", "/invoices/complement"): ("require_any_prop_permission", ("billing.manage", "check-outs.manage")),
    ("GET", "/invoices"): ("require_prop_permission", ("billing.read",)),
    ("GET", "/analytics/invoices"): ("require_prop_permission", ("reports.billing.invoices.read",)),
    ("GET", "/analytics/payments"): ("require_prop_permission", ("reports.billing.payments.read",)),
    ("GET", "/invoices/stats"): ("require_prop_permission", ("billing.read",)),
    ("GET", "/invoices/{invoice_id}"): ("require_prop_permission", ("billing.read",)),
    ("POST", "/invoices/{invoice_id}/items"): ("require_prop_permission", ("billing.manage",)),
    ("DELETE", "/invoices/{invoice_id}/items/{item_id}"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/invoices/{invoice_id}/repair-settlement"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/invoices/{invoice_id}/credit-note"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/invoices/{invoice_id}/cancel"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/invoices/{invoice_id}/pay"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/invoices/{invoice_id}/email"): ("require_any_prop_permission", ("billing.manage", "check-outs.manage")),
    ("POST", "/payments"): ("require_prop_permission", ("payments.manage",)),
    ("GET", "/payments"): ("require_prop_permission", ("payments.read",)),
    ("POST", "/payments/{payment_id}/classify-informational"): ("require_prop_permission", ("payments.manage",)),
    ("GET", "/payments/{payment_id}/link-candidates"): ("require_prop_permission", ("payments.manage",)),
    ("POST", "/payments/{payment_id}/link-shift"): ("require_prop_permission", ("payments.manage",)),
    ("GET", "/payments/{payment_id}"): ("require_prop_permission", ("payments.read",)),
    ("POST", "/payments/{payment_id}/refund"): ("require_prop_permission", ("payments.manage",)),
    ("GET", "/services"): ("require_prop_permission", ("billing.read",)),
    ("GET", "/folios/{booking_id}"): ("require_prop_permission", ("billing.read",)),
    ("POST", "/folios/{booking_id}/post"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/folios/{booking_id}/reopen"): ("require_prop_permission", ("billing.manage",)),
    ("POST", "/folios/{booking_id}/settle"): ("require_any_prop_permission", ("billing.manage", "billing.write_off.approve")),
    ("POST", "/folios/{booking_id}/close"): ("require_any_prop_permission", ("billing.manage", "billing.write_off.approve")),
    ("GET", "/folios"): ("require_prop_permission", ("billing.read",)),
}

# Excepciones globales documentadas (ruta → dependency/código).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/my-invoices"): ("require_permission", ("account.read",)),
    ("GET", "/my-invoices/{invoice_id}"): ("require_permission", ("account.read",)),
    ("POST", "/my-invoices/{invoice_id}/pay"): ("require_permission", ("account.update",)),
    ("POST", "/folios/cleanup-expired"): ("require_permission", ("billing.manage",)),
    ("GET", "/folios/categories"): ("require_permission", ("billing.read",)),
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    """(método, path) → (dependency, códigos) del primer Depends en la firma.

    Soporta require_prop_permission/require_any_prop_permission/require_permission/
    require_any_permission, en una o varias líneas (bloque de firma acumulado).
    """
    text = (SERVER_ROOT / "src/app/modules/billing/routes.py").read_text(encoding="utf-8")
    # La constante canónica del combo de supervisor se resuelve para el parseo.
    text = text.replace("FOLIO_ADJUST_APPROVAL_PERMISSION", '"billing.write_off.approve"')
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
    assert not missing, f"rutas billing sin parsear: {missing}"
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
    assert not unclassified, f"rutas billing sin clasificar: {unclassified}"
