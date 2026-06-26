"""Profile, heartbeat, refresh and status endpoints."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from src.app.security.dependencies import require_login
from src.app.security.session import (
    SESSION_COOKIE_NAME,
    create_user_session,
    get_current_user,
    get_session,
    log_user_activity,
)
from src.database.connection import get_database

from ._helpers import (
    REFRESH_TOKEN_TTL_DAYS,
    _auth_payload,
    _create_refresh_token,
    _now,
)

api_router = APIRouter(prefix="/api/auth", tags=["auth-profile"])
web_router = APIRouter(prefix="/auth", tags=["auth"])


@api_router.get("/status")
def auth_status_api(request: Request):
    """Return health/status of the auth module.

    Public endpoint (no auth required). Returns:
    - MongoDB connectivity (ping + server info)
    - Session configuration (TTL, inactivity timeout)
    - Active session counts
    - Server UTC time
    """
    from src.app.security.session import (
        SESSION_TTL_HOURS,
        utc_now,
    )
    from config.settings import get_settings

    status: dict[str, object] = {
        "server": {
            "utc_time": utc_now().isoformat(),
            "timezone": "UTC",
        },
        "config": {
            "session_ttl_hours": SESSION_TTL_HOURS,
            "mongo_database": get_settings().mongo_database,
        },
    }

    # MongoDB connectivity
    try:
        db = get_database()
        # Ping the server to verify connectivity
        db.command("ping")
        # Count active sessions
        active_sessions = db.user_sessions.count_documents({"is_active": True})
        # Count expired/inactive sessions
        inactive_sessions = db.user_sessions.count_documents({"is_active": False})
        status["database"] = {
            "connected": True,
            "active_sessions": active_sessions,
            "inactive_sessions": inactive_sessions,
            "total_sessions": active_sessions + inactive_sessions,
        }
    except Exception as exc:
        status["database"] = {
            "connected": False,
            "error": str(exc),
        }

    return status


@api_router.get("/me")
def me_api(request: Request):
    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not session:
        from src.app.security.navigation import get_navigation_for_user
        return {
            "authenticated": False,
            "user": None,
            "session": None,
            "home_href": None,
            "navigation": get_navigation_for_user(None),
        }
    from src.app.security.navigation import get_default_redirect_for_role
    home_href = get_default_redirect_for_role(user.get("primary_role"))
    return _auth_payload(user, session, home_href)


@web_router.get("/me")
def me(request: Request, current_user: dict = Depends(require_login)):
    from src.app.security.navigation import get_default_redirect_for_role
    redirect_url = get_default_redirect_for_role(current_user.get("primary_role"))
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@api_router.post("/heartbeat")
def heartbeat(
    request: Request,
    current_user: dict = Depends(require_login),
):
    db = get_database()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return {"ok": True}
    session = get_session(db, token)
    return {"ok": True}


@api_router.post("/refresh")
def refresh_session(request: Request, payload: dict = Body(...)):
    raw_token = str(payload.get("refresh_token") or request.cookies.get("hoteldata_refresh") or "").strip()
    if not raw_token:
        raise HTTPException(status_code=400, detail="Refresh token requerido.")

    db = get_database()
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    doc = db.refresh_tokens.find_one({"token_hash": token_hash, "used": False, "expires_at": {"$gt": _now()}})
    if not doc:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado.")

    db.refresh_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used": True}})
    user = db.users.find_one({"_id": doc["user_id"], "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo.")

    new_token = create_user_session(db, user, request, remember_me=True)
    log_user_activity(db, action="auth.refresh", request=request, user=user)
    _, session = get_current_user(db, new_token)
    from src.app.security.navigation import get_default_redirect_for_role
    home_href = get_default_redirect_for_role(user.get("primary_role"))

    new_refresh = _create_refresh_token(db, user)
    response = JSONResponse({
        **_auth_payload(user, session, home_href),
        "refresh_token": new_refresh,
    })
    response.set_cookie(
        SESSION_COOKIE_NAME, new_token,
        httponly=True, samesite="lax",
        max_age=30 * 24 * 60 * 60, path="/",
    )
    response.set_cookie(
        "hoteldata_refresh", new_refresh,
        httponly=True, samesite="lax",
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60, path="/api/auth/refresh",
    )
    return response
