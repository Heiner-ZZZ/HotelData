"""Tests for the auth flow: login, logout, current-user.

These tests exercise the *real* Mongo against a dedicated test database
(`hoteldata_hub_test`, set in `conftest.py`). They never touch the dev
or prod database.
"""
from __future__ import annotations

import pytest

from src.app.security.session import SESSION_COOKIE_NAME, hash_session_token, get_session
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


async def test_me_unauthenticated_returns_401(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    body = response.json()["detail"]
    assert body["authenticated"] is False
    assert body["login_url"] == "/login"


async def test_me_authenticated_returns_user(client, cliente_user):
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["user"]["username"] == cliente_user["username"]
    assert payload["user"]["primary_role"] == "cliente"



async def test_login_inactive_user_returns_specific_message(client, db):
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
    assert "Cuenta desactivada" in response.json()["detail"]


async def test_login_creates_only_one_active_session(client, db, cliente_user):
    """RN-004: New login invalidates previous session, so only one
    active session exists per user at any time."""
    # First login
    response1 = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert response1.status_code == 200
    session_token_1 = response1.cookies.get("hoteldata_session")
    assert session_token_1 is not None

    # Second login -- should invalidate the first session
    response2 = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert response2.status_code == 200
    session_token_2 = response2.cookies.get("hoteldata_session")
    assert session_token_2 is not None
    assert session_token_2 != session_token_1, "second login must issue a new token"

    # First session should now be inactive
    first_session = db.user_sessions.find_one({"session_token_hash": hash_session_token(session_token_1)})
    assert first_session is not None
    assert first_session.get("is_active") is False, "first session must be invalidated"
    assert first_session.get("end_reason") == "new_login"

    # Verify token 1 is no longer valid
    session_1_check = get_session(db, session_token_1)
    assert session_1_check is None, "first session token should not resolve"


async def test_logout_invalidates_session_and_clears_cookie(client, db, cliente_user):
    """CA-001/002/003/006: Logout invalidates session server-side,
    deletes the cookie, redirects to /login, and logs the action."""
    # Login first
    await login(client, cliente_user["username"], cliente_user["password"])
    token_before = client.cookies.get(SESSION_COOKIE_NAME)
    assert token_before is not None

    # Logout
    response = await client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login"

    # Cookie should be deleted (Set-Cookie with max-age=0 or expired)
    set_cookie = response.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()

    # Session should be invalidated in DB
    session_doc = db.user_sessions.find_one({"session_token_hash": hash_session_token(token_before)})
    assert session_doc is not None
    assert session_doc.get("is_active") is False
    assert session_doc.get("end_reason") == "logout"

    # Activity log should record the logout
    log_entry = db.user_activity_logs.find_one({"action": "auth.logout"})
    assert log_entry is not None
    assert str(log_entry["user_id"]) == cliente_user["user_id"]

    # Token should no longer resolve
    assert get_session(db, token_before) is None


async def test_logout_without_session_does_not_error(client, db):
    """Logout without an active session should not raise an error."""
    response = await client.get("/auth/logout", follow_redirects=False)
    # Should still redirect to /login gracefully
    assert response.status_code in (303, 302)
    assert "login" in response.headers.get("location", "")
