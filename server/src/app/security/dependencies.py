from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import HTTPException, Request, status

from src.app.modules.partner.services.audit import register_action
from src.app.security.hotel_filter import user_can_access_hotel
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


def require_any_permission(*permission_codes: str) -> Callable[[Request], dict[str, Any]]:
    """Require at least one permission from a set of equivalent capabilities.

    Some workflows span modules: a front-desk check-out operator needs to
    issue/send that booking's invoice without receiving every billing-admin
    capability. This dependency keeps that boundary explicit at the route.
    """
    if not permission_codes:
        raise ValueError("At least one permission code is required")

    def dependency(request: Request) -> dict[str, Any]:
        user = require_login(request)
        db = get_database()
        if any(user_has_permission(db, user, code) for code in permission_codes):
            return user

        username = (user or {}).get("username") or "anonymous"
        required = " or ".join(permission_codes)
        try:
            register_action(
                prop_id=0,
                entity_type="permission",
                entity_id=f"denied:{required}",
                action="access_denied",
                summary=(
                    f"403: {username} tried {request.method} {request.url.path} "
                    f"(requires {required})"
                ),
                changed_by=username,
                metadata={
                    "permissions": list(permission_codes),
                    "path": request.url.path,
                    "method": request.method,
                    "user_id": (user or {}).get("_id"),
                    "ip": request.client.host if request.client else None,
                },
            )
        except Exception:
            _logger.warning(
                "Failed to write access_denied audit for %s on %s %s "
                "(perms=%s); 403 will still fire",
                username,
                request.method,
                request.url.path,
                required,
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permiso requerido: {required}",
        )

    return dependency


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


def _resolve_prop_id(request: Request, explicit: int | None) -> int | None:
    """Resolve the hotel prop_id from an explicit value, path or query params."""
    if explicit is not None:
        return int(explicit)
    raw = request.path_params.get("prop_id") or request.query_params.get("prop_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def require_prop_permission(
    permission_code: str,
    prop_id: int | None = None,
) -> Callable[[Request], dict[str, Any]]:
    """Require a permission scoped to a hotel (Fase 1 RBAC por hotel).

    ``prop_id`` can be passed explicitly at decoration time or resolved from
    the request (``prop_id`` path param → query param). When no prop_id can
    be resolved the request is rejected with 400 (deny-by-default): this
    dependency is only meant for per-hotel routes that must carry a hotel
    context.

    Permission resolution goes through ``user_has_permission(prop_id=...)``
    which consults ``role_assignments`` → ``hotel_roles`` for the hotel
    (with the backward-compatible global fallback when no assignment exists).
    """

    def dependency(request: Request) -> dict[str, Any]:
        user = require_login(request)
        db = get_database()
        pid = _resolve_prop_id(request, prop_id)
        if pid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contexto de hotel requerido (prop_id).",
            )
        # Gate operativo (Fase A): el hotel existe pero NO está publicado
        # (onboarding pendiente de aprobación) → 403 con mensaje claro para
        # el frontend. Si la fila no existe se conserva el comportamiento
        # actual (los chequeos de alcance/permiso siguientes siguen gateando).
        hotel = db.dim_hotels.find_one({"prop_id": pid}, {"published": 1})
        if hotel is not None and hotel.get("published") is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El hotel {pid} no está operativo.",
            )
        # Junta los dos ejes del RBAC: alcance (user_can_access_hotel) + capacidad
        # (user_has_permission con prop_id). Sin esto, un empleado del hotel A
        # podría operar en rutas del hotel B si tuviera asignación en otro lado.
        if not user_can_access_hotel(user, pid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin acceso al hotel {pid}.",
            )
        if user_has_permission(db, user, permission_code, prop_id=pid):
            return user

        # ── Audit the 403 BEFORE raising (same guard as require_permission) ──
        username = (user or {}).get("username") or "anonymous"
        try:
            register_action(
                prop_id=pid,
                entity_type="permission",
                entity_id=f"denied:{permission_code}",
                action="access_denied",
                summary=(
                    f"403: {username} tried {request.method} {request.url.path} "
                    f"(requires {permission_code} in hotel {pid})"
                ),
                changed_by=username,
                metadata={
                    "permission": permission_code,
                    "prop_id": pid,
                    "path": request.url.path,
                    "method": request.method,
                    "user_id": (user or {}).get("_id"),
                    "ip": request.client.host if request.client else None,
                },
            )
        except Exception:
            _logger.warning(
                "Failed to write access_denied audit for %s on %s %s "
                "(perm=%s, prop_id=%s); 403 will still fire",
                username,
                request.method,
                request.url.path,
                permission_code,
                pid,
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permiso requerido: {permission_code}",
        )

    return dependency
