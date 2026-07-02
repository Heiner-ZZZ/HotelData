"""Password recovery and reset endpoints."""

from __future__ import annotations

import hashlib
import re as _re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Body, HTTPException, Request

from src.app.security.session import log_user_activity, invalidate_user_sessions, password_context, find_user_by_identifier
from src.database.connection import get_database

from ._helpers import (
    RECOVERY_TOKEN_TTL_MINUTES,
    _now,
    _send_recovery_email,
)

api_router = APIRouter(prefix="/api/auth", tags=["auth-password"])


@api_router.post("/recover")
def recover_password(request: Request, payload: dict = Body(...)):
    email = str(payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido.")

    db = get_database()
    user = find_user_by_identifier(db, email)

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

    _send_recovery_email(user, token)

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
            from config.settings import get_settings
            from src.app.email.service import send_email
            from src.app.email.templates import base_layout
            body = (
                f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
                f'Tu contrasena fue restablecida exitosamente.</p>\n'
                f'<p style="margin:0;font-size:13px;color:#6f797d;line-height:1.5">'
                f'Si no realizaste este cambio, contacta al soporte de inmediato.'
                f'</p>'
            )
            html = base_layout(
                "Contrasena restablecida",
                body,
                logo_url=get_settings().app_base_url,
            )
            send_email(email, "Tu contrasena fue restablecida — HotelData", html)
    except Exception:
        pass

    log_user_activity(
        db, action="auth.password_recovered", request=request,
        user=user,
    )

    return {"ok": True, "message": "Contraseña restablecida exitosamente. Tus sesiones han sido cerradas."}
