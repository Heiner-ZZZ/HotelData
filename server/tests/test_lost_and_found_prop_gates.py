"""Invariante de migración E (2026-08): lost & found opera POR HOTEL.

Rutas de ``lost_and_found/routes.py``: gatean con
``require_any_prop_permission`` (``lost-found.X`` o ``housekeeping.X``, el
mismo combo que ya usaba la versión global). Deny-by-default: sin
role_assignment → 403; sin prop_id → 400; item de otro hotel → 404.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("POST", ""): ("require_any_prop_permission", ("lost-found.create", "housekeeping.create")),
    ("GET", ""): ("require_any_prop_permission", ("lost-found.read", "housekeeping.read")),
    ("GET", "/{item_id}"): ("require_any_prop_permission", ("lost-found.read", "housekeeping.read")),
    ("PUT", "/{item_id}"): ("require_any_prop_permission", ("lost-found.update", "housekeeping.update")),
    ("DELETE", "/{item_id}"): ("require_any_prop_permission", ("lost-found.delete", "housekeeping.delete")),
    ("POST", "/{item_id}/claim"): ("require_any_prop_permission", ("lost-found.update", "housekeeping.update")),
    ("POST", "/{item_id}/dispose"): ("require_any_prop_permission", ("lost-found.update", "housekeeping.update")),
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    text = (SERVER_ROOT / "src/app/modules/lost_and_found/routes.py").read_text(encoding="utf-8")
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
    assert not missing, f"rutas lost_and_found sin parsear: {missing}"
    bad = {
        f"{m} {p}": (expected, actual.get((m, p)))
        for (m, p), expected in EXPECTED_PROP_ROUTES.items()
        if actual.get((m, p)) != (expected[0], frozenset(expected[1]))
    }
    assert not bad, f"rutas de operación sin gate por-hotel correcto: {bad}"


def test_all_routes_classified() -> None:
    actual = _route_gates()
    unclassified = sorted(set(actual) - set(EXPECTED_PROP_ROUTES))
    assert not unclassified, f"rutas lost_and_found sin clasificar: {unclassified}"
