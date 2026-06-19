from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse

from src.app.security.dependencies import require_login
from src.app.security.session import log_user_activity, verify_password
from src.app.security.session import password_context
from src.database.connection import get_database

from .schemas import PasswordChange, SettingsUpdate


api_router = APIRouter(prefix="/api/settings", tags=["settings-api"])

_DEFAULT_SETTINGS = {
    "session_timeout_minutes": 60,
    "default_dashboard": "/management",
    "theme": "system",
}


def _serialize_settings(user: dict[str, Any]) -> dict[str, Any]:
    raw = user.get("settings", {})
    merged = {**_DEFAULT_SETTINGS, **raw}
    return {
        "session_timeout_minutes": merged["session_timeout_minutes"],
        "default_dashboard": merged["default_dashboard"],
        "theme": merged["theme"],
    }


@api_router.get("")
def get_settings(request: Request):
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    if "settings" not in current_user:
        db.users.update_one(
            {"_id": user_id},
            {"$set": {"settings": dict(_DEFAULT_SETTINGS), "updated_at": utc_now()}},
        )
        current_user["settings"] = dict(_DEFAULT_SETTINGS)

    log_user_activity(db, action="settings.read", request=request, user=current_user)
    return _serialize_settings(current_user)


@api_router.put("")
def update_settings(request: Request, payload: SettingsUpdate = Body(...)):
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    allowed_keys = set(_DEFAULT_SETTINGS.keys())
    safe_updates = {}
    for key, value in payload.model_dump(exclude_none=True).items():
        if key in allowed_keys and value is not None:
            safe_updates[key] = value

    if not safe_updates:
        return JSONResponse(
            {"ok": False, "message": "No se enviaron campos válidos para actualizar."},
            status_code=400,
        )

    set_doc = {f"settings.{k}": v for k, v in safe_updates.items()}
    set_doc["updated_at"] = utc_now()
    set_doc["updated_by"] = current_user.get("username", "unknown")

    db.users.update_one({"_id": user_id}, {"$set": set_doc})

    log_user_activity(
        db,
        action="settings.updated",
        request=request,
        user=current_user,
        details={"updated_fields": list(safe_updates.keys())},
    )

    updated_user = db.users.find_one({"_id": user_id}, {"password_hash": 0})
    return _serialize_settings(updated_user or current_user)


@api_router.put("/password")
def change_password(request: Request, payload: PasswordChange = Body(...)):
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    stored_hash = current_user.get("password_hash", "")
    if not verify_password(payload.current_password, stored_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")

    new_hash = password_context.hash(payload.new_password)
    db.users.update_one(
        {"_id": user_id},
        {"$set": {"password_hash": new_hash, "updated_at": utc_now()}},
    )

    log_user_activity(
        db,
        action="settings.password_changed",
        request=request,
        user=current_user,
    )

    return {"ok": True, "message": "Contraseña actualizada correctamente."}


def utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
