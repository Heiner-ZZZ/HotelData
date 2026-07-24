from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from src.app.security.navigation import get_default_redirect_for_role, get_navigation_for_user
from src.app.security.permissions import get_user_permission_codes
from src.app.security.role_helpers import get_role_name
from src.app.security.route_permissions import is_public_path
from src.app.security.session import SESSION_COOKIE_NAME, get_current_user
from src.database.connection import get_database



def _login_redirect(request: Request) -> RedirectResponse:
    next_path = request.url.path
    if request.url.query:
        next_path = f"{next_path}?{request.url.query}"
    return RedirectResponse(f"/login?next={quote(next_path, safe='/?=&')}", status_code=303)


async def role_access_middleware(request: Request, call_next):
    """Authentication-only middleware.

    Responsibilities:
    - Resolve the current user from the session cookie.
    - Redirect unauthenticated users to /login (HTML) or return 401 (API).
    - Inject ``request.state.current_user``, ``permission_codes``, and
      ``navigation`` so downstream handlers don't need to re-query.

    Authorization (who can do what) is handled exclusively by
    ``Depends(require_permission(...))`` at each endpoint — not here.
    """
    path = request.url.path
    is_api_request = path.startswith("/api/")

    # ── Public paths: no auth required ──────────────────────────────────
    if is_public_path(path):
        request.state.current_user = None
        request.state.navigation = get_navigation_for_user(None)
        return await call_next(request)

    # ── Resolve user from session ───────────────────────────────────────
    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    request.state.current_user = user
    request.state.current_session = session
    permission_codes = get_user_permission_codes(db, user) if user else set()
    request.state.permission_codes = permission_codes
    request.state.navigation = get_navigation_for_user(user, permission_codes)

    # ── Root redirect ───────────────────────────────────────────────────
    if path == "/":
        if not user:
            return RedirectResponse("/login", status_code=303)
        return RedirectResponse(get_default_redirect_for_role(get_role_name(user)), status_code=303)

    # ── Unauthenticated → 401 (API) or redirect (HTML) ──────────────────
    if not user:
        if is_api_request:
            return JSONResponse(
                status_code=401,
                content={
                    "authenticated": False,
                    "detail": "Authentication required",
                    "login_url": f"/login?next={quote(path, safe='/?=&')}",
                },
            )
        return _login_redirect(request)

    # ── /auth/* paths manage their own auth (login, register, etc.) ─────
    if path.startswith("/auth/"):
        return await call_next(request)

    # ── All other routes: authorization is delegated to the endpoint ────
    # Each endpoint must use ``Depends(require_permission(...))`` to enforce
    # granular, DB-backed access control.
    return await call_next(request)
