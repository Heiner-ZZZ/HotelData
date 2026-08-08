"""Login, logout and session management endpoints."""

from __future__ import annotations


from bson import ObjectId

from bson.errors import InvalidId
from fastapi import APIRouter, Body, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr
from src.app.security.rate_limit import limiter
from src.app.security.role_helpers import get_role_name
from src.app.security.route_permissions import is_safe_internal_next
from src.app.security.session import (
    SESSION_COOKIE_NAME,
    get_current_user,
    invalidate_session,
    log_user_activity,
)
from src.database.connection import get_database

from src.app.modules.auth.schemas import ModuleStatus
from src.app.modules.auth.service import module_status

from ._helpers import (
    _auth_payload,
    _check_account_locked,
    _create_refresh_token,
    _now,
    _record_failed_attempt,
    _reset_failed_attempts,
)


# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ───
# All class declarations BELOW this banner must be on their OWN line.
# The COGS 500 bug taught us: collapsing ``# ─── … ───`` banners onto the
# class declaration line makes Python treat the entire class as comment.
#
# Each model uses ``id: ObjectIdStr = Field(validation_alias=...,
# serialization_alias=...)`` for Mongo ``_id`` coercion. Frontend sees a
# plain string ``session_id`` / ``id`` field — never ``{"$oid": "..."}``.


class UserSessionResponse(BaseModel):
    """One row for ``GET /api/auth/sessions``.

    Wire fields (camelCase-style kept from the legacy dict):
      - ``session_id``     Mongo ``_id`` → plain str (24-char hex)
      - ``is_current``     computed in the route; True if this session
                           matches the requester's ``current_session``
                           ObjectId.
      - ``created_at``     ISO 8601 string (route pre-formats via
                           ``.isoformat()`` for backward compat with the
                           previous dict; Pydantic ``str`` keeps the
                           wire shape stable).
      - ``expires_at``     ISO 8601 string (same convention).
      - ``ip_address``     nullable
      - ``user_agent``     nullable
      - ``remember_me``    bool default False
    """

    session_id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="session_id")
    is_current: bool = False
    created_at: str = ""
    expires_at: str = ""
    ip_address: str | None = None
    user_agent: str | None = None
    remember_me: bool = False

    model_config = ConfigDict(populate_by_name=True)


class UserSessionListEnvelope(BaseModel):
    items: list[UserSessionResponse]
    total: int


class TerminateSessionResponse(BaseModel):
    """Returned by DELETE /api/auth/sessions/{session_id}."""

    ok: bool
    message: str


class TerminateOthersResponse(BaseModel):
    """Returned by POST /api/auth/sessions/terminate-others."""

    ok: bool
    message: str
    terminated_count: int


class AdminSessionResponse(BaseModel):
    """One row for ``GET /api/auth/admin/sessions``.

    Adds ``username`` + ``email`` on top of ``UserSessionResponse``
    because admin users see all sessions across all users.
    """

    session_id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="session_id")
    username: str = ""
    email: str = ""
    created_at: str = ""
    expires_at: str = ""
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AdminSessionListEnvelope(BaseModel):
    items: list[AdminSessionResponse]
    total: int


# Rebuild Pydantic v2 models to resolve string-lazy annotations from
# ``from __future__ import annotations``. Without this explicit rebuild,
# FastAPI's ``TypeAdapter`` binding at ``response_model=...`` raises
# ``pydantic.errors.PydanticUserError`` (``TypeAdapter[… is not fully
# defined``) on the first request to ANY of these endpoints.
UserSessionResponse.model_rebuild()
UserSessionListEnvelope.model_rebuild()
TerminateSessionResponse.model_rebuild()
TerminateOthersResponse.model_rebuild()
AdminSessionResponse.model_rebuild()
AdminSessionListEnvelope.model_rebuild()


router = APIRouter(prefix="/modules/auth", tags=["modules-auth"])


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return module_status()
web_router = APIRouter(prefix="/auth", tags=["auth"])
api_router = APIRouter(prefix="/api/auth", tags=["auth-api"])


@web_router.get("/login")
def login_form(request: Request):
    db = get_database()
    user, _ = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    next_url = request.query_params.get("next", "")
    if user:
        from src.app.security.navigation import get_default_redirect_for_role
        redirect_url = next_url if is_safe_internal_next(next_url) else get_default_redirect_for_role(get_role_name(user))
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)


@web_router.post("/login")
def login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    next: str = Form(default=""),
):
    db = get_database()
    from src.app.security.approval import maybe_apply_rejection_grace
    from src.app.security.session import find_user_by_identifier, verify_password, create_user_session
    user = find_user_by_identifier(db, identifier)
    if user:
        # Gracia perezosa de rechazo (mismo comportamiento que login_api).
        if maybe_apply_rejection_grace(db, user):
            log_user_activity(
                db, action="auth.login_blocked_rejected", request=request,
                details={"identifier": identifier.strip()},
            )
            return JSONResponse(
                {"detail": "Tu registro de alojamiento fue rechazado y la cuenta ya no está activa."},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        _check_account_locked(db, user)
    if not user or not user.get("is_active", True) or not verify_password(password, user.get("password_hash", "")):
        _record_failed_attempt(db, identifier)
        log_user_activity(db, action="auth.login_failed", request=request, details={"identifier": identifier.strip()})
        return JSONResponse(
            {"detail": "Credenciales inválidas. Revise usuario, correo o contraseña."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    _reset_failed_attempts(db, user)
    token = create_user_session(db, user, request)
    log_user_activity(db, action="auth.login_success", request=request, user=user)
    from src.app.security.navigation import get_default_redirect_for_role
    redirect_url = next if is_safe_internal_next(next) else get_default_redirect_for_role(get_role_name(user))
    response = RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME, token,
        httponly=True, samesite="lax",
        max_age=365 * 24 * 60 * 60, path="/",
    )
    return response


@api_router.post("/login")
@limiter.limit("1000/minute")
def login_api(
    request: Request,
    payload: dict = Body(...),
):
    identifier = str(payload.get("identifier") or "").strip()
    password = str(payload.get("password") or "")
    next_url = str(payload.get("next") or "")
    remember_me = bool(payload.get("remember_me", False))

    if not identifier or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ingrese usuario/correo y contraseña.")

    db = get_database()
    from src.app.security.approval import maybe_apply_rejection_grace
    from src.app.security.session import find_user_by_identifier, verify_password, create_user_session
    user = find_user_by_identifier(db, identifier)
    if user:
        # Gracia perezosa de rechazo: si el registro fue rechazado hace más de
        # REJECTION_GRACE_DAYS, la cuenta se desactiva en este login.
        if maybe_apply_rejection_grace(db, user):
            log_user_activity(
                db, action="auth.login_blocked_rejected", request=request,
                details={"identifier": identifier},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tu registro de alojamiento fue rechazado y la cuenta ya no está activa.",
            )
        _check_account_locked(db, user)
    if not user or not user.get("is_active", True) or not verify_password(password, user.get("password_hash", "")):
        _record_failed_attempt(db, identifier)
        log_user_activity(db, action="auth.login_failed", request=request, details={"identifier": identifier})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas. Revise usuario, correo o contraseña.")

    _reset_failed_attempts(db, user)
    token = create_user_session(db, user, request, remember_me=remember_me)
    log_user_activity(db, action="auth.login_success", request=request, user=user)

    _, session = get_current_user(db, token)
    from src.app.security.navigation import get_default_redirect_for_role
    from src.app.security.permissions import get_user_permission_codes
    home_href = next_url if is_safe_internal_next(next_url) else get_default_redirect_for_role(get_role_name(user))

    max_age = 365 * 24 * 60 * 60  # sessions only expire on explicit logout
    codes = get_user_permission_codes(db, user)
    response = JSONResponse(_auth_payload(user, session, home_href, codes))
    response.set_cookie(
        SESSION_COOKIE_NAME, token,
        httponly=True, samesite="lax",
        max_age=max_age, path="/",
    )

    if remember_me:
        refresh_token = _create_refresh_token(db, user)
        response.set_cookie(
            "hoteldata_refresh", refresh_token,
            httponly=True, samesite="lax",
        max_age=365 * 24 * 60 * 60, path="/api/auth/refresh",
        )
    return response


@api_router.get("/sessions", response_model=UserSessionListEnvelope)
def list_own_sessions(request: Request) -> UserSessionListEnvelope:
    db = get_database()
    user, current_session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not current_session:
        raise HTTPException(status_code=401, detail="No autenticado.")
    user_id = user["_id"]
    current_id = current_session["_id"]
    sessions = list(
        db.user_sessions.find(
            {"user_id": user_id, "is_active": True},
        ).sort("created_at", -1)
    )
    return UserSessionListEnvelope(
        items=[
            UserSessionResponse(
                _id=s["_id"],
                is_current=s["_id"] == current_id,
                created_at=s.get("created_at").isoformat() if hasattr(s.get("created_at"), "isoformat") else str(s.get("created_at", "")),
                expires_at=s.get("expires_at").isoformat() if hasattr(s.get("expires_at"), "isoformat") else str(s.get("expires_at", "")),
                ip_address=s.get("ip_address"),
                user_agent=s.get("user_agent"),
                remember_me=bool(s.get("remember_me", False)),
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@api_router.delete("/sessions/{session_id}", response_model=TerminateSessionResponse)
def terminate_own_session(request: Request, session_id: str) -> TerminateSessionResponse:
    db = get_database()
    user, current_session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not current_session:
        raise HTTPException(status_code=401, detail="No autenticado.")
    try:
        oid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de sesión inválido.")
    if oid == current_session["_id"]:
        raise HTTPException(status_code=400, detail="No puedes terminar tu sesión actual. Usa cerrar sesión.")
    result = db.user_sessions.update_one(
        {"_id": oid, "user_id": user["_id"], "is_active": True},
        {"$set": {"is_active": False, "ended_at": _now(), "end_reason": "terminated_by_user"}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o ya inactiva.")
    log_user_activity(db, action="auth.session_terminated", request=request, user=user, details={"session_id": session_id})
    return TerminateSessionResponse(ok=True, message="Sesión terminada.")


@api_router.post("/sessions/terminate-others", response_model=TerminateOthersResponse)
def terminate_other_sessions(request: Request) -> TerminateOthersResponse:
    db = get_database()
    user, current_session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not current_session:
        raise HTTPException(status_code=401, detail="No autenticado.")

    user_id = user["_id"]
    current_id = current_session["_id"]

    result = db.user_sessions.update_many(
        {"user_id": user_id, "is_active": True, "_id": {"$ne": current_id}},
        {"$set": {"is_active": False, "ended_at": _now(), "end_reason": "terminated_by_user_bulk"}},
    )
    count = result.modified_count

    log_user_activity(
        db, action="auth.sessions_terminated_others", request=request, user=user,
        details={"terminated_count": count}
    )
    return TerminateOthersResponse(
        ok=True,
        message=f"Se cerraron {count} sesión(es) en otros dispositivos.",
        terminated_count=count,
    )


@web_router.get("/logout")
def logout(request: Request):
    db = get_database()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user, _ = get_current_user(db, token)
    invalidate_session(db, token)
    log_user_activity(db, action="auth.logout", request=request, user=user)
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie("hoteldata_refresh", path="/api/auth/refresh")
    return response


# ═══════════════════════════════════════════════
# ADMIN session management (all users)
# ═══════════════════════════════════════════════

ADMIN_ROLES = {"super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"}


def _require_admin(user: dict | None) -> None:
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado.")
    role = get_role_name(user)
    if role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores.")


@api_router.get("/admin/sessions", response_model=AdminSessionListEnvelope)
def admin_list_sessions(request: Request) -> AdminSessionListEnvelope:
    """List all active sessions across all users (admin only)."""
    db = get_database()
    user, _ = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    _require_admin(user)

    sessions = list(
        db.user_sessions.find({"is_active": True}).sort("created_at", -1)
    )
    return AdminSessionListEnvelope(
        items=[
            AdminSessionResponse(
                _id=s["_id"],
                username=s.get("username", ""),
                email=s.get("email", ""),
                created_at=s.get("created_at").isoformat() if hasattr(s.get("created_at"), "isoformat") else str(s.get("created_at", "")),
                expires_at=s.get("expires_at").isoformat() if hasattr(s.get("expires_at"), "isoformat") else str(s.get("expires_at", "")),
                ip_address=s.get("ip_address"),
                user_agent=s.get("user_agent"),
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@api_router.post("/admin/sessions/{session_id}/terminate")
def admin_terminate_session(request: Request, session_id: str):
    """Terminate any user's session by session_id (admin only)."""
    db = get_database()
    user, _ = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    _require_admin(user)

    try:
        oid = ObjectId(session_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de sesión inválido.")

    target = db.user_sessions.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    if not target.get("is_active"):
        raise HTTPException(status_code=400, detail="La sesión ya está inactiva.")

    db.user_sessions.update_one(
        {"_id": oid},
        {"$set": {"is_active": False, "ended_at": _now(), "end_reason": "terminated_by_admin"}},
    )

    log_user_activity(
        db, action="auth.admin_session_terminated", request=request, user=user,
        details={"target_session_id": session_id, "target_user": target.get("username", "")},
    )
    return {"ok": True, "message": f"Sesión de {target.get('username', '?')} terminada."}
