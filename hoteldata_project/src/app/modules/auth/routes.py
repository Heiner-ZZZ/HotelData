from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.app.modules.auth.schemas import ModuleStatus
from src.app.modules.auth.service import module_status
from src.app.security.session import (
    SESSION_COOKIE_NAME,
    create_user_session,
    find_user_by_identifier,
    get_current_user,
    invalidate_session,
    log_user_activity,
    verify_password,
)
from src.app.security.dependencies import require_login
from src.app.security.navigation import get_default_redirect_for_role
from src.app.security.route_permissions import is_safe_internal_next
from src.database.connection import get_database


router = APIRouter(prefix="/modules/auth", tags=["modules-auth"])
web_router = APIRouter(prefix="/auth", tags=["auth"])
api_router = APIRouter(prefix="/api/auth", tags=["auth-api"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return module_status()


@web_router.get("/login")
def login_form(request: Request):
    db = get_database()
    user, _ = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {
            "current_user": user,
            "error": "",
            "identifier": "",
            "next_url": request.query_params.get("next", ""),
        },
    )


@web_router.post("/login")
def login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    next: str = Form(default=""),
):
    db = get_database()
    user = find_user_by_identifier(db, identifier)
    if not user or not user.get("is_active", True) or not verify_password(password, user.get("password_hash", "")):
        log_user_activity(
            db,
            action="auth.login_failed",
            request=request,
            details={"identifier": identifier.strip()},
        )
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "current_user": None,
                "error": "Credenciales inválidas. Revise usuario, correo o contraseña.",
                "identifier": identifier,
                "next_url": next,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_user_session(db, user, request)
    log_user_activity(db, action="auth.login_success", request=request, user=user)
    redirect_url = next if is_safe_internal_next(next) else get_default_redirect_for_role(user.get("primary_role"))
    response = RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=8 * 60 * 60,
        path="/",
    )
    return response


@web_router.get("/logout")
def logout(request: Request):
    db = get_database()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user, _ = get_current_user(db, token)
    invalidate_session(db, token)
    log_user_activity(db, action="auth.logout", request=request, user=user)
    response = RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@web_router.get("/me")
def me(request: Request, current_user: dict = Depends(require_login)):
    db = get_database()
    _, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    home_href = get_default_redirect_for_role(current_user.get("primary_role"))
    return templates.TemplateResponse(
        request,
        "auth/me.html",
        {
            "current_user": current_user,
            "session": session,
            "authenticated": True,
            "home_href": home_href,
        },
    )


@api_router.get("/me")
def me_api(request: Request):
    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "authenticated": False,
                "login_url": "/auth/login",
            },
        )

    home_href = get_default_redirect_for_role(user.get("primary_role"))
    return {
        "authenticated": True,
        "user": {
            "user_id": str(user.get("_id") or user.get("user_id") or ""),
            "username": user.get("username") or "",
            "email": user.get("email") or "",
            "display_name": user.get("display_name") or user.get("full_name") or user.get("username") or "",
            "primary_role": user.get("primary_role") or "",
        },
        "session": {
            "session_token": session.get("session_token") or "",
            "expires_at": session.get("expires_at").isoformat() if hasattr(session.get("expires_at"), "isoformat") else session.get("expires_at"),
            "created_at": session.get("created_at").isoformat() if hasattr(session.get("created_at"), "isoformat") else session.get("created_at"),
        },
        "home_href": home_href,
        "login_url": "/auth/login",
    }
