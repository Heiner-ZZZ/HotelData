from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from src.app.security.navigation import get_default_redirect_for_role, get_navigation_for_user
from src.app.security.permissions import get_user_permission_codes, user_has_permission
from src.app.security.role_helpers import get_role_name
from src.app.security.route_permissions import get_access_rule, is_public_path, role_allowed
from src.app.security.session import SESSION_COOKIE_NAME, get_current_user
from src.database.connection import get_database



def _login_redirect(request: Request) -> RedirectResponse:
    next_path = request.url.path
    if request.url.query:
        next_path = f"{next_path}?{request.url.query}"
    return RedirectResponse(f"/login?next={quote(next_path, safe='/?=&')}", status_code=303)


async def role_access_middleware(request: Request, call_next):
    path = request.url.path
    is_api_request = path.startswith("/api/")
    if is_public_path(path):
        request.state.current_user = None
        request.state.navigation = get_navigation_for_user(None)
        return await call_next(request)

    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    request.state.current_user = user
    request.state.current_session = session
    permission_codes = get_user_permission_codes(db, user) if user else set()
    request.state.permission_codes = permission_codes
    request.state.navigation = get_navigation_for_user(user, permission_codes)

    if path == "/":
        if not user:
            return RedirectResponse("/login", status_code=303)
        return RedirectResponse(get_default_redirect_for_role(get_role_name(user)), status_code=303)

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

    if path.startswith("/auth/"):
        return await call_next(request)

    rule = get_access_rule(path, request.method)
    allowed = True
    if rule:
        allowed = False
        if rule.roles and role_allowed(user, rule.roles):
            allowed = True
        if rule.permission and user_has_permission(db, user, rule.permission):
            allowed = True

    if not allowed:
        if is_api_request:
            return JSONResponse(
                status_code=403,
                content={
                    "authenticated": True,
                    "detail": "Forbidden",
                    "required_permission": rule.permission if rule else None,
                    "allowed_roles": list(rule.roles) if rule else [],
                },
            )
        return JSONResponse(
            status_code=403,
            content={
                "authenticated": True,
                "detail": "Forbidden",
                "required_permission": rule.permission if rule else None,
                "allowed_roles": list(rule.roles) if rule else [],
            },
        )

    return await call_next(request)
