from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request, status

from src.app.security.permissions import user_has_permission
from src.app.security.session import SESSION_COOKIE_NAME
from src.app.security.session import get_current_user as resolve_current_user
from src.database.connection import get_database


def get_current_user(request: Request) -> dict[str, Any] | None:
    db = get_database()
    user, session = resolve_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    request.state.current_user = user
    request.state.current_session = session
    return user


def require_login(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        detail="Debe iniciar sesión.",
        headers={"Location": "/auth/login"},
    )


def require_permission(permission_code: str) -> Callable[[Request], dict[str, Any]]:
    def dependency(request: Request) -> dict[str, Any]:
        user = require_login(request)
        db = get_database()
        if user_has_permission(db, user, permission_code):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permiso requerido: {permission_code}",
        )

    return dependency
