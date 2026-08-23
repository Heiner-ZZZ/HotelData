"""Opción 2 (2026-08): los selectores de scope NO exigen códigos de permiso.

El scope sale de ``assigned_hotels`` (deny-by-default por rol restringido), no
de códigos globales:

- ``GET /api/management/properties/context`` y ``/properties/options`` →
  ``require_login`` (bootstrap del contexto + picker). Un usuario housekeeping
  con el template canónico (que NO porta properties.read/reservations.read)
  debe poder arrancar la app y usar el selector.
- ``GET /api/management/amenities/options`` → ``require_login``; cuando llega
  ``prop_id`` el catálogo queda restringido por ASIGNACIÓN (cross-hotel → 403).
- ``GET /api/management/reports`` → ``require_any_permission("reports.read",
  "dashboard.read")``: el gerente (template sin reports.read) conserva la
  página de Reportes; un cliente (sin dashboard.read) sigue fuera.

RED: estos tests fallan con los gates globales actuales (403 para housekeeping
en context/options/amenities y para el gerente en reports).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from passlib.context import CryptContext

from scripts.init_security_model_ga03 import ROLE_PERMISSION_CODES

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_PASSWORD = "Pass123!"


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_role(db, role_name: str) -> None:
    db.roles.insert_one(
        {
            "role_name": role_name,
            "display_name": role_name.replace("_", " ").title(),
            "permissions": list(ROLE_PERMISSION_CODES.get(role_name, [])),
            "is_system": True,
            "created_at": _now(),
        }
    )


def _seed_user(db, *, username: str, role: str, assigned_hotels: list[int] | None) -> dict:
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash(_PASSWORD),
            "primary_role": role,
            "role_ids": [],
            "assigned_hotels": assigned_hotels,
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": username, "password": _PASSWORD}


def _seed_hotels(db) -> None:
    db.dim_hotels.insert_many(
        [
            {"prop_id": 1, "hotel_name": "Hotel Uno", "display_name": "Hotel Uno"},
            {"prop_id": 2, "hotel_name": "Hotel Dos", "display_name": "Hotel Dos"},
        ]
    )


async def _login(client, creds: dict) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text


@pytest.fixture
def housekeeping_creds(db) -> dict:
    """Rol GLOBAL housekeeping canónico (SIN properties.read/reservations.read/
    amenities.read) + 1 hotel asignado — el escenario post-sync de Fase 5."""
    _seed_role(db, "housekeeping")
    return _seed_user(db, username="hk_scope", role="housekeeping", assigned_hotels=[1])


@pytest.fixture
def gerente_creds(db) -> dict:
    """Rol GLOBAL gerente_hotel canónico (49 códigos, SIN reports.read) + 1 hotel."""
    _seed_role(db, "gerente_hotel")
    return _seed_user(db, username="gerente_scope", role="gerente_hotel", assigned_hotels=[1])


# ── properties/context + properties/options: login-only, scope por asignación ──


@pytest.mark.asyncio
async def test_properties_context_login_only_housekeeping(client, db, housekeeping_creds):
    """Housekeeping SIN códigos globales de selector arranca la app: context 200."""
    _seed_hotels(db)
    await _login(client, housekeeping_creds)

    resp = await client.get("/api/management/properties/context")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["mode"] == "single"
    assert payload["default_prop_id"] == 1
    assert [p["prop_id"] for p in payload["assigned_properties"]] == [1]


@pytest.mark.asyncio
async def test_properties_options_login_only_scoped(client, db, housekeeping_creds):
    """El picker devuelve SOLO los hoteles asignados (deny-by-default)."""
    _seed_hotels(db)
    await _login(client, housekeeping_creds)

    resp = await client.get(
        "/api/management/properties/options",
        params={"q": "", "page": 1, "page_size": 10},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert [p["prop_id"] for p in payload["properties"]] == [1]


# ── amenities/options: login-only; catálogo por asignación ──


@pytest.mark.asyncio
async def test_amenities_options_no_prop_login_only(client, db, housekeeping_creds):
    """Sin prop_id: lista ligera de propiedades del scope (sin código global)."""
    _seed_hotels(db)
    await _login(client, housekeeping_creds)

    resp = await client.get("/api/management/amenities/options")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert [p["prop_id"] for p in payload["properties"]] == [1]


@pytest.mark.asyncio
async def test_amenities_options_catalog_in_scope(client, db, housekeeping_creds):
    """Con prop_id del hotel asignado: catálogo 200 (scope por asignación)."""
    _seed_hotels(db)
    await _login(client, housekeeping_creds)

    resp = await client.get("/api/management/amenities/options", params={"prop_id": 1})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "properties" in payload
    assert "catalog" in payload  # rama catálogo ejecutada


@pytest.mark.asyncio
async def test_amenities_options_catalog_cross_hotel_403(client, db, housekeeping_creds):
    """prop_id de OTRO hotel (no asignado) → 403 (sin fuga cross-hotel)."""
    _seed_hotels(db)
    await _login(client, housekeeping_creds)

    resp = await client.get("/api/management/amenities/options", params={"prop_id": 2})
    assert resp.status_code == 403, resp.text


# ── selectores siguen exigiendo login (303 anónimo) ──


@pytest.mark.asyncio
async def test_selectors_401_unauthenticated(client, db):
    """Sin sesión los selectores NO son públicos: 401 (el middleware de API
    devuelve 401 JSON antes de llegar al dependency; el 303 de require_login
    es el fallback de rutas web)."""
    for url in (
        "/api/management/properties/context",
        "/api/management/properties/options",
        "/api/management/amenities/options",
    ):
        resp = await client.get(url)
        assert resp.status_code == 401, f"{url}: {resp.status_code}"


# ── reports: gerente conserva la página (dashboard.read); cliente fuera ──


@pytest.mark.asyncio
async def test_reports_gerente_ok_with_dashboard_read(client, db, gerente_creds):
    """Gerente (template canónico sin reports.read, con dashboard.read) → 200."""
    await _login(client, gerente_creds)

    resp = await client.get("/api/management/reports", params={"page": 1, "page_size": 10})
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_reports_cliente_403_without_dashboard_read(client, db, cliente_user):
    """Cliente (sin reports.read ni dashboard.read) sigue fuera → 403."""
    _seed_role(db, "cliente")
    await _login(client, {"username": cliente_user["username"], "password": cliente_user["password"]})

    resp = await client.get("/api/management/reports")
    assert resp.status_code == 403, resp.text
