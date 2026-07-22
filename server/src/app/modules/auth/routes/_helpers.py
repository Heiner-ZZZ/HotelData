"""Shared helpers for auth route modules."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.security.session import (
    ensure_utc,
    find_user_by_identifier,
    utc_now,
)


LOCK_ATTEMPTS = 5
LOCK_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 30
PENDING_TTL_MINUTES = 15
RECOVERY_TOKEN_TTL_MINUTES = 60

# Backward-compatible alias — prefer utc_now() directly
_now = utc_now


def _auth_payload(user: dict, session: dict | None, home_href: str, permission_codes: set[str] | None = None) -> dict:
    codes_list = sorted(list(permission_codes)) if permission_codes else []
    return {
        "authenticated": True,
        "user": {
            "user_id": str(user.get("_id") or user.get("user_id") or ""),
            "username": user.get("username") or "",
            "email": user.get("email") or "",
            "display_name": user.get("display_name") or user.get("full_name") or user.get("username") or "",
            "primary_role": user.get("primary_role") or "",
            "is_active": bool(user.get("is_active", True)),
            "avatar_url": user.get("avatar_url") or "",
        },
        "session": {
            "session_token": session.get("session_token_hash", "") if session else "",
            "expires_at": session.get("expires_at").isoformat() if session and hasattr(session.get("expires_at"), "isoformat") else (session.get("expires_at") if session else None),  # type: ignore[union-attr]
            "created_at": session.get("created_at").isoformat() if session and hasattr(session.get("created_at"), "isoformat") else (session.get("created_at") if session else None),  # type: ignore[union-attr]
        },
        "home_href": home_href,
        "login_url": "/login",
        "permission_codes": codes_list,
    }


def _check_account_locked(db: Any, user: dict) -> None:
    locked_until = user.get("locked_until")
    if locked_until:
        if isinstance(locked_until, str):
            locked_until = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        locked_until = ensure_utc(locked_until)
        if locked_until > utc_now():
            remaining = int((locked_until - utc_now()).total_seconds() // 60)
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
        update["locked_until"] = utc_now() + timedelta(minutes=LOCK_MINUTES)
    db.users.update_one({"_id": user["_id"]}, {"$set": update})


def _reset_failed_attempts(db: Any, user: dict) -> None:
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"failed_login_attempts": 0, "locked_until": None}},
    )


def _is_email_available(db: Any, email: str) -> bool:
    existing = db.users.find_one({"email": email})
    if not existing:
        return True
    if existing.get("deleted_at"):
        return True
    return False


def _is_username_available(db: Any, username: str) -> bool:
    existing = db.users.find_one({"username": username})
    if not existing:
        return True
    if existing.get("deleted_at"):
        return True
    return False


def _create_refresh_token(db: Any, user: dict) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.refresh_tokens.insert_one({
        "token_hash": token_hash,
        "user_id": user["_id"],
        "created_at": utc_now(),
        "expires_at": utc_now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "used": False,
    })
    return token


def _send_verification_code(email: str, display_name: str, code: str) -> None:
    settings = get_settings()
    base_url = (settings.app_base_url or "https://hoteldata.app").rstrip("/")

    from src.app.email.templates import base_layout

    # Build square digit boxes
    digits_html = ""
    for i, digit in enumerate(code):
        margin_left = "margin-left:6px;" if i > 0 else ""
        digits_html += (
            f'<td style="width:44px;height:52px;text-align:center;'
            f'font-size:26px;font-weight:700;font-family:monospace;'
            f'color:#191c1e;background:#f7f9fb;border:1px solid #d0d5d8;'
            f'{margin_left}">'
            f'{digit}'
            f'</td>'
        )

    body = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{display_name}</strong>,</p>\n'
        f'<p style="margin:0 0 16px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Usa el siguiente codigo para completar tu registro en HotelData:\n'
        f'</p>\n'
        f'<table align="center" cellpadding="0" cellspacing="0" style="margin:0 auto 20px">\n'
        f'  <tr>{digits_html}</tr>\n'
        f'</table>\n'
        f'<p style="margin:0;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Este codigo expira en <strong>{PENDING_TTL_MINUTES} minutos</strong>.<br>'
        f'Si no solicitaste este registro, ignora este mensaje.'
        f'</p>'
    )

    html = base_layout(
        "Verifica tu correo electronico",
        body,
        logo_url=base_url,
        footer_note=(
            "Este es un mensaje automatico de HotelData.<br>"
            "No compartas este codigo con nadie."
        ),
    )
    send_email(email, "Tu codigo de verificacion — HotelData", html)


def _send_recovery_email(user: dict, token: str) -> None:
    settings = get_settings()
    base_url = (settings.app_base_url or "https://hoteldata.app").rstrip("/")
    reset_link = f"{base_url}/reset?token={token}"

    from src.app.email.templates import base_layout, cta_button

    display_name = user.get("display_name") or user.get("username") or "Usuario"
    body = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{display_name}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Recibimos una solicitud para restablecer la contrasena de tu cuenta '
        f'en HotelData.\n'
        f'</p>\n'
        f'{cta_button(reset_link, "Restablecer contrasena")}\n'
        f'<p style="margin:20px 0 0;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Este enlace expira en <strong>{RECOVERY_TOKEN_TTL_MINUTES} minuto(s)</strong>.<br>'
        f'Si no solicitaste este cambio, ignora este mensaje.'
        f'</p>'
    )

    html = base_layout(
        "Restablece tu contrasena",
        body,
        logo_url=base_url,
        footer_note=(
            "Este es un mensaje automatico de HotelData.<br>"
            "Si no solicitaste restablecer tu contrasena, ignora este correo."
        ),
    )
    send_email(user.get("email", ""), "Recupera tu contrasena — HotelData", html)


def _send_property_verification_code(email: str, display_name: str, code: str) -> None:
    """Send the property-owner onboarding 6-digit verification code.

    Parallel to `_send_verification_code`, but uses the property-onboarding
    template (different headline, host-specific copy, lists what the
    panel will unlock). Subject is 'Tu código de activación — HotelData'.

    Called from `register_property.send_property_registration_code` after
    the `pending_property` subdocument is persisted to `pending_registrations`.
    """
    settings = get_settings()
    base_url = (settings.app_base_url or "https://hoteldata.app").rstrip("/")

    from src.app.email.templates import onboarding_property_verification

    html = onboarding_property_verification(
        email=email,
        display_name=display_name,
        code=code,
        base_url=base_url,
        expiry_minutes=PENDING_TTL_MINUTES,
    )
    send_email(email, "Tu código de activación — HotelData", html)
