"""Tests for settings and account endpoints: password change, profile.

These tests exercise the *real* Mongo against a dedicated test database
(`hoteldata_hub_test`, set in `conftest.py`). They never touch the dev
or prod database.
"""
from __future__ import annotations

import pytest

from src.app.security.session import SESSION_COOKIE_NAME, get_session
from tests.conftest import login


pytestmark = pytest.mark.asyncio


async def test_change_password_success(client, db, cliente_user):
    """CA-001: Password change works with correct current password."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.put(
        "/api/settings/password",
        json={"current_password": cliente_user["password"], "new_password": "NuevoPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True

    # Verify new password works for login
    await login(client, cliente_user["username"], "NuevoPass123!")
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["authenticated"] is True


async def test_change_password_wrong_current(client, db, cliente_user):
    """CA-002: Password change fails with incorrect current password."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.put(
        "/api/settings/password",
        json={"current_password": "WrongPass123!", "new_password": "NuevoPass123!"},
    )
    assert response.status_code == 400
    assert "no es correcta" in response.json()["detail"]


async def test_change_password_same_as_current_is_rejected(client, db, cliente_user):
    """RN-001: New password cannot be same as current."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.put(
        "/api/settings/password",
        json={"current_password": cliente_user["password"], "new_password": cliente_user["password"]},
    )
    assert response.status_code == 400
    assert "diferente" in response.json()["detail"].lower()


async def test_change_password_too_short_is_rejected(client, db, cliente_user):
    """RF-002: New password must be at least 8 characters."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.put(
        "/api/settings/password",
        json={"current_password": cliente_user["password"], "new_password": "Ab1"},
    )
    assert response.status_code == 422  # Pydantic validation error


async def test_change_password_logs_activity(client, db, cliente_user):
    """CA-005: Password change logged in user_activity_logs."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    await client.put(
        "/api/settings/password",
        json={"current_password": cliente_user["password"], "new_password": "NuevoPass123!"},
    )

    log = db.user_activity_logs.find_one({"action": "settings.password_changed"})
    assert log is not None
    assert str(log["user_id"]) == cliente_user["user_id"]

    # Restore password for other tests using the same fixture
    db.users.update_one(
        {"username": cliente_user["username"]},
        {"$set": {"password_hash": cliente_user["password"]}},
    )


async def test_change_password_invalidates_sessions(client, db, cliente_user):
    """RF-004/RN-003: Password change invalidates active sessions."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200
    token_before = client.cookies.get(SESSION_COOKIE_NAME)

    await client.put(
        "/api/settings/password",
        json={"current_password": cliente_user["password"], "new_password": "NuevoPass123!"},
    )

    # Old session should be invalidated
    session = get_session(db, token_before)
    assert session is None

    # Need to login again with new password
    assert (await login(client, cliente_user["username"], "NuevoPass123!")) == 200

    # Restore password
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db.users.update_one(
        {"username": cliente_user["username"]},
        {"$set": {"password_hash": pwd.hash(cliente_user["password"])}},
    )


async def test_get_profile_returns_user_data(client, db, cliente_user):
    """CA-004: GET /api/account/profile returns user data."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.get("/api/account/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == cliente_user["user_id"]
    assert data["username"] == cliente_user["username"]
    assert data["email"] == cliente_user["email"]
    assert data["primary_role"] == "cliente"
    # Password hash should NOT be in response
    assert "password_hash" not in data


async def test_update_profile_updates_fields(client, db, cliente_user):
    """RF-005: Profile update works for allowed fields."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.put(
        "/api/account/profile",
        json={"display_name": "Cliente Actualizado", "phone": "+123456789", "email": "nuevo_email@test.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Cliente Actualizado"
    assert data["phone"] == "+123456789"
    assert data["email"] == "nuevo_email@test.com"


async def test_update_profile_invalid_fields_ignored(client, db, cliente_user):
    """RF-005: Only whitelisted fields are updated."""
    assert (await login(client, cliente_user["username"], cliente_user["password"])) == 200

    response = await client.put(
        "/api/account/profile",
        json={"display_name": "Nuevo Nombre", "password_hash": "should_not_be_allowed"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Nuevo Nombre"
    # password_hash should not be updatable via profile
    user = db.users.find_one({"username": cliente_user["username"]})
    assert user["password_hash"] != "should_not_be_allowed"
