from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import gridfs
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from src.app.email.service import send_email
from src.app.security.dependencies import require_login
from src.app.security.session import log_user_activity
from src.database.connection import get_database
from config.settings import get_settings


api_router = APIRouter(prefix="/api/account", tags=["account-api"])


import re as _re

_PHONE_REGEX = _re.compile(r"^[\d\s\+\-\(\)]{7,20}$")

_PROFILE_FIELDS = {
    "display_name": "",
    "email": "",
    "phone": "",
    "notification_email": "",
    "address_street": "",
    "address_city": "",
    "address_state": "",
    "address_country": "",
    "address_postal_code": "",
    "date_of_birth": "",
    "nationality": "",
    "id_document_type": "",
    "id_document_number": "",
    "preferred_language": "es",
    "marketing_opt_in": False,
    "notification_email_enabled": True,
    "notification_sms_enabled": False,
    # Avatar
    "avatar_url": "",
    # Social media
    "social_instagram": "",
    "social_facebook": "",
    "social_twitter": "",
    "social_linkedin": "",
    # Travel preferences
    "travel_purpose": "",
    "travel_budget": "",
    "travel_companions": "",
    "travel_accommodation": "",
    "travel_destination_type": "",
    "travel_interests": "",
    "travel_frequent_flyer": "",
    "travel_loyalty_programs": "",
    "travel_notes": "",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_profile(user: dict[str, Any]) -> dict[str, Any]:
    """Build a profile dict from a MongoDB user document, filling defaults."""
    return {
        "user_id": str(user.get("_id")),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "display_name": user.get("display_name") or user.get("username") or "",
        "primary_role": user.get("primary_role", ""),
        "is_active": bool(user.get("is_active", True)),
        "created_at": user.get("created_at").isoformat() if hasattr(user.get("created_at"), "isoformat") else str(user.get("created_at", "")),
        **{k: user.get(k, v) for k, v in _PROFILE_FIELDS.items()},
    }


@api_router.get("/profile")
def get_profile(request: Request):
    """Return the current user's full profile, ensuring default fields exist."""
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    # Ensure profile fields exist on the user document
    updates = {k: v for k, v in _PROFILE_FIELDS.items() if k not in current_user}
    if updates:
        db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    **updates,
                    "updated_at": utc_now(),
                    "updated_by": f"system.init_profile_{current_user.get('username')}",
                }
            },
        )
        current_user.update(updates)

    log_user_activity(db, action="account.profile_read", request=request, user=current_user)
    return _serialize_profile(current_user)


@api_router.put("/profile")
def update_profile(request: Request, payload: dict[str, Any] = Body(...)):
    """Update the current user's profile fields. Returns full updated profile."""
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    # Whitelist only allowed profile fields
    allowed_keys = set(_PROFILE_FIELDS.keys())
    safe_updates = {}
    for key, value in payload.items():
        if key in allowed_keys:
            # Type-coerce booleans
            if isinstance(_PROFILE_FIELDS[key], bool) and not isinstance(value, bool):
                safe_updates[key] = str(value).lower() in ("true", "1", "yes")
            else:
                safe_updates[key] = value

    if not safe_updates:
        return JSONResponse(
            {"ok": False, "message": "No se enviaron campos válidos para actualizar."},
            status_code=400,
        )

    phone_val = safe_updates.get("phone")
    if phone_val is not None and phone_val != "" and not _PHONE_REGEX.match(str(phone_val)):
        return JSONResponse(
            {"ok": False, "message": "Formato de teléfono inválido. Usa solo dígitos, espacios, +, -, ( )."},
            status_code=400,
        )

    email_val = safe_updates.get("notification_email", "")
    if email_val and "@" not in str(email_val):
        return JSONResponse(
            {"ok": False, "message": "Email de notificación inválido."},
            status_code=400,
        )

    safe_updates["updated_at"] = utc_now()
    safe_updates["updated_by"] = current_user.get("username", "unknown")

    old_email = current_user.get("email", "")
    new_email = safe_updates.get("email", old_email)

    try:
        db.users.update_one({"_id": user_id}, {"$set": safe_updates})
    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail="El email ya está registrado por otro usuario.",
        )
    if new_email != old_email:
        try:
            _send_email_change_verification(current_user, old_email, new_email)
        except Exception:
            pass
        if old_email:
            try:
                from src.app.email.templates import base_layout
                body = (
                    f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
                    f'El correo de tu cuenta fue cambiado de <strong>{old_email}</strong> a <strong>{new_email}</strong>.</p>\n'
                    f'<p style="margin:0;font-size:13px;color:#6f797d;line-height:1.5">'
                    f'Si no realizaste este cambio, contacta al soporte de inmediato.'
                    f'</p>'
                )
                html = base_layout(
                    "Correo electronico actualizado",
                    body,
                    logo_url=get_settings().app_base_url,
                )
                send_email(old_email, "Tu correo fue cambiado — HotelData", html)
            except Exception:
                pass

    log_user_activity(
        db,
        action="account.profile_updated",
        request=request,
        user=current_user,
        details={"updated_fields": list(safe_updates.keys())},
    )

    # Re-fetch the updated document
    updated_user = db.users.find_one({"_id": user_id}, {"password_hash": 0})
    return _serialize_profile(updated_user or current_user)


@api_router.post("/profile/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
    if file.content_type not in allowed_types:
        return JSONResponse(
            {"ok": False, "message": f"Tipo de archivo no permitido: {file.content_type}. Usa JPG, PNG, WebP, GIF o AVIF."},
            status_code=400,
        )

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        return JSONResponse(
            {"ok": False, "message": "La imagen no puede superar los 2 MB."},
            status_code=400,
        )

    # Remove old avatar from GridFS if exists
    old_avatar_url = current_user.get("avatar_url", "")
    if old_avatar_url.startswith("/api/account/avatar/"):
        try:
            old_id = ObjectId(old_avatar_url.split("/")[-1])
            fs = gridfs.GridFS(db)
            if fs.exists(old_id):
                fs.delete(old_id)
        except Exception:
            pass

    # Store in GridFS
    unique_name = f"{current_user.get('username', str(user_id))}_{uuid.uuid4().hex[:8]}"
    fs = gridfs.GridFS(db)
    file_id = fs.put(content, filename=unique_name, content_type=file.content_type)
    avatar_url = f"/api/account/avatar/{file_id}"

    db.users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "avatar_url": avatar_url,
                "updated_at": utc_now(),
                "updated_by": current_user.get("username", "unknown"),
            }
        },
    )

    log_user_activity(
        db,
        action="account.avatar_uploaded",
        request=request,
        user=current_user,
        details={"avatar_url": avatar_url},
    )

    return {"ok": True, "avatar_url": avatar_url, "message": "Foto de perfil actualizada."}


@api_router.get("/avatar/{file_id}")
def get_avatar(file_id: str):
    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de archivo inválido.")

    fs = gridfs.GridFS(get_database())
    if not fs.exists(oid):
        raise HTTPException(status_code=404, detail="Avatar no encontrado.")

    grid_file = fs.get(oid)
    return Response(
        content=grid_file.read(),
        media_type=grid_file.content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@api_router.get("/verify-email")
def verify_email(request: Request, token: str = ""):
    if not token:
        raise HTTPException(status_code=400, detail="Token requerido.")
    if verify_email_change(token):
        return JSONResponse({"ok": True, "message": "Correo verificado exitosamente."})
    raise HTTPException(status_code=400, detail="Token inválido o expirado.")


def _send_email_change_verification(user: dict, old_email: str, new_email: str) -> None:
    token = secrets.token_urlsafe(32)
    db = get_database()
    settings = get_settings()
    db.email_verification_tokens.insert_one({
        "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "user_id": user["_id"],
        "old_email": old_email,
        "new_email": new_email,
        "created_at": utc_now(),
        "expires_at": utc_now().replace(hour=23, minute=59, second=59) + timedelta(days=7),
        "used": False,
    })
    link = f"{settings.app_base_url}/verify-email?token={token}"

    from src.app.email.templates import base_layout, cta_button
    body = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Has solicitado cambiar tu correo de <strong>{old_email}</strong> a <strong>{new_email}</strong>.</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Haz clic en el siguiente enlace para confirmar el cambio:'
        f'</p>\n'
        f'{cta_button(link, "Verificar correo")}\n'
        f'<p style="margin:20px 0 0;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Si no solicitaste este cambio, ignora este mensaje.'
        f'</p>'
    )
    html = base_layout(
        "Verifica tu nuevo correo",
        body,
        logo_url=settings.app_base_url,
        footer_note=(
            "Este es un mensaje automatico de HotelData Hub.<br>"
            "El enlace expirara en 7 dias."
        ),
    )
    try:
        send_email(new_email, "Verifica tu nuevo correo — HotelData", html)
    except Exception:
        pass


def verify_email_change(token: str) -> bool:
    db = get_database()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    doc = db.email_verification_tokens.find_one({
        "token_hash": token_hash,
        "used": False,
        "expires_at": {"$gt": utc_now()},
    })
    if not doc:
        return False
    db.email_verification_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used": True}})
    purpose = doc.get("purpose", "")
    if purpose == "registration":
        db.users.update_one(
            {"_id": doc["user_id"]},
            {"$set": {"email_verified": True, "updated_at": utc_now()}},
        )
    return True
