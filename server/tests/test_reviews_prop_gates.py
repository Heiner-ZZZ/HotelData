"""Invariante de migración E (2026-08): reseñas — moderación/staff POR HOTEL.

Rutas de ``reviews/routes.py``: las de STAFF/moderación gatean con
``require_prop_permission`` (``reviews.read`` lecturas, ``reviews.moderate``
moderación/borrado). Deny-by-default: sin role_assignment → 403; sin
prop_id → 400; reseña de otro hotel → 404.

Excepciones globales documentadas (auto-servicio del huésped / autor / vista
pública):
- GET ``/api/hotels/{prop_id}/reviews`` — público (sin auth).
- POST ``""``, POST ``/staff``, POST ``/guest`` — creación de reseña
  (huésped / asistida por staff en check-out / anónima). Flujos del autor.
- PUT ``/{review_id}`` — el AUTOR edita su reseña pendiente (ownership).
- POST ``/{review_id}/report`` — cualquier usuario autenticado reporta.
- GET ``/{review_id}`` — lectura por autor/autenticado.
- GET ``""`` — MIXTO: el huésped lista sus reseñas; con ``prop_id`` el
  handler aplica el gate por-hotel INLINE (staff).
- PATCH ``/{review_id}/respond`` — rol fijo ``hotel_partner``/super_admin
  + gate por-hotel INLINE (se prop-gatea con ``reviews.read``).
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_ROUTES: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("PATCH", "/{review_id}/moderate"): ("require_prop_permission", ("reviews.moderate",)),
    ("DELETE", "/{review_id}"): ("require_prop_permission", ("reviews.moderate",)),
    ("GET", "/reputation/analytics"): ("require_prop_permission", ("reviews.read",)),
    ("GET", "/reputation/dashboard"): ("require_prop_permission", ("reviews.read",)),
}

# Excepciones globales (dependency actual). Las de flujo huésped/autor se
# dejan igual; GET "" y respond conservan require_login y el gate por-hotel
# se aplica INLINE (mixto huésped/staff). GET /reports es la COLA de
# moderación multi-hotel (el handler no filtra por prop_id — vista de
# gerencia, excepción global documentada).
GLOBAL_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("POST", ""): "require_login",
    ("POST", "/staff"): "require_login",
    ("POST", "/guest"): "no-auth",
    ("GET", ""): "require_login",
    ("PATCH", "/{review_id}/respond"): "require_login",
    ("PUT", "/{review_id}"): "require_login",
    ("POST", "/{review_id}/report"): "require_login",
    ("GET", "/{review_id}"): "require_login",
    ("GET", "/reports"): "require_login",
}


def _route_gates() -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    text = (SERVER_ROOT / "src/app/modules/reviews/routes.py").read_text(encoding="utf-8")
    route_re = re.compile(r"@api_router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")
    gate_re = re.compile(
        r"Depends\(\s*"
        r"(require_any_prop_permission|require_prop_permission|require_any_permission|require_permission)"
        r"\(\s*\"([^\"]+)\"|Depends\(\s*(require_login)\s*\)",
        re.S,
    )

    def _parse(g) -> tuple[str, frozenset[str]]:
        if g.group(3):
            return (g.group(3), frozenset())
        return (g.group(1), frozenset({g.group(2)}))

    mapping: dict[tuple[str, str], tuple[str, frozenset[str]]] = {}
    current: tuple[str, str] | None = None
    block: list[str] = []
    for line in text.splitlines():
        m = route_re.search(line)
        if m:
            if current is not None:
                g = gate_re.search("\n".join(block))
                if g and current not in mapping:
                    mapping[current] = _parse(g)
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
                mapping[current] = _parse(g)
            current = None
    return mapping


def test_operation_routes_use_prop_gates() -> None:
    actual = _route_gates()
    missing = sorted(set(EXPECTED_PROP_ROUTES) - set(actual))
    assert not missing, f"rutas reviews sin parsear: {missing}"
    bad = {
        f"{m} {p}": (expected, actual.get((m, p)))
        for (m, p), expected in EXPECTED_PROP_ROUTES.items()
        if actual.get((m, p)) != (expected[0], frozenset(expected[1]))
    }
    assert not bad, f"rutas de operación sin gate por-hotel correcto: {bad}"


def test_global_exceptions_keep_global_gate() -> None:
    actual = _route_gates()
    for (m, p), expected_dep in GLOBAL_EXCEPTIONS.items():
        if expected_dep == "no-auth":
            continue
        gate = actual.get((m, p))
        assert gate is not None, f"{m} {p}: sin gate parseado"
        assert gate[0] == expected_dep, f"excepción {m} {p}: {gate}"


def test_all_routes_classified() -> None:
    actual = _route_gates()
    known = set(EXPECTED_PROP_ROUTES) | set(GLOBAL_EXCEPTIONS)
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"rutas reviews sin clasificar: {unclassified}"
