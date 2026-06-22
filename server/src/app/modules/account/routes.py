from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from pymongo.errors import DuplicateKeyError

from src.app.security.dependencies import require_login
from src.app.security.session import log_user_activity
from src.database.connection import get_database


api_router = APIRouter(prefix="/api/account", tags=["account-api"])


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

    safe_updates["updated_at"] = utc_now()
    safe_updates["updated_by"] = current_user.get("username", "unknown")

    try:
        db.users.update_one({"_id": user_id}, {"$set": safe_updates})
    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail="El email ya está registrado por otro usuario.",
        )

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
    """Upload a profile avatar image. Saves to static/avatars/ and updates avatar_url."""
    db = get_database()
    current_user = require_login(request)
    user_id = current_user["_id"]

    # Validate content type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
    if file.content_type not in allowed_types:
        return JSONResponse(
            {"ok": False, "message": f"Tipo de archivo no permitido: {file.content_type}. Usa JPG, PNG, WebP, GIF o AVIF."},
            status_code=400,
        )

    # Read file content
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return JSONResponse(
            {"ok": False, "message": "La imagen no puede superar los 5 MB."},
            status_code=400,
        )

    # Determine extension
    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/avif": ".avif",
    }
    ext = ext_map.get(file.content_type, ".jpg")

    # Build path: static/avatars/{user_id}_{uuid}{ext}
    avatars_dir = Path(__file__).resolve().parents[2] / "static" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{current_user.get('username', str(user_id))}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = avatars_dir / unique_name

    with open(dest_path, "wb") as f:
        f.write(content)

    # Build URL path
    avatar_url = f"/static/avatars/{unique_name}"

    # Update user document
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
