"""Tests for the auth flow: login, logout, current-user.

These tests exercise the *real* Mongo against a dedicated test database
(`hoteldata_hub_test`, set in `conftest.py`). They never touch the dev
or prod database.
"""
from __future__ import annotations

import pytest

from src.app.security.session import SESSION_COOKIE_NAME
from tests.conftest import login


pytestmark = pytest.mark.asyncio


async def test_login_api_success_sets_session_cookie(client, cliente_user):
    response = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["username"] == cliente_user["username"]
    assert payload["user"]["primary_role"] == "cliente"
    # Server sets the session cookie
    assert SESSION_COOKIE_NAME in response.cookies


async def test_login_api_accepts_email_as_identifier(client, cliente_user):
    response = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["email"], "password": cliente_user["password"]},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == cliente_user["email"]


async def test_login_api_accepts_explicit_login_alias(client, db):
    from tests.conftest import _seed_user

    user = _seed_user(
        db,
        username="alias_login_user",
        email="alias-login@example.com",
        password="Secret123!",
        role="cliente",
    )
    db.users.update_one(
        {"username": user["username"]},
        {"$set": {"login_aliases": ["Visible Login Name"]}},
    )

    response = await client.post(
        "/api/auth/login",
        json={"identifier": "Visible Login Name", "password": "Secret123!"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alias_login_user"


async def test_login_api_wrong_password_returns_401(client, cliente_user):
    response = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": "WRONG"},
    )
    assert response.status_code == 401
    assert "Credenciales" in response.json()["detail"] or "inv" in response.json()["detail"].lower()
    assert SESSION_COOKIE_NAME not in response.cookies


async def test_login_api_unknown_user_returns_401(client):
    response = await client.post(
        "/api/auth/login",
        json={"identifier": "ghost_user", "password": "whatever"},
    )
    assert response.status_code == 401


async def test_login_api_missing_fields_returns_400(client):
    response = await client.post("/api/auth/login", json={"identifier": ""})
    assert response.status_code == 400


async def test_me_unauthenticated_returns_guest_payload(client):
    """/api/auth/me es un endpoint público: sin sesión responde 200 con un
    payload de huésped (authenticated=False), no 401.
    """
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
    assert body["user"] is None
    assert body["session"] is None


async def test_me_authenticated_returns_user(client, cliente_user):
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["username"] == cliente_user["username"]
    assert payload["user"]["primary_role"] == "cliente"



async def test_login_inactive_user_is_rejected(client, db):
    from tests.conftest import _seed_user

    _seed_user(
        db,
        username="inactive_user",
        email="inactive@example.com",
        password="Secret123!",
        role="cliente",
    )
    db.users.update_one({"username": "inactive_user"}, {"$set": {"is_active": False}})
    response = await client.post(
        "/api/auth/login",
        json={"identifier": "inactive_user", "password": "Secret123!"},
    )
    assert response.status_code == 401
