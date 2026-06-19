"""Tests for `security/middleware.py`: public paths, auth gates, role checks.

Each test exercises the actual middleware against a real (test) Mongo
through the ASGI transport. No mocks of the auth layer.
"""
from __future__ import annotations

import pytest

from tests.conftest import login


pytestmark = pytest.mark.asyncio


# --- Public paths ---------------------------------------------------------



async def test_static_files_are_public(client):
    # /static/* is whitelisted in route_permissions.PUBLIC_PREFIXES.
    # We don't need the file to exist; the middleware lets the request
    # through and only then FastAPI returns 404 for the missing file.
    response = await client.get("/static/does-not-exist.css")
    assert response.status_code in (200, 404)
    assert response.status_code != 303  # would mean redirect to /login


# --- Unauthenticated requests --------------------------------------------


async def test_unauth_api_returns_401_json(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    body = response.json()["detail"]
    assert body["authenticated"] is False


async def test_unauth_web_route_redirects_to_login(client):
    response = await client.get("/partner/hotels", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


async def test_unauth_root_redirects_to_login(client):
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


# --- Authenticated, wrong role -------------------------------------------


async def test_cliente_blocked_from_admin_api_returns_403(client, cliente_user):
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200
    # /api/admin/* is restricted to super_admin / admin_sistema
    response = await client.get("/api/admin/users")
    assert response.status_code == 403
    body = response.json()
    assert body["authenticated"] is True
    assert body["detail"] == "Forbidden"


async def test_admin_can_access_admin_api(client, admin_user):
    assert (await login(client, admin_user["username"], admin_user["password"])) == 200
    # /api/admin/users exists in src/app/modules/admin/routes.py and
    # super_admin bypasses the role/permission gate via
    # `user_has_permission` (src/app/security/permissions.py:38).
    # Expect 200, not (200, 404): the route is registered and the
    # super_admin always has access.
    response = await client.get("/api/admin/users")
    assert response.status_code == 200


# --- Authenticated, allowed route ----------------------------------------


async def test_authenticated_user_root_redirects_to_role_home(client, cliente_user):
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 303
    # cliente is sent to a cliente-friendly page
    assert response.headers["location"] != "/login"


async def test_cliente_api_me_works(client, cliente_user):
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["primary_role"] == "cliente"
