"""Registration and email verification endpoints."""

from __future__ import annotations

import hashlib
import random
from datetime import timedelta

from fastapi import APIRouter, Body, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from src.app.modules.legal.service import validate_terms_acceptance
from src.app.security.session import ensure_utc, password_context, log_user_activity
from src.database.connection import get_database

from ._helpers import (
    PENDING_TTL_MINUTES,
    _is_email_available,
    _is_username_available,
    _now,
    _send_verification_code,
)

from src.app.security.role_helpers import resolve_role_id

api_router = APIRouter(prefix="/api/auth", tags=["auth-register"])


@api_router.post("/send-code")
def send_code(
    request: Request,
    payload: dict = Body(...),
):
    email = str(payload.get("email") or "").strip().lower()
    display_name = str(payload.get("display_name") or "").strip() or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="email es requerido.")

    db = get_database()
    if not _is_email_available(db, email):
        raise HTTPException(status_code=400, detail="Este correo ya está registrado como usuario activo.")

    # Aceptación de Términos: si el frontend la envía, debe coincidir con la
    # versión vigente; queda estampada en el pendiente para confirm-code.
    accepted_terms_version = payload.get("accepted_terms_version")
    validate_terms_acceptance(db, "terms_guest", accepted_terms_version)

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
    if accepted_terms_version is not None:
        pending["terms_guest_version"] = int(accepted_terms_version)
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

    # Aceptación de Términos: si el payload la trae, debe coincidir con la
    # versión vigente. Sin el campo (back-compat con tests/seeds) no se estampa.
    accepted_terms_version = payload.get("accepted_terms_version")
    validate_terms_acceptance(db, "terms_guest", accepted_terms_version)

    if not send_verification:
        now = _now()
        user_doc = {
            "username": username,
            "email": email,
            "password_hash": password_context.hash(password),
            "display_name": display_name,
            "primary_role_id": resolve_role_id("cliente"),
            "is_active": True,
            "email_verified": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "created_at": now,
            "updated_at": now,
        }
        if accepted_terms_version is not None:
            user_doc["terms_guest_version"] = int(accepted_terms_version)
            user_doc["terms_accepted_at"] = now
        try:
            result = db.users.insert_one(user_doc)
        except DuplicateKeyError:
            raise HTTPException(status_code=400, detail="El username o email ya está registrado.")
        user_doc["_id"] = result.inserted_id
        log_user_activity(db, action="auth.register", request=request, user=user_doc)
        return {"ok": True, "message": "Registro exitoso. Ya puedes iniciar sesión."}

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
    if accepted_terms_version is not None:
        pending["terms_guest_version"] = int(accepted_terms_version)
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

    expires_at = ensure_utc(pending.get("expires_at"))
    if expires_at and expires_at < _now():
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
        "primary_role_id": resolve_role_id("cliente"),
        "is_active": True,
        "email_verified": True,
        "failed_login_attempts": 0,
        "locked_until": None,
        "created_at": now,
        "updated_at": now,
    }
    # La aceptación de términos quedó validada y estampada en el pendiente
    # (send-code); se copia al usuario al confirmar.
    if pending.get("terms_guest_version") is not None:
        user_doc["terms_guest_version"] = int(pending["terms_guest_version"])
        user_doc["terms_accepted_at"] = now
    try:
        result = db.users.insert_one(user_doc)
    except DuplicateKeyError:
        db.pending_registrations.delete_one({"email": email})
        raise HTTPException(status_code=400, detail="El username o email ya está registrado.")

    user_doc["_id"] = result.inserted_id
    db.pending_registrations.delete_one({"email": email})
    log_user_activity(db, action="auth.register_confirmed", request=request, user=user_doc)
    return {"ok": True, "message": "Cuenta verificada exitosamente. Ya puedes iniciar sesión."}
