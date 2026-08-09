from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from passlib.context import CryptContext

from src.database.connection import get_database

from ._helpers import utc_now
from .ownership import HOTEL_ROLES
from src.app.security.role_helpers import is_super_admin

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def update_user(
    target_user_id: str,
    payload: dict[str, Any],
    acting_user: dict[str, Any],
) -> dict[str, Any]:
    """Update a user's data from the system-admin view.

    Whitelisted fields: ``display_name``, ``email``, ``primary_role``
    (keeps ``primary_role_id``/``role_ids`` in sync), ``is_active`` and
    ``password`` (optional reset). Guards mirror ``toggle_user_active`` /
    ``delete_user``: the super_admin account is protected and the acting
    user cannot deactivate itself.
    """
    db = get_database()
    if not target_user_id:
        return {"ok": False, "message": "Usuario no válido."}

    try:
        object_id = ObjectId(target_user_id)
    except InvalidId:
        return {"ok": False, "message": "Identificador de usuario inválido."}

    target_user = db.users.find_one({"_id": object_id})
    if not target_user:
        return {"ok": False, "message": "Usuario no encontrado."}

    if is_super_admin(target_user):
        return {"ok": False, "message": "No se permite editar la cuenta super_admin."}

    updates: dict[str, Any] = {}

    username = payload.get("username")
    if username is not None:
        username = str(username).strip()
        if not username:
            return {"ok": False, "message": "El nombre de usuario no puede quedar vacío."}
        if any(ch.isspace() for ch in username):
            return {"ok": False, "message": "El nombre de usuario no puede contener espacios."}
        duplicate = db.users.find_one({"username": username, "_id": {"$ne": object_id}})
        if duplicate:
            return {"ok": False, "message": "El nombre de usuario ya está en uso por otra cuenta."}
        updates["username"] = username

    display_name = payload.get("display_name")
    if display_name is not None:
        display_name = str(display_name).strip()
        if not display_name:
            return {"ok": False, "message": "El nombre mostrado no puede quedar vacío."}
        updates["display_name"] = display_name

    email = payload.get("email")
    if email is not None:
        email = str(email).strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            return {"ok": False, "message": "Formato de email inválido."}
        duplicate = db.users.find_one({"email": email, "_id": {"$ne": object_id}})
        if duplicate:
            return {"ok": False, "message": "El email ya está registrado por otro usuario."}
        updates["email"] = email

    primary_role = payload.get("primary_role")
    if primary_role is not None:
        primary_role = str(primary_role).strip()
        role = db.roles.find_one({"role_name": primary_role})
        if not role:
            return {"ok": False, "message": f"Rol no válido: {primary_role}."}
        updates["primary_role"] = primary_role
        updates["primary_role_id"] = role["_id"]
        # El modelo de cuenta usa un rol principal único; role_ids queda
        # sincronizado con el FK (misma convención de seed/ownership).
        updates["role_ids"] = [role["_id"]]

    assigned_hotels = payload.get("assigned_hotels")
    if assigned_hotels is not None:
        effective_role = updates.get("primary_role") or target_user.get("primary_role") or ""
        if effective_role not in HOTEL_ROLES:
            return {
                "ok": False,
                "message": "Los hoteles asignados solo aplican a usuarios con rol de hotel.",
            }
        try:
            hotels = [int(h) for h in assigned_hotels]
        except (TypeError, ValueError):
            return {"ok": False, "message": "Los hoteles asignados deben ser identificadores numéricos."}
        if not hotels:
            return {
                "ok": False,
                "message": "No puede dejar a un usuario de hotel sin hoteles asignados. "
                "Para revocar su acceso, desactívelo o elimínelo.",
            }
        existing = set(
            int(doc["prop_id"])
            for doc in db.dim_hotels.find({"prop_id": {"$in": hotels}}, {"prop_id": 1})
        )
        missing = [h for h in hotels if h not in existing]
        if missing:
            return {"ok": False, "message": f"Los hoteles no existen: {', '.join(map(str, missing))}."}
        updates["assigned_hotels"] = hotels

    is_active = payload.get("is_active")
    if is_active is not None:
        new_state = bool(is_active)
        if acting_user.get("_id") == target_user.get("_id") and not new_state:
            return {"ok": False, "message": "No puede desactivar su propia cuenta desde esta vista."}
        updates["is_active"] = new_state
        if not new_state:
            db.user_sessions.update_many(
                {"user_id": object_id, "is_active": True},
                {"$set": {"is_active": False, "end_reason": "user_deactivated"}},
            )

    password = payload.get("password")
    if password is not None:
        password = str(password)
        if len(password) < 6:
            return {"ok": False, "message": "La contraseña debe tener al menos 6 caracteres."}
        updates["password_hash"] = password_context.hash(password)
        updates["must_change_password"] = True

    if not updates:
        return {"ok": False, "message": "No se enviaron campos válidos para actualizar."}

    updates["updated_at"] = utc_now()
    updates["updated_by"] = acting_user.get("username")
    db.users.update_one({"_id": object_id}, {"$set": updates})

    updated_fields = [
        key
        for key in updates
        if key not in ("updated_at", "updated_by", "password_hash", "must_change_password")
    ]
    db.user_activity_logs.insert_one(
        {
            "user_id": acting_user.get("_id"),
            "username": acting_user.get("username"),
            "email": acting_user.get("email"),
            "action": "admin.user_updated",
            "module": "admin",
            "details": {
                "target_user_id": str(target_user["_id"]),
                "target_username": target_user.get("username"),
                "updated_fields": updated_fields,
                "password_reset": "password_hash" in updates,
            },
            "created_at": utc_now(),
        }
    )

    return {
        "ok": True,
        "message": f"Usuario {target_user.get('username')} actualizado correctamente.",
    }


def toggle_user_active(target_user_id: str, acting_user: dict[str, Any]) -> dict[str, Any]:
    db = get_database()
    if not target_user_id:
        return {"ok": False, "message": "Usuario no válido."}

    try:
        object_id = ObjectId(target_user_id)
    except InvalidId:
        return {"ok": False, "message": "Identificador de usuario inválido."}

    target_user = db.users.find_one({"_id": object_id})
    if not target_user:
        return {"ok": False, "message": "Usuario no encontrado."}

    if acting_user.get("_id") == target_user.get("_id"):
        return {"ok": False, "message": "No puede desactivar su propia cuenta desde esta vista."}

    if is_super_admin(target_user):
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
    except InvalidId:
        return {"ok": False, "message": "Identificador de usuario inválido."}

    target_user = db.users.find_one({"_id": object_id})
    if not target_user:
        return {"ok": False, "message": "Usuario no encontrado."}

    if acting_user.get("_id") == target_user.get("_id"):
        return {"ok": False, "message": "No puede eliminar su propia cuenta."}

    if is_super_admin(target_user):
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
