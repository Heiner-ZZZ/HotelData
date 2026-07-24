from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.security.role_helpers import get_role_name
from src.database.connection import get_database


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_active_sessions(page: int = 1, page_size: int = 50) -> dict:
    db = get_database()
    query = {"is_active": True}
    total = db.user_sessions.count_documents(query)
    cursor = (
        db.user_sessions.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for s in cursor:
        user = db.users.find_one({"_id": s.get("user_id")}, {"username": 1, "email": 1, "display_name": 1, "primary_role_id": 1})
        items.append({
            "session_id": str(s["_id"]),
            "user_id": str(s.get("user_id", "")),
            "username": s.get("username", ""),
            "email": s.get("email", ""),
            "display_name": (user or {}).get("display_name", ""),
            "primary_role": get_role_name(user or {}),
            "created_at": _fmt(s.get("created_at")),
            "expires_at": _fmt(s.get("expires_at")),
            "ip_address": s.get("ip_address"),
            "user_agent": s.get("user_agent"),
            "remember_me": bool(s.get("remember_me", False)),
        })
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def terminate_session(session_id: str, acting_user: dict[str, Any]) -> dict:
    db = get_database()
    try:
        oid = ObjectId(session_id)
    except InvalidId:
        return {"ok": False, "message": "ID de sesión inválido."}

    session = db.user_sessions.find_one({"_id": oid, "is_active": True})
    if not session:
        return {"ok": False, "message": "Sesión no encontrada o ya inactiva."}

    acting_uid = acting_user.get("_id")
    if isinstance(acting_uid, str):
        acting_uid = ObjectId(acting_uid)
    if session.get("user_id") == acting_uid:
        return {"ok": False, "message": "No puedes terminar tu propia sesión desde aquí. Usa cerrar sesión."}

    db.user_sessions.update_one(
        {"_id": oid},
        {"$set": {"is_active": False, "ended_at": _now(), "end_reason": "terminated_by_admin"}},
    )
    db.user_activity_logs.insert_one({
        "user_id": acting_user.get("_id"),
        "username": acting_user.get("username"),
        "action": "admin.session_terminated",
        "module": "admin",
        "details": {"target_session_id": session_id, "target_user_id": str(session.get("user_id", ""))},
        "created_at": _now(),
    })
    return {"ok": True, "message": "Sesión terminada."}


def terminate_user_sessions(user_id_str: str, acting_user: dict[str, Any]) -> dict:
    db = get_database()
    try:
        uid = ObjectId(user_id_str)
    except InvalidId:
        return {"ok": False, "message": "ID de usuario inválido."}

    acting_uid = acting_user.get("_id")
    if isinstance(acting_uid, str):
        acting_uid = ObjectId(acting_uid)
    if uid == acting_uid:
        return {"ok": False, "message": "No puedes terminar tus propias sesiones desde aquí."}

    result = db.user_sessions.update_many(
        {"user_id": uid, "is_active": True},
        {"$set": {"is_active": False, "ended_at": _now(), "end_reason": "terminated_by_admin"}},
    )
    db.user_activity_logs.insert_one({
        "user_id": acting_user.get("_id"),
        "username": acting_user.get("username"),
        "action": "admin.user_sessions_terminated",
        "module": "admin",
        "details": {"target_user_id": user_id_str, "count": result.modified_count},
        "created_at": _now(),
    })
    return {"ok": True, "message": f"{result.modified_count} sesión(es) terminada(s)."}


def notify_new_login(user: dict[str, Any], ip_address: str | None, user_agent: str | None) -> None:
    db = get_database()
    settings = get_settings()
    email = user.get("email", "")
    if not email:
        return

    recent_sessions = list(
        db.user_sessions.find(
            {"user_id": user["_id"], "is_active": True},
            {"ip_address": 1, "created_at": 1},
        ).sort("created_at", -1).limit(5)
    )

    known_ips: set[str] = set()
    for s in recent_sessions:
        if s.get("ip_address"):
            known_ips.add(s["ip_address"])

    if ip_address and ip_address not in known_ips and known_ips:
        from src.app.email.templates import base_layout, detail_row, detail_table
        rows = detail_table(
            "Detalles del inicio de sesion",
            detail_row("IP", ip_address or "Desconocida")
            + detail_row("Dispositivo", user_agent or "Desconocido")
            + detail_row("Fecha", _now().strftime("%Y-%m-%d %H:%M UTC")),
        )
        body = (
            f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
            f'Se detecto un inicio de sesion en tu cuenta desde una ubicacion o dispositivo no reconocido.</p>\n'
            f'{rows}\n'
            f'<p style="margin:16px 0 0;font-size:13px;color:#6f797d;line-height:1.5">'
            f'Si fuiste tu, ignora este mensaje. Si no reconoces esta actividad, cambia tu contrasena inmediatamente.'
            f'</p>'
        )
        html = base_layout(
            "Nuevo inicio de sesion detectado",
            body,
            logo_url=settings.app_base_url,
            footer_note="Mantén tu contrasena segura y no la compartas con nadie.",
        )
        send_email(email, "Nuevo inicio de sesion — HotelData", html)


def _fmt(val: Any) -> str:
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val) if val else ""
