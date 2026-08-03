"""Tests for the analytics ClickHouse health endpoint (/api/analytics/health)."""

from __future__ import annotations

import pytest

from tests.conftest import login


pytestmark = pytest.mark.asyncio


async def test_analytics_health_requires_auth(client):
    """The endpoint is not public — unauthenticated API callers get 401."""
    response = await client.get("/api/analytics/health")
    assert response.status_code == 401


async def test_analytics_health_returns_clickhouse_status(client, admin_user):
    """Authenticated request returns 200 with the expected diagnostic shape.

    Works whether ClickHouse is reachable (connected=True) or not
    (connected=False + error) — the endpoint must never 500.
    """
    assert (await login(client, admin_user["username"], admin_user["password"])) == 200

    response = await client.get("/api/analytics/health")
    assert response.status_code == 200
    data = response.json()

    # Shape contract
    assert set(data.keys()) == {
        "connected",
        "host",
        "port",
        "database",
        "user",
        "version",
        "error",
    }
    # Config echo must never be None/empty
    assert data["host"]
    assert isinstance(data["port"], int)
    assert data["database"]
    assert data["user"]

    # Reachable → version + no error; unreachable → error present
    if data["connected"]:
        assert data["error"] is None
        assert data["version"]
    else:
        assert data["error"], "expected a non-empty error when unreachable"


async def test_analytics_health_settings_defaults(monkeypatch):
    """CLICKHOUSE_* settings resolve to documented defaults without env."""
    for var in (
        "CLICKHOUSE_HOST",
        "CLICKHOUSE_PORT",
        "CLICKHOUSE_USER",
        "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_DB",
    ):
        monkeypatch.delenv(var, raising=False)

    from config.settings import get_settings

    settings = get_settings()
    assert settings.clickhouse_host == "localhost"
    assert settings.clickhouse_port == 8123
    assert settings.clickhouse_user == "default"
    assert settings.clickhouse_database == "hoteldata"
    assert settings.clickhouse_password == ""
