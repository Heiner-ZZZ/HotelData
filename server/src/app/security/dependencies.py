from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import HTTPException, Request, status

from src.app.modules.partner.services.audit import register_action
from src.app.security.permissions import user_has_permission
from src.app.security.session import SESSION_COOKIE_NAME
from src.app.security.session import get_current_user as resolve_current_user
from src.database.connection import get_database

_logger = logging.getLogger(__name__)


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

        # ── Audit the 403 BEFORE raising ──────────────────────────────
        # Every denied attempt is written to audit_log so SIEM and the
        # /audit admin view surface brute-force / privilege-escalation
        # attempts. Best-effort: a Mongo blip MUST NOT bypass the gate
        # and accidentally allow the request through; the 403 always
        # fires regardless of audit outcome.
        username = (user or {}).get("username") or "anonymous"
        try:
            register_action(
                prop_id=0,
                entity_type="permission",
                entity_id=f"denied:{permission_code}",
                action="access_denied",
                summary=(
                    f"403: {username} tried {request.method} {request.url.path} "
                    f"(requires {permission_code})"
                ),
                changed_by=username,
                metadata={
                    "permission": permission_code,
                    "path": request.url.path,
                    "method": request.method,
                    "user_id": (user or {}).get("_id"),
                    "ip": request.client.host if request.client else None,
                },
            )
        except Exception:
            _logger.warning(
                "Failed to write access_denied audit for %s on %s %s "
                "(perm=%s); 403 will still fire",
                username,
                request.method,
                request.url.path,
                permission_code,
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permiso requerido: {permission_code}",
        )

    return dependency
