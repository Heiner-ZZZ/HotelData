"""Invariante de migración E (2026-08): check-ins/outs operan POR HOTEL.

Rutas de ``reservations/routes/management.py`` (check-ins, check-outs,
no-show/reopen, pos-charge, users/search, assign-rooms): gatean con
``require_prop_permission``/``require_any_prop_permission`` (lecturas
``check-ins.read``/``check-outs.read``/``reservations.read``, escrituras
``check-ins.manage``/``check-outs.manage``/``reservations.update``/
``charges.manage``). Deny-by-default: sin role_assignment → 403; sin
prop_id → 400; booking de otro hotel → 404.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/check-ins/dates"): ("require_prop_permission", ("check-ins.read",)),
    ("GET", "/check-ins"): ("require_prop_permission", ("check-ins.read",)),
    ("PATCH", "/check-ins/{booking_id}/update-datetime"): ("require_prop_permission", ("check-ins.manage",)),
    ("POST", "/check-ins/{booking_id}/declare-late-arrival"): ("require_prop_permission", ("check-ins.manage",)),
    ("GET", "/check-ins/{booking_id}/detail"): ("require_prop_permission", ("check-ins.read",)),
    ("GET", "/check-ins/{booking_id}/room-availability"): ("require_prop_permission", ("check-ins.read",)),
    ("PATCH", "/check-ins/{booking_id}/detail"): ("require_prop_permission", ("check-ins.manage",)),
    ("POST", "/check-ins/{booking_id}/complete"): ("require_prop_permission", ("check-ins.manage",)),
    ("GET", "/check-outs/dates"): ("require_prop_permission", ("check-outs.read",)),
    ("GET", "/check-outs"): ("require_prop_permission", ("check-outs.read",)),
    ("GET", "/check-outs/{booking_id}/detail"): ("require_prop_permission", ("check-outs.read",)),
    ("PATCH", "/check-outs/{booking_id}/detail"): ("require_prop_permission", ("check-outs.manage",)),
    ("POST", "/check-outs/{booking_id}/complete"): ("require_prop_permission", ("check-outs.manage",)),
    ("POST", "/bookings/{booking_id}/pos-charge"): ("require_prop_permission", ("charges.manage",)),
    ("GET", "/users/search"): ("require_any_prop_permission", ("reservations.manage", "reservations.read")),
    ("POST", "/bookings/{booking_id}/no-show"): ("require_prop_permission", ("reservations.update",)),
    ("POST", "/bookings/{booking_id}/reopen-no-show"): ("require_prop_permission", ("check-ins.manage",)),
    ("GET", "/bookings/{booking_id}/available-rooms"): ("require_prop_permission", ("reservations.read",)),
    ("POST", "/bookings/{booking_id}/assign-rooms"): ("require_prop_permission", ("reservations.update",)),
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    text = (SERVER_ROOT / "src/app/modules/reservations/routes/management.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@management_api_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
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
    assert not missing, f"rutas management sin parsear: {missing}"
    bad = {
        f"{m} {p}": (expected, actual.get((m, p)))
        for (m, p), expected in EXPECTED_PROP_ROUTES.items()
        if actual.get((m, p)) != (expected[0], frozenset(expected[1]))
    }
    assert not bad, f"rutas de operación sin gate por-hotel correcto: {bad}"


def test_all_routes_classified() -> None:
    actual = _route_gates()
    unclassified = sorted(set(actual) - set(EXPECTED_PROP_ROUTES))
    assert not unclassified, f"rutas management sin clasificar: {unclassified}"
