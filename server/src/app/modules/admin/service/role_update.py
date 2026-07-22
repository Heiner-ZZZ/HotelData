from __future__ import annotations

from typing import Any

from src.database.connection import get_database

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

    permission_docs = list(db.permissions.find({"permission_code": {"$in": permission_codes}}))
    valid_codes = sorted({item["permission_code"] for item in permission_docs if item.get("permission_code")})
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
