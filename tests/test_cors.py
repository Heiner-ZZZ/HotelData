"""Tests for the CORS middleware (allowlist driven by env).

The middleware is configured from `config/settings.py`:
- `CORS_ALLOWED_ORIGINS` (comma-separated)
- `CORS_ALLOWED_METHODS` (comma-separated)
- `CORS_ALLOWED_HEADERS` (comma-separated)

Defaults in `config/settings.py` match the previous hardcoded values
plus an explicit list of methods and headers. These tests verify that:
1. Preflight from an allowed origin is answered with the CORS headers.
2. Preflight from a non-allowed origin is rejected.
3. Simple GET from a non-allowed origin does NOT leak `Access-Control-*`
   headers.
4. The configured allowlist is the one used (no wildcards).
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.app.main import create_app


pytestmark = pytest.mark.asyncio


ALLOWED_ORIGIN = "http://localhost:4200"
EVIL_ORIGIN = "http://evil.example.com"


@pytest_asyncio.fixture
async def cors_client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac


async def test_preflight_from_allowed_origin_is_accepted(cors_client):
    response = await cors_client.options(
        "/api/auth/me",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "GET" in allowed_methods
    assert "OPTIONS" in allowed_methods


async def test_preflight_from_disallowed_origin_is_blocked(cors_client):
    response = await cors_client.options(
        "/api/auth/me",
        headers={
            "Origin": EVIL_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    # Starlette's CORS middleware responds without allow-origin for
    # disallowed origins. Status is 200 (preflight handled) but no
    # `access-control-allow-origin` header.
    assert response.headers.get("access-control-allow-origin") != EVIL_ORIGIN
    # The response should not echo the evil origin in any CORS header
    assert EVIL_ORIGIN not in response.headers.get("access-control-allow-origin", "")


async def test_simple_get_from_disallowed_origin_does_not_leak_cors_headers(cors_client):
    response = await cors_client.get(
        "/api/auth/me",
        headers={"Origin": EVIL_ORIGIN},
    )
    # 401 from the middleware because we're not authenticated is fine.
    # The point: CORS headers must NOT be set for a disallowed origin.
    assert response.headers.get("access-control-allow-origin") != EVIL_ORIGIN


async def test_credentials_header_is_set_for_allowed_origin(cors_client):
    response = await cors_client.options(
        "/api/auth/me",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


async def test_allowed_headers_are_explicit_not_wildcard(cors_client):
    response = await cors_client.options(
        "/api/auth/me",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    allowed_headers = response.headers.get("access-control-allow-headers", "")
    # Wildcard "*" must NOT be present (would mean a future header slips
    # through).
    assert "*" not in allowed_headers
    # The headers we actually use must be there.
    normalized = {h.strip().lower() for h in allowed_headers.split(",")}
    assert "authorization" in normalized
    assert "content-type" in normalized
