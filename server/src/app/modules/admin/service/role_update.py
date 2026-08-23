from __future__ import annotations

from typing import Any

from src.database.connection import get_database
from src.app.security.permissions import (
    GUEST_ROLES,
    PLATFORM_ROLES,
    READ_DEP_ACTIONS,
    ensure_read_dependencies,
    permission_scope,
)

from ._helpers import utc_now


def update_role_definition(
    role_name: str,
    description: str,
    permission_codes: list[str],
    acting_user: dict[str, Any],
) -> dict[str, Any]:
    db = get_database()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        return {"ok": False, "message": "Rol no encontrado."}

    if role_name == "super_admin":
        return {"ok": False, "message": "El rol super_admin no se modifica desde esta vista."}

    all_permission_docs = list(db.permissions.find({}, {"permission_code": 1}))
    available_codes = {
        item["permission_code"] for item in all_permission_docs if item.get("permission_code")
    }
    normalized_codes = ensure_read_dependencies(set(permission_codes), available_codes)
    # Solo las acciones CRUD (create/update/delete/manage/execute) implican un
    # ``<resource>.read`` hermano. Los códigos compuestos (``hotel.manage_roles``,
    # ``properties.approve``, ``hr.onboarding.create``) son permisos completos
    # por sí mismos y no exigen un read que no existe en el catálogo — mismo
    # criterio que _filter_preview_codes (ver permissions.READ_DEP_ACTIONS).
    missing_read = sorted(
        f"{code.split('.', 1)[0]}.read"
        for code in normalized_codes
        if '.' in code
        and code.split('.', 1)[1] in READ_DEP_ACTIONS
        and f"{code.split('.', 1)[0]}.read" not in available_codes
    )
    if missing_read:
        return {
            "ok": False,
            "message": "No se pueden guardar acciones sin un permiso Read disponible: "
            + ', '.join(missing_read),
        }
    # ── Guard de scope (C 2026-08, lógica dura) ──────────────────────────
    # El editor global tampoco puede romper el invariante: roles NO-plataforma
    # no portan códigos system (etl.*, users.*, properties.approve…), y roles
    # ≠ cliente no portan códigos guest (account.*, search.*).
    if role_name not in PLATFORM_ROLES:
        platform_bad = sorted(c for c in normalized_codes if permission_scope(c) == "system")
        if platform_bad:
            return {
                "ok": False,
                "message": (
                    "Permisos de plataforma no aplican al rol "
                    f"{role_name}: {', '.join(platform_bad)}"
                ),
            }
    if role_name not in GUEST_ROLES:
        guest_bad = sorted(c for c in normalized_codes if permission_scope(c) == "guest")
        if guest_bad:
            return {
                "ok": False,
                "message": (
                    "Permisos de huésped no aplican al rol "
                    f"{role_name}: {', '.join(guest_bad)}"
                ),
            }
    valid_codes = sorted(normalized_codes & available_codes)
    role_id = role["_id"]

    db.roles.update_one(
        {"_id": role_id},
        {
            "$set": {
                "description": description.strip(),
                "permissions": valid_codes,
                "updated_at": utc_now(),
                "updated_by": acting_user.get("username"),
            }
        },
    )

    db.user_activity_logs.insert_one(
        {
            "user_id": acting_user.get("_id"),
            "username": acting_user.get("username"),
            "email": acting_user.get("email"),
            "action": "admin.role_updated",
            "module": "admin",
            "details": {
                "role_name": role_name,
                "permission_codes": valid_codes,
            },
            "created_at": utc_now(),
        }
    )
    return {"ok": True, "message": f"Rol {role_name} actualizado correctamente."}
