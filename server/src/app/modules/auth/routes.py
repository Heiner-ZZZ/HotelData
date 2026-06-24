from __future__ import annotations

import hashlib
import random
import re as _re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pymongo.errors import DuplicateKeyError

from src.app.email.service import send_email
from src.app.modules.auth.schemas import ModuleStatus
from src.app.modules.auth.service import module_status
from src.app.security.dependencies import require_login
from src.app.security.navigation import get_default_redirect_for_role
from src.app.security.rate_limit import limiter
from src.app.security.route_permissions import is_safe_internal_next
from src.app.security.session import (
    SESSION_COOKIE_NAME,
    INACTIVITY_TIMEOUT_MINUTES,
    create_user_session,
    find_user_by_identifier,
    get_current_user,
    get_session,
    invalidate_session,
    invalidate_user_sessions,
    log_user_activity,
    touch_session_activity,
    verify_password,
    password_context,
)
from src.database.connection import get_database
from config.settings import get_settings


router = APIRouter(prefix="/modules/auth", tags=["modules-auth"])
web_router = APIRouter(prefix="/auth", tags=["auth"])
api_router = APIRouter(prefix="/api/auth", tags=["auth-api"])

LOCK_ATTEMPTS = 5
LOCK_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _auth_payload(user: dict, session: dict | None, home_href: str) -> dict:
    return {
        "authenticated": True,
        "user": {
            "user_id": str(user.get("_id") or user.get("user_id") or ""),
            "username": user.get("username") or "",
            "email": user.get("email") or "",
            "display_name": user.get("display_name") or user.get("full_name") or user.get("username") or "",
            "primary_role": user.get("primary_role") or "",
            "is_active": bool(user.get("is_active", True)),
        },
        "session": {
            "session_token": session.get("session_token_hash", "") if session else "",
            "expires_at": session.get("expires_at").isoformat() if session and hasattr(session.get("expires_at"), "isoformat") else (session.get("expires_at") if session else None),
            "created_at": session.get("created_at").isoformat() if session and hasattr(session.get("created_at"), "isoformat") else (session.get("created_at") if session else None),
        },
        "home_href": home_href,
        "login_url": "/login",
    }


def _check_account_locked(db: Any, user: dict) -> None:
    locked_until = user.get("locked_until")
    if locked_until:
        if isinstance(locked_until, str):
            locked_until = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > _now():
            remaining = int((locked_until - _now()).total_seconds() // 60)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Cuenta bloqueada por múltiples intentos fallidos. Intenta de nuevo en {remaining} minuto(s).",
            )


def _record_failed_attempt(db: Any, identifier: str) -> None:
    user = find_user_by_identifier(db, identifier)
    if not user:
        return
    attempts = (user.get("failed_login_attempts") or 0) + 1
    update: dict[str, Any] = {"failed_login_attempts": attempts}
    if attempts >= LOCK_ATTEMPTS:
        update["locked_until"] = _now() + timedelta(minutes=LOCK_MINUTES)
    db.users.update_one({"_id": user["_id"]}, {"$set": update})


def _reset_failed_attempts(db: Any, user: dict) -> None:
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"failed_login_attempts": 0, "locked_until": None}},
    )


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return module_status()


@web_router.get("/login")
def login_form(request: Request):
    db = get_database()
    user, _ = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    next_url = request.query_params.get("next", "")
    if user:
        redirect_url = next_url if is_safe_internal_next(next_url) else get_default_redirect_for_role(user.get("primary_role"))
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
    user = find_user_by_identifier(db, identifier)
    if user:
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
    redirect_url = next if is_safe_internal_next(next) else get_default_redirect_for_role(user.get("primary_role"))
    response = RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME, token,
        httponly=True, samesite="lax",
        max_age=8 * 60 * 60, path="/",
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
    user = find_user_by_identifier(db, identifier)
    if user:
        _check_account_locked(db, user)
    if not user or not user.get("is_active", True) or not verify_password(password, user.get("password_hash", "")):
        _record_failed_attempt(db, identifier)
        log_user_activity(db, action="auth.login_failed", request=request, details={"identifier": identifier})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas. Revise usuario, correo o contraseña.")

    _reset_failed_attempts(db, user)
    token = create_user_session(db, user, request, remember_me=remember_me)
    log_user_activity(db, action="auth.login_success", request=request, user=user)

    _, session = get_current_user(db, token)
    home_href = next_url if is_safe_internal_next(next_url) else get_default_redirect_for_role(user.get("primary_role"))

    max_age = 30 * 24 * 60 * 60 if remember_me else 8 * 60 * 60
    response = JSONResponse(_auth_payload(user, session, home_href))
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
            max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60, path="/api/auth/refresh",
        )
    return response


# --- Registration with email verification (2-step flow) ---

PENDING_TTL_MINUTES = 15


def _is_email_available(db: Any, email: str) -> bool:
    """Check if email is available (not in use by active or deleted users)"""
    existing = db.users.find_one({"email": email})
    if not existing:
        return True
    # If user was deleted (logical deletion), allow reuse
    if existing.get("deleted_at"):
        return True
    # If user exists and is not deleted, it's not available
    return False


def _is_username_available(db: Any, username: str) -> bool:
    """Check if username is available"""
    existing = db.users.find_one({"username": username})
    if not existing:
        return True
    if existing.get("deleted_at"):
        return True
    return False


@api_router.post("/send-code")
def send_code(
    request: Request,
    payload: dict = Body(...),
):
    """Step 1: Send verification code to email (email-first flow)."""
    email = str(payload.get("email") or "").strip().lower()
    display_name = str(payload.get("display_name") or "").strip() or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="email es requerido.")

    db = get_database()
    if not _is_email_available(db, email):
        raise HTTPException(status_code=400, detail="Este correo ya está registrado como usuario activo.")

    code = f"{random.randint(0, 999999):06d}"
    now = _now()
    pending = {
        "email": email,
        "display_name": display_name,
        "code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "attempts": 0,
        "created_at": now,
        "expires_at": now + timedelta(minutes=PENDING_TTL_MINUTES),
    }
    db.pending_registrations.replace_one(
        {"email": email},
        pending,
        upsert=True,
    )
    _send_verification_code(email, display_name, code)
    log_user_activity(db, action="auth.send_code", request=request, details={"email": email})
    return {
        "ok": True,
        "email": email,
        "message": f"Te enviamos un código de verificación a {email}. Revisa tu bandeja de entrada."
    }


@api_router.post("/register")
def register(
    request: Request,
    payload: dict = Body(...),
):
    username = str(payload.get("username") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    display_name = str(payload.get("display_name") or "").strip() or username
    send_verification = bool(payload.get("send_verification", False))

    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="username, email y password son requeridos.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    db = get_database()
    if not _is_username_available(db, username):
        raise HTTPException(status_code=400, detail="El username ya está registrado.")
    if not _is_email_available(db, email):
        raise HTTPException(status_code=400, detail="El email ya está registrado como usuario activo.")

    if not send_verification:
        # ── Modo directo: crear usuario inmediatamente ──
        now = _now()
        user_doc = {
            "username": username,
            "email": email,
            "password_hash": password_context.hash(password),
            "display_name": display_name,
            "primary_role": "cliente",
            "is_active": True,
            "email_verified": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = db.users.insert_one(user_doc)
        except DuplicateKeyError:
            raise HTTPException(status_code=400, detail="El username o email ya está registrado.")
        user_doc["_id"] = result.inserted_id
        log_user_activity(db, action="auth.register", request=request, user=user_doc)
        return {"ok": True, "message": "Registro exitoso. Ya puedes iniciar sesión."}

    # ── Modo con verificación: enviar código y guardar registro pendiente ──
    code = f"{random.randint(0, 999999):06d}"
    now = _now()
    pending = {
        "username": username,
        "email": email,
        "password_hash": password_context.hash(password),
        "display_name": display_name,
        "code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "attempts": 0,
        "created_at": now,
        "expires_at": now + timedelta(minutes=PENDING_TTL_MINUTES),
    }
    db.pending_registrations.replace_one(
        {"email": email},
        pending,
        upsert=True,
    )
    _send_verification_code(email, display_name, code)
    log_user_activity(db, action="auth.register_pending", request=request, details={"email": email})
    return {
        "ok": True,
        "requires_verification": True,
        "email": email,
        "message": f"Te enviamos un código de verificación a {email}. Revisa tu bandeja de entrada."
    }


@api_router.post("/confirm-code")
def confirm_code(
    request: Request,
    payload: dict = Body(...),
):
    email = str(payload.get("email") or "").strip().lower()
    code = str(payload.get("code") or "").strip()
    # Optional: allow passing full user data for email-first flow
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    display_name = str(payload.get("display_name") or "").strip()

    if not email or not code:
        raise HTTPException(status_code=400, detail="email y code son requeridos.")
    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="El código debe tener 6 dígitos.")

    db = get_database()
    pending = db.pending_registrations.find_one({"email": email})
    if not pending:
        raise HTTPException(status_code=404, detail="No hay registro pendiente para este correo. Solicita un nuevo código.")

    if pending["expires_at"] < _now():
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="El código expiró. Solicita un nuevo registro.")

    if pending["attempts"] >= 5:
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Solicita un nuevo código.")

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if code_hash != pending["code_hash"]:
        db.pending_registrations.update_one(
            {"email": email},
            {"$inc": {"attempts": 1}},
        )
        remaining = 4 - pending["attempts"]
        raise HTTPException(
            status_code=400,
            detail=f"Código incorrecto. Te quedan {remaining} intento(s)."
        )

    # Use data from pending, or override with provided values (email-first flow)
    user_username = username or pending.get("username")
    user_password_hash = pending.get("password_hash") or (password_context.hash(password) if password else None)
    user_display_name = display_name or pending.get("display_name")

    if not user_username or not user_password_hash:
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="Datos de usuario incompletos. Usa el registro completo.")

    now = _now()
    user_doc = {
        "username": user_username,
        "email": email,
        "password_hash": user_password_hash,
        "display_name": user_display_name or user_username,
        "primary_role": "cliente",
        "is_active": True,
        "email_verified": True,
        "failed_login_attempts": 0,
        "locked_until": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = db.users.insert_one(user_doc)
    except DuplicateKeyError:
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="El username o email ya está registrado.")

    user_doc["_id"] = result.inserted_id
    db.pending_registrations.delete_one({"email": email})
    log_user_activity(db, action="auth.register_confirmed", request=request, user=user_doc)
    return {"ok": True, "message": "Cuenta verificada exitosamente. Ya puedes iniciar sesión."}

def _send_verification_code(email: str, display_name: str, code: str) -> None:
    settings = get_settings()
    base_url = (settings.app_base_url or "https://hoteldata.app").rstrip("/")

    # Build digit boxes HTML
    digits_html = ""
    for i, digit in enumerate(code):
        padding = "padding-left:8px;" if i > 0 else ""
        digits_html += (
            f'<td style="width:48px;height:56px;text-align:center;'
            f'font-size:28px;font-weight:800;font-family:monospace;'
            f'color:#162033;background:#f7faff;border:2px solid #d8e0eb;'
            f'border-radius:8px;padding:0;{padding}">'
            f'{digit}'
            f'</td>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Tu código de verificación — HotelData</title>
</head>
<body style="margin:0;padding:0;background-color:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f6fb;padding:24px 0">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:560px">
          <!-- Logo -->
          <tr>
            <td align="center" style="padding:0 0 20px">
              <img src="{base_url}/assets/logo-hoteldata.png" alt="HotelData Hub" width="200" style="display:block;max-width:200px;height:auto;border:0">
            </td>
          </tr>
          <!-- Card -->
          <tr>
            <td style="background:#ffffff;border-radius:12px;padding:40px 36px;box-shadow:0 2px 12px rgba(0,0,0,0.06)">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0 0 8px">
                    <span style="display:inline-block;background:#eef4ff;color:#1463ff;font-size:12px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:6px 16px;border-radius:20px">Código de verificación</span>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 0 20px">
                    <h1 style="margin:0;font-size:22px;font-weight:700;color:#162033">Tu código de verificación</h1>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 0 20px;font-size:15px;line-height:1.7;color:#5f6f87;text-align:center">
                    Hola <strong style="color:#162033">{display_name}</strong>,<br><br>
                    Usa el siguiente código para completar tu registro en <strong>HotelData Hub</strong>:
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 0 24px">
                    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto">
                      <tr>
                        {digits_html}
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 0 24px;font-size:13px;line-height:1.6;color:#8a99b0;text-align:center">
                    Este código expira en <strong>{PENDING_TTL_MINUTES} minutos</strong>.<br>
                    Si no solicitaste este registro, ignora este mensaje.
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 0 16px">
                    <hr style="border:0;border-top:1px solid #e8ecf2;margin:0">
                  </td>
                </tr>
                <tr>
                  <td style="padding:0;font-size:13px;line-height:1.6;color:#8a99b0;text-align:center">
                    ¿Problemas con el código?
                    <a href="{base_url}/register" style="color:#1463ff;text-decoration:underline">Solicita uno nuevo</a>.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:24px 0 0">
              <p style="margin:0;font-size:12px;line-height:1.6;color:#8a99b0">
                © 2026 HotelData Hub. Todos los derechos reservados.<br>
                Este es un correo automático, por favor no respondas a este mensaje.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    send_email(email, "Tu código de verificación — HotelData", html)


# --- Refresh tokens ---

def _create_refresh_token(db: Any, user: dict) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.refresh_tokens.insert_one({
        "token_hash": token_hash,
        "user_id": user["_id"],
        "created_at": _now(),
        "expires_at": _now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "used": False,
    })
    return token


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


# --- User session management ---

@api_router.get("/sessions")
def list_own_sessions(request: Request):
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
    return {
        "items": [
            {
                "session_id": str(s["_id"]),
                "is_current": s["_id"] == current_id,
                "created_at": s.get("created_at").isoformat() if hasattr(s.get("created_at"), "isoformat") else str(s.get("created_at", "")),
                "expires_at": s.get("expires_at").isoformat() if hasattr(s.get("expires_at"), "isoformat") else str(s.get("expires_at", "")),
                "ip_address": s.get("ip_address"),
                "user_agent": s.get("user_agent"),
                "remember_me": bool(s.get("remember_me", False)),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@api_router.delete("/sessions/{session_id}")
def terminate_own_session(request: Request, session_id: str):
    db = get_database()
    user, current_session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not current_session:
        raise HTTPException(status_code=401, detail="No autenticado.")
    try:
        oid = ObjectId(session_id)
    except Exception:
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
    return {"ok": True, "message": "Sesión terminada."}


@api_router.post("/sessions/terminate-others")
def terminate_other_sessions(request: Request):
    """Terminate all sessions EXCEPT the current one."""
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
    return {
        "ok": True,
        "message": f"Se cerraron {count} sesión(es) en otros dispositivos.",
        "terminated_count": count
    }


@api_router.post("/heartbeat")
def heartbeat(
    request: Request,
    current_user: dict = Depends(require_login),
):
    """Update the session's last_activity_at timestamp.

    Called periodically by the frontend to keep the session alive
    while the user is actively using the application.
    """
    db = get_database()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return {"ok": True}
    session = get_session(db, token)
    if session:
        touch_session_activity(db, session)
        touch_session_activity(db, session)
    return {
        "ok": True,
        "inactivity_timeout_minutes": INACTIVITY_TIMEOUT_MINUTES,
    }


# --- Web routes ---

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


@web_router.get("/me")
def me(request: Request, current_user: dict = Depends(require_login)):
    redirect_url = get_default_redirect_for_role(current_user.get("primary_role"))
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# --- Password Recovery ---

RECOVERY_TOKEN_TTL_MINUTES = 60


@api_router.post("/recover")
def recover_password(request: Request, payload: dict = Body(...)):
    email = str(payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido.")

    db = get_database()
    user = find_user_by_identifier(db, email)

    # Always return success to avoid user enumeration
    if not user or not user.get("is_active", True):
        return {
            "ok": True,
            "message": "Si el correo existe, recibirás un enlace para restablecer tu contraseña.",
        }

    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = _now()

    db.password_recovery_tokens.insert_one({
        "token_hash": token_hash,
        "user_id": user["_id"],
        "email": email,
        "created_at": now,
        "expires_at": now + timedelta(minutes=RECOVERY_TOKEN_TTL_MINUTES),
        "used": False,
    })

    settings = get_settings()
    base_url = (settings.app_base_url or "https://hoteldata.app").rstrip("/")
    reset_link = f"{base_url}/reset?token={token}"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Recupera tu contraseña — HotelData</title>
</head>
<body style="margin:0;padding:0;background-color:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f6fb;padding:24px 0">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:560px">
          <tr>
            <td align="center" style="padding:0 0 20px">
              <img src="{base_url}/assets/logo-hoteldata.png" alt="HotelData Hub" width="200" style="display:block;max-width:200px;height:auto;border:0">
            </td>
          </tr>
          <tr>
            <td style="background:#ffffff;border-radius:12px;padding:40px 36px;box-shadow:0 2px 12px rgba(0,0,0,0.06)">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0 0 8px">
                    <span style="display:inline-block;background:#fef3e2;color:#b45a1c;font-size:12px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;padding:6px 16px;border-radius:20px">Recuperación de contraseña</span>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 0 20px">
                    <h1 style="margin:0;font-size:22px;font-weight:700;color:#162033">Restablece tu contraseña</h1>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 0 20px;font-size:15px;line-height:1.7;color:#5f6f87;text-align:center">
                    Hola <strong style="color:#162033">{user.get('display_name') or user.get('username')}</strong>,<br><br>
                    Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>HotelData Hub</strong>.
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 0 24px">
                    <a href="{reset_link}" style="display:inline-block;background:#1463ff;color:#ffffff;padding:14px 36px;border-radius:8px;text-decoration:none;font-size:16px;font-weight:700">Restablecer contraseña</a>
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 0 24px;font-size:13px;line-height:1.6;color:#8a99b0;text-align:center">
                    Este enlace expira en <strong>{RECOVERY_TOKEN_TTL_MINUTES} minuto(s)</strong>.<br>
                    Si no solicitaste este cambio, ignora este mensaje.
                  </td>
                </tr>
                <tr>
                  <td style="padding:0 0 16px">
                    <hr style="border:0;border-top:1px solid #e8ecf2;margin:0">
                  </td>
                </tr>
                <tr>
                  <td style="padding:0;font-size:13px;line-height:1.6;color:#8a99b0;text-align:center">
                    ¿No puedes hacer clic? Copia este enlace en tu navegador:<br>
                    <span style="color:#1463ff;word-break:break-all;font-size:12px">{reset_link}</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:24px 0 0">
              <p style="margin:0;font-size:12px;line-height:1.6;color:#8a99b0">
                © 2026 HotelData Hub. Todos los derechos reservados.<br>
                Este es un correo automático, por favor no respondas a este mensaje.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    send_email(email, "Recupera tu contraseña — HotelData", html)

    log_user_activity(
        db, action="auth.recovery_requested", request=request,
        user=user, details={"email": email},
    )

    return {
        "ok": True,
        "message": "Si el correo existe, recibirás un enlace para restablecer tu contraseña.",
    }


@api_router.post("/recover/reset")
def reset_password(request: Request, payload: dict = Body(...)):
    token = str(payload.get("token") or "").strip()
    new_password = str(payload.get("password") or "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token y contraseña son requeridos.")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")
    if not _re.search(r"[A-Z]", new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos una mayúscula.")
    if not _re.search(r"[a-z]", new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos una minúscula.")
    if not _re.search(r"\d", new_password):
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos un dígito.")

    db = get_database()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    doc = db.password_recovery_tokens.find_one({
        "token_hash": token_hash,
        "used": False,
        "expires_at": {"$gt": _now()},
    })
    if not doc:
        raise HTTPException(status_code=400, detail="El enlace es inválido o expiró. Solicita uno nuevo.")

    user = db.users.find_one({"_id": doc["user_id"]})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo.")

    new_hash = password_context.hash(new_password)
    password_history = user.get("password_history", [])
    stored_hash = user.get("password_hash", "")

    # Check not in history
    for old_hash in password_history:
        if password_context.verify(new_password, old_hash):
            raise HTTPException(
                status_code=400,
                detail="La nueva contraseña no puede ser igual a ninguna de las últimas 5 contraseñas usadas.",
            )

    if stored_hash:
        password_history.append(stored_hash)
    if len(password_history) > 5:
        password_history = password_history[-5:]

    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": new_hash,
                "password_history": password_history,
                "password_changed_at": _now(),
                "updated_at": _now(),
            }
        },
    )

    db.password_recovery_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used": True}})

    invalidate_user_sessions(db, user["_id"], reason="password_recovered")

    try:
        email = user.get("email", "")
        if email:
            html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;padding:24px;max-width:480px;margin:0 auto">
<h2 style="color:#1463ff">HotelData — Contraseña restablecida</h2>
<p>Tu contraseña fue restablecida exitosamente.</p>
<p>Si no realizaste este cambio, contacta al soporte de inmediato.</p>
<hr><p style="color:#5f6f87;font-size:0.85rem">HotelData Hub</p>
</body></html>"""
            send_email(email, "Tu contraseña fue restablecida — HotelData", html)
    except Exception:
        pass

    log_user_activity(
        db, action="auth.password_recovered", request=request,
        user=user,
    )

    return {"ok": True, "message": "Contraseña restablecida exitosamente. Tus sesiones han sido cerradas."}


@api_router.get("/me")
def me_api(request: Request):
    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user or not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"authenticated": False, "login_url": "/login"})
    home_href = get_default_redirect_for_role(user.get("primary_role"))
    return _auth_payload(user, session, home_href)
