"""Invariante de migración E (2026-08): reservas operan POR HOTEL.

Rutas de ``reservations/routes/reservations.py``: las de OPERACIÓN gatean con
``require_prop_permission`` (``reservations.read/create/update/delete``).
Deny-by-default: sin role_assignment → 403; sin prop_id → 400; booking de
otro hotel → 404.

Excepciones globales documentadas (vistas multi-hotel / flujos del huésped):
- GET ``/options`` y GET ``/stats`` — vistas multi-hotel (picker + widgets de
  la lista de reservas; sin prop_id no operan un hotel concreto).
- GET ``/unpriced`` — vista de mantenimiento multi-hotel (respeta
  ``hotel_filter_from_user``).
- GET ``/{booking_id}`` — flujo MIXTO: el huésped (``cliente``) lee su propia
  reserva (check de ownership inline); para staff el handler aplica el gate
  por-hotel INLINE (``user_has_permission(prop_id=...)`` + acceso al hotel).
- GET ``""`` (lista) — flujo MIXTO: el huésped lista sus reservas; con
  ``prop_id`` staff aplica el gate por-hotel INLINE.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/dates"): ("require_prop_permission", ("reservations.read",)),
    ("GET", "/availability-check"): ("require_prop_permission", ("reservations.read",)),
    ("GET", "/rate-plans"): ("require_prop_permission", ("reservations.read",)),
    ("POST", "/preview"): ("require_prop_permission", ("reservations.read",)),
    ("POST", ""): ("require_prop_permission", ("reservations.create",)),
    ("POST", "/validate-coupon"): ("require_prop_permission", ("reservations.read",)),
    ("GET", "/export"): ("require_prop_permission", ("reservations.read",)),
    ("PATCH", "/{booking_id}/special-requests"): ("require_prop_permission", ("reservations.update",)),
    ("GET", "/{booking_id}/cancel-preview"): ("require_prop_permission", ("reservations.read",)),
    ("POST", "/{booking_id}/cancel"): ("require_prop_permission", ("reservations.delete",)),
    ("POST", "/{booking_id}/confirm"): ("require_prop_permission", ("reservations.update",)),
    ("POST", "/{booking_id}/reject"): ("require_prop_permission", ("reservations.update",)),
    ("POST", "/{booking_id}/recalculate-price"): ("require_prop_permission", ("reservations.update",)),
    ("PATCH", "/{booking_id}"): ("require_prop_permission", ("reservations.update",)),
    ("GET", "/{booking_id}/room-guests"): ("require_prop_permission", ("reservations.read",)),
    ("PUT", "/{booking_id}/room-guests"): ("require_prop_permission", ("reservations.update",)),
    ("GET", "/{booking_id}/check-in-status"): ("require_prop_permission", ("reservations.read",)),
}

# Excepciones globales (ruta → dependency/código). GET "" y GET /{booking_id}
# tienen además un gate por-hotel INLINE documentado (mixto huésped/staff).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", ""): ("require_permission", ("reservations.read",)),
    ("GET", "/options"): ("require_permission", ("reservations.read",)),
    ("GET", "/stats"): ("require_permission", ("reservations.read",)),
    ("GET", "/unpriced"): ("require_permission", ("reservations.update",)),
    ("GET", "/{booking_id}"): ("require_permission", ("reservations.read",)),
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    text = (SERVER_ROOT / "src/app/modules/reservations/routes/reservations.py").read_text(encoding="utf-8")
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
            if current is not None:
                g = gate_re.search("\n".join(block))
                if g and current not in mapping:
                    mapping[current] = (g.group(1), frozenset(re.findall(r'"([^"]+)"', g.group(2))))
            current = (m.group(1).upper(), m.group(2))
            block = []
            continue
        if current is None:
            continue
        block.append(line)
        stripped = line.strip()
        if stripped.startswith("):") or (stripped.startswith("def ") and stripped.endswith(":")):
            g = gate_re.search("\n".join(block))
            if g and current not in mapping:
                mapping[current] = (g.group(1), frozenset(re.findall(r'"([^"]+)"', g.group(2))))
            current = None
    return mapping


def test_operation_routes_use_prop_gates() -> None:
    actual = _route_gates()
    missing = sorted(set(EXPECTED_PROP_ROUTES) - set(actual))
    assert not missing, f"rutas reservations sin parsear: {missing}"
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
    assert not unclassified, f"rutas reservations sin clasificar: {unclassified}"
