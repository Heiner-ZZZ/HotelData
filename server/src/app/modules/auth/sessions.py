from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from src.app.email.service import send_email
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
        user = db.users.find_one({"_id": s.get("user_id")}, {"username": 1, "email": 1, "display_name": 1, "primary_role": 1})
        items.append({
            "session_id": str(s["_id"]),
            "user_id": str(s.get("user_id", "")),
            "username": s.get("username", ""),
            "email": s.get("email", ""),
            "display_name": (user or {}).get("display_name", ""),
            "primary_role": (user or {}).get("primary_role", ""),
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
    except Exception:
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
    except Exception:
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
        html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;padding:24px;max-width:480px;margin:0 auto">
<h2 style="color:#1463ff">HotelData — Nuevo inicio de sesión</h2>
<p>Se detectó un inicio de sesión en tu cuenta desde una ubicación o dispositivo no reconocido.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr><td style="padding:8px;background:#f3f6fb;font-weight:600">IP</td><td style="padding:8px">{ip_address or "Desconocida"}</td></tr>
<tr><td style="padding:8px;background:#f3f6fb;font-weight:600">Dispositivo</td><td style="padding:8px">{user_agent or "Desconocido"}</td></tr>
<tr><td style="padding:8px;background:#f3f6fb;font-weight:600">Fecha</td><td style="padding:8px">{_now().strftime("%Y-%m-%d %H:%M UTC")}</td></tr>
</table>
<p>Si fuiste tú, ignora este mensaje. Si no reconoces esta actividad, cambia tu contraseña inmediatamente.</p>
<hr><p style="color:#5f6f87;font-size:0.85rem">HotelData Hub</p>
</body></html>"""
        send_email(email, "Nuevo inicio de sesión — HotelData", html)


def _fmt(val: Any) -> str:
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val) if val else ""
