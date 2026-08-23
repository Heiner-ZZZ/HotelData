"""Invariante de migración E (2026-08): propiedades y habitaciones POR HOTEL.

Rutas de OPERACIÓN de ``partner/routes/hotels.py`` (propiedades),
``rooms.py`` (habitaciones), ``room_features.py`` (características por tipo
de habitación) y ``content.py`` (contenido e imágenes de la propiedad):
gatean con ``require_prop_permission`` (``properties.read``/``rooms.read``
para lecturas, ``properties.update``/``rooms.update``/``rooms.manage`` para
escrituras). El rol del hotel es la única fuente de capacidad dentro del
hotel (deny-by-default: sin role_assignment → 403; sin prop_id → 400).

Excepciones documentadas:
- GET ``/properties`` y ``/properties/dashboard`` — vistas MULTI-HOTEL
  (listado enriquecido y dashboard de la cartera; sin prop_id no operan un
  hotel concreto).
- GET ``/properties/context`` y ``/properties/options`` — selectores de SCOPE
  LOGIN-ONLY (Opción 2, 2026-08): sin códigos globales; el modo/picker salen
  de ``assigned_hotels`` (deny-by-default por rol restringido).
- GET ``/properties/{prop_id}/history`` y ``/history/{change_id}`` — auditoría
  del perfil; usa ``audit.read`` (código SYSTEM-SCOPE que los roles de hotel
  no portan por diseño: el historial de cambios es vista de plataforma).
- GET ``/room-features`` y POST ``/room-features/custom`` — catálogo MAESTRO
  global de características (sin prop_id; compartido entre hoteles).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[1]

# (archivo, {ruta → (dependency, códigos)}) — rutas de operación POR HOTEL.
EXPECTED_PROP_ROUTES: dict[str, dict[tuple[str, str], tuple[str, tuple[str, ...]]]] = {
    "hotels.py": {
        ("GET", "/properties/{prop_id}/edit"): ("require_prop_permission", ("properties.read",)),
        ("GET", "/properties/{prop_id}/profile"): ("require_prop_permission", ("properties.read",)),
        ("PUT", "/properties/{prop_id}/profile"): ("require_prop_permission", ("properties.update",)),
        ("GET", "/properties/{prop_id}/operational-calendar"): ("require_prop_permission", ("properties.read",)),
        ("GET", "/properties/{prop_id}"): ("require_prop_permission", ("properties.read",)),
    },
    "rooms.py": {
        ("GET", "/rooms"): ("require_prop_permission", ("rooms.read",)),
        ("POST", "/rooms"): ("require_prop_permission", ("rooms.manage",)),
        ("GET", "/rooms/{room_type_id}"): ("require_prop_permission", ("rooms.read",)),
        ("PUT", "/rooms/{room_type_id}"): ("require_prop_permission", ("rooms.update",)),
        ("POST", "/rooms/{room_type_id}/rooms"): ("require_prop_permission", ("rooms.manage",)),
        ("POST", "/rooms/roh"): ("require_prop_permission", ("rooms.manage",)),
        ("POST", "/rooms/{room_type_id}/image"): ("require_prop_permission", ("rooms.update",)),
        ("DELETE", "/rooms/{room_type_id}"): ("require_prop_permission", ("rooms.manage",)),
    },
    "room_features.py": {
        ("GET", "/room-features/{room_type_id}"): ("require_prop_permission", ("rooms.read",)),
        ("PUT", "/room-features/{room_type_id}"): ("require_prop_permission", ("rooms.update",)),
    },
    "content.py": {
        ("PUT", "/properties/{prop_id}/content"): ("require_prop_permission", ("properties.update",)),
        ("POST", "/properties/{prop_id}/images"): ("require_prop_permission", ("properties.update",)),
        ("POST", "/properties/{prop_id}/images/upload"): ("require_prop_permission", ("properties.update",)),
        ("DELETE", "/properties/{prop_id}/images"): ("require_prop_permission", ("properties.update",)),
        ("PUT", "/properties/{prop_id}/images/reorder"): ("require_prop_permission", ("properties.update",)),
        ("POST", "/properties/{prop_id}/room-types/images/upload"): ("require_prop_permission", ("rooms.update",)),
        ("DELETE", "/properties/{prop_id}/room-types/images"): ("require_prop_permission", ("rooms.update",)),
        ("PUT", "/properties/{prop_id}/room-types/{room_type_id}/images/reorder"): ("require_prop_permission", ("rooms.update",)),
    },
}

# Excepciones globales documentadas por archivo.
GLOBAL_EXCEPTIONS: dict[str, dict[tuple[str, str], tuple[str, tuple[str, ...]]]] = {
    "hotels.py": {
        ("GET", "/properties"): ("require_permission", ("properties.read",)),
        ("GET", "/properties/dashboard"): ("require_permission", ("dashboard.read",)),
        ("GET", "/properties/{prop_id}/history"): ("require_permission", ("audit.read",)),
        ("GET", "/properties/{prop_id}/history/{change_id}"): ("require_permission", ("audit.read",)),
    },
    "rooms.py": {
        ("GET", "/rooms/options"): ("require_permission", ("rooms.read",)),
    },
    "room_features.py": {
        ("GET", "/room-features"): ("require_permission", ("rooms.read",)),
        ("POST", "/room-features/custom"): ("require_permission", ("rooms.update",)),
    },
}

# Selectores de scope (Opción 2): login-only — el invariante exige
# ``require_login`` exacto para estas rutas.
LOGIN_ONLY_ROUTES: dict[str, frozenset[tuple[str, str]]] = {
    "hotels.py": frozenset({
        ("GET", "/properties/context"),
        ("GET", "/properties/options"),
    }),
}


def _route_gates(path: Path) -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    """(método, path) → (dependency, códigos) del primer Depends en la firma.

    Soporta firmas de una línea (``def f(x):``) y multilínea (``):``), y
    decoradores ``@api_router.*(...)`` multilínea (normalizados antes).
    """
    raw = path.read_text(encoding="utf-8")
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
        r"Depends\(\s*(require_login|require_any_prop_permission|require_prop_permission|"
        r"require_any_permission|require_permission)"
        r"(?:\(\s*(.*?)\s*\)\s*)?\)",
        re.DOTALL,
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
                    codes = frozenset(re.findall(r'"([^"]+)"', g.group(2) or ""))
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
                codes = frozenset(re.findall(r'"([^"]+)"', g.group(2) or ""))
                mapping[current] = (g.group(1), codes)
            current = None
    return mapping


ROUTES_DIR = SERVER_ROOT / "src/app/modules/partner/routes"


@pytest.mark.parametrize("filename", sorted(EXPECTED_PROP_ROUTES))
def test_operation_routes_use_prop_gates(filename: str) -> None:
    actual = _route_gates(ROUTES_DIR / filename)
    expected = EXPECTED_PROP_ROUTES[filename]
    missing = sorted(set(expected) - set(actual))
    assert not missing, f"{filename}: rutas sin parsear: {missing}"
    bad = {
        f"{m} {p}": (exp, actual.get((m, p)))
        for (m, p), exp in expected.items()
        if actual.get((m, p)) != (exp[0], frozenset(exp[1]))
    }
    assert not bad, f"{filename}: rutas de operación sin gate por-hotel correcto: {bad}"


@pytest.mark.parametrize("filename", sorted(GLOBAL_EXCEPTIONS))
def test_global_exceptions_keep_global_gate(filename: str) -> None:
    actual = _route_gates(ROUTES_DIR / filename)
    for (m, p), expected in GLOBAL_EXCEPTIONS[filename].items():
        gate = actual.get((m, p))
        assert gate == (expected[0], frozenset(expected[1])), f"{filename}: excepción {m} {p}: {gate}"


@pytest.mark.parametrize("filename", sorted(LOGIN_ONLY_ROUTES))
def test_scope_selectors_use_login_only(filename: str) -> None:
    actual = _route_gates(ROUTES_DIR / filename)
    for (m, p) in LOGIN_ONLY_ROUTES[filename]:
        gate = actual.get((m, p))
        assert gate == ("require_login", frozenset()), f"{filename}: selector {m} {p} espera require_login: {gate}"


@pytest.mark.parametrize("filename", sorted(set(EXPECTED_PROP_ROUTES) | set(GLOBAL_EXCEPTIONS) | set(LOGIN_ONLY_ROUTES)))
def test_all_routes_classified(filename: str) -> None:
    actual = _route_gates(ROUTES_DIR / filename)
    known = (
        set(EXPECTED_PROP_ROUTES.get(filename, {}))
        | set(GLOBAL_EXCEPTIONS.get(filename, {}))
        | set(LOGIN_ONLY_ROUTES.get(filename, frozenset()))
    )
    unclassified = sorted(set(actual) - known)
    assert not unclassified, f"{filename}: rutas sin clasificar: {unclassified}"
