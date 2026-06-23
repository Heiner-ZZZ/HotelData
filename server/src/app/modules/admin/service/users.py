from __future__ import annotations

from typing import Any

from bson import ObjectId

from src.database.connection import get_database

from ._helpers import utc_now


def toggle_user_active(target_user_id: str, acting_user: dict[str, Any]) -> dict[str, Any]:
    db = get_database()
    if not target_user_id:
        return {"ok": False, "message": "Usuario no válido."}

    try:
        object_id = ObjectId(target_user_id)
    except Exception:
        return {"ok": False, "message": "Identificador de usuario inválido."}

    target_user = db.users.find_one({"_id": object_id})
    if not target_user:
        return {"ok": False, "message": "Usuario no encontrado."}

    if acting_user.get("_id") == target_user.get("_id"):
        return {"ok": False, "message": "No puede desactivar su propia cuenta desde esta vista."}

    if target_user.get("primary_role") == "super_admin":
        return {"ok": False, "message": "No se permite desactivar la cuenta super_admin."}

    new_state = not bool(target_user.get("is_active", True))
    db.users.update_one(
        {"_id": object_id},
        {
            "$set": {
                "is_active": new_state,
                "updated_at": utc_now(),
                "updated_by": acting_user.get("username"),
            }
        },
    )
    if not new_state:
        db.user_sessions.update_many(
            {"user_id": object_id, "is_active": True},
            {"$set": {"is_active": False, "end_reason": "user_deactivated"}},
        )

    db.user_activity_logs.insert_one(
        {
            "user_id": acting_user.get("_id"),
            "username": acting_user.get("username"),
            "email": acting_user.get("email"),
            "action": "admin.user_toggled_active",
            "module": "admin",
            "details": {
                "target_user_id": str(target_user["_id"]),
                "target_username": target_user.get("username"),
                "is_active": new_state,
            },
            "created_at": utc_now(),
        }
    )

    state_label = "activado" if new_state else "desactivado"
    return {
        "ok": True,
        "message": f"Usuario {target_user.get('username')} {state_label} correctamente.",
    }


def delete_user(target_user_id: str, acting_user: dict[str, Any]) -> dict[str, Any]:
    db = get_database()
    if not target_user_id:
        return {"ok": False, "message": "Usuario no válido."}

    try:
        object_id = ObjectId(target_user_id)
    except Exception:
        return {"ok": False, "message": "Identificador de usuario inválido."}

    target_user = db.users.find_one({"_id": object_id})
    if not target_user:
        return {"ok": False, "message": "Usuario no encontrado."}

    if acting_user.get("_id") == target_user.get("_id"):
        return {"ok": False, "message": "No puede eliminar su propia cuenta."}

    if target_user.get("primary_role") == "super_admin":
        return {"ok": False, "message": "No se permite eliminar la cuenta super_admin."}

    now = utc_now()
    db.users.update_one(
        {"_id": object_id},
        {
            "$set": {
                "is_active": False,
                "deleted_at": now,
                "deleted_by": acting_user.get("username"),
                "deleted_username": target_user.get("username"),
                "deleted_email": target_user.get("email"),
                "updated_at": now,
                "updated_by": acting_user.get("username"),
            }
        },
    )
    # Cerrar sesiones activas
    db.user_sessions.update_many(
        {"user_id": object_id, "is_active": True},
        {"$set": {"is_active": False, "end_reason": "user_deleted"}},
    )

    db.user_activity_logs.insert_one(
        {
            "user_id": acting_user.get("_id"),
            "username": acting_user.get("username"),
            "email": acting_user.get("email"),
            "action": "admin.user_deleted",
            "module": "admin",
            "details": {
                "target_user_id": str(target_user["_id"]),
                "target_username": target_user.get("username"),
                "target_email": target_user.get("email"),
            },
            "created_at": now,
        }
    )

    return {
        "ok": True,
        "message": f"Usuario {target_user.get('username')} eliminado correctamente. El correo y username pueden reutilizarse.",
    }
