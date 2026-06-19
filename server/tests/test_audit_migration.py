"""Smoke tests for the audit module migration (Phase 2 / ADR-0006).

After Phase 2, the canonical `audit` bounded context lives in
`src/app/modules/audit/`. The legacy files in `src/app/features/audit/`
are still on disk but no longer mounted in `src/app.main`. These tests
lock in the wiring so a future refactor cannot silently unmount the
canonical routes.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio



async def test_api_audit_activity_endpoint_is_registered(client: AsyncClient):
    """GET /api/audit/activity must be served and return JSON shape."""
    response = await client.get("/api/audit/activity", follow_redirects=False)
    # Unauthenticated API request → 401 JSON from middleware
    assert response.status_code == 401
    body = response.json()
    assert body["authenticated"] is False


async def test_modules_audit_status_endpoint_exists(client: AsyncClient):
    """GET /modules/audit/status must be served (module status endpoint).

    Note: this is a web route (not /api/*), so the middleware
    redirects unauthenticated requests to /login?next=... (303),
    not the 401 JSON reserved for /api/*.
    """
    response = await client.get("/modules/audit/status", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


async def test_no_duplicate_audit_route_registration():
    """The same path must not be served by two different modules.

    This catches a regression where someone re-mounts the legacy
    `features/audit` router on top of `modules/audit`.
    """
    from src.app.main import create_app

    app = create_app()
    audit_paths: dict[str, set[str]] = {}
    for r in app.routes:
        if hasattr(r, "path") and "audit" in r.path.lower():
            ep = getattr(r, "endpoint", None)
            mod = ep.__module__ if ep else "?"
            audit_paths.setdefault(r.path, set()).add(mod)
    # Every audit path is served by exactly one module.
    for path, modules in audit_paths.items():
        assert len(modules) == 1, f"{path} served by multiple modules: {modules}"
        # And that module must be modules/audit, not features/audit.
        (single_module,) = modules
        assert single_module == "src.app.modules.audit.routes", (
            f"{path} served by {single_module}, expected src.app.modules.audit.routes"
        )
