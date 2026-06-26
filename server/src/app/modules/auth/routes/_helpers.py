"""Shared helpers for auth route modules."""

from __future__ import annotations

import hashlib
import random
import re as _re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.security.navigation import get_default_redirect_for_role
from src.app.security.route_permissions import is_safe_internal_next
from src.app.security.session import (
    SESSION_COOKIE_NAME,
    create_user_session,
    find_user_by_identifier,
    get_current_user,
    get_session,
    invalidate_session,
    invalidate_user_sessions,
    log_user_activity,
    verify_password,
    password_context,
)
from src.database.connection import get_database


LOCK_ATTEMPTS = 5
LOCK_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 30
PENDING_TTL_MINUTES = 15
RECOVERY_TOKEN_TTL_MINUTES = 60


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
        "created_at": _now(),
        "expires_at": _now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "used": False,
    })
    return token


def _send_verification_code(email: str, display_name: str, code: str) -> None:
    settings = get_settings()
    base_url = (settings.app_base_url or "https://hoteldata.app").rstrip("/")

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


def _send_recovery_email(user: dict, token: str) -> None:
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
    send_email(user.get("email", ""), "Recupera tu contraseña — HotelData", html)
