"""Invariante de migración E (2026-08): tarifas operan POR HOTEL.

Rutas de OPERACIÓN de ``partner/routes/rates.py`` (detalle, planes, reglas
estacionales, calendario, promociones legacy y contratos corporativos):
gatean con ``require_prop_permission`` (``rates.read`` para lecturas,
``rates.update``/``rates.manage`` para escrituras). El rol del hotel es la
única fuente de capacidad dentro del hotel (deny-by-default: sin
role_assignment → 403; sin prop_id → 400).

Excepción global documentada:
- GET ``/rates/options`` — vista MULTI-HOTEL del picker de propiedades de la
  UI de Tarifas (lista los hoteles accesibles del usuario filtrados por
  ``list_partner_hotels(user=...)``; sin prop_id no opera un hotel concreto).
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

# Rutas de operación → (dependency, código).
EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/rates"): ("require_prop_permission", ("rates.read",)),
    ("POST", "/rates/plans"): ("require_prop_permission", ("rates.manage",)),
    ("PUT", "/rates/plans/{plan_id}"): ("require_prop_permission", ("rates.update",)),
    ("DELETE", "/rates/plans/{plan_id}"): ("require_prop_permission", ("rates.manage",)),
    ("GET", "/rates/seasonal-rules"): ("require_prop_permission", ("rates.read",)),
    ("POST", "/rates/seasonal-rules"): ("require_prop_permission", ("rates.manage",)),
    ("PUT", "/rates/seasonal-rules/{rule_id}"): ("require_prop_permission", ("rates.manage",)),
    ("DELETE", "/rates/seasonal-rules/{rule_id}"): ("require_prop_permission", ("rates.manage",)),
    ("POST", "/rates/calendar"): ("require_prop_permission", ("rates.update",)),
    ("POST", "/rates/calendar/batch"): ("require_prop_permission", ("rates.update",)),
    ("POST", "/rates/calendar/generate"): ("require_prop_permission", ("rates.manage",)),
    ("POST", "/rates/promotions"): ("require_prop_permission", ("rates.manage",)),
    ("GET", "/rates/contracts"): ("require_prop_permission", ("rates.read",)),
    ("POST", "/rates/contracts"): ("require_prop_permission", ("rates.manage",)),
    ("PUT", "/rates/contracts/{contract_id}"): ("require_prop_permission", ("rates.update",)),
    ("DELETE", "/rates/contracts/{contract_id}"): ("require_prop_permission", ("rates.manage",)),
    ("POST", "/rates/contracts/validate"): ("require_prop_permission", ("rates.read",)),
}

# Excepciones globales documentadas (ruta → dependency/código).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("GET", "/rates/options"): ("require_permission", ("rates.read",)),
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    """(método, path) → (dependency, códigos) del primer Depends en la firma.

    Soporta firmas de una línea (``def f(x):``) y multilínea (``):``), y
    decoradores ``@api_router.*(...)`` multilínea (normalizados antes).
    """
    raw = (SERVER_ROOT / "src/app/modules/partner/routes/rates.py").read_text(encoding="utf-8")
    normalized: list[str] = []
    i = 0
    lines = raw.splitlines()
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("@api_router.") and "(" in line:
            depth = line.count("(") - line.count(")")
            joined = line
            while depth > 0 and i + 1 < len(lines):
                i += 1
                nxt = lines[i]
                joined += " " + nxt.strip()
                depth += nxt.count("(") - nxt.count(")")
            normalized.append(joined)
        else:
            normalized.append(line)
        i += 1
    text = "\n".join(normalized)
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
                    codes = frozenset(re.findall(r'"([^"]+)"', g.group(2)))
                    mapping[current] = (g.group(1), codes)
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
                codes = frozenset(re.findall(r'"([^"]+)"', g.group(2)))
                mapping[current] = (g.group(1), codes)
            current = None
    return mapping


def test_operation_routes_use_prop_gates() -> None:
    actual = _route_gates()
    missing = sorted(set(EXPECTED_PROP_ROUTES) - set(actual))
    assert not missing, f"rutas rates sin parsear: {missing}"
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
    assert not unclassified, f"rutas rates sin clasificar: {unclassified}"
