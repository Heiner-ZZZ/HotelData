from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId
from pymongo.database import Database


logger = logging.getLogger(__name__)


def _normalize_role_ids(user: dict[str, Any]) -> list[ObjectId]:
    role_ids: list[ObjectId] = []
    for role_id in user.get("role_ids", []) or []:
        if isinstance(role_id, ObjectId):
            role_ids.append(role_id)
        elif isinstance(role_id, str):
            try:
                role_ids.append(ObjectId(role_id))
            except Exception:
                continue
    return role_ids


def get_user_permission_codes(db: Database, user: dict[str, Any]) -> set[str]:
    role_ids = _normalize_role_ids(user)
    primary_role = user.get("primary_role")
    if primary_role:
        role = db.roles.find_one({"role_name": primary_role})
        if role and role["_id"] not in role_ids:
            role_ids.append(role["_id"])
        elif not role:
            # The user has a `primary_role` but the `roles` collection
            # does not contain it. This usually means the security seed
            # (`scripts/init_security_model_ga03.py`) has not been run,
            # or the role was renamed. Log so the gap is visible in
            # dev/test without crashing the request.
            logger.debug(
                "permissions.primary_role_unresolved user=%s primary_role=%s",
                user.get("username"),
                primary_role,
            )
    if not role_ids:
        return set()
    cursor = db.role_permissions.find({"role_id": {"$in": role_ids}}, {"permission_code": 1})
    return {item["permission_code"] for item in cursor if item.get("permission_code")}


def user_has_permission(db: Database, user: dict[str, Any] | None, permission_code: str) -> bool:
    if not user or not user.get("is_active", True):
        return False
    if user.get("primary_role") == "super_admin":
        return True
    return permission_code in get_user_permission_codes(db, user)
