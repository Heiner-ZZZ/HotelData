from __future__ import annotations

from typing import Any

from src.app.security.navigation import get_navigation_for_role
from src.app.security.permissions import expand_permissions
from src.database.connection import get_database

from ._helpers import _clean, ensure_user_status_field


def role_permission_map() -> dict[str, list[str]]:
    """Return role_name → [permission_code, ...] from the embedded ``roles.permissions`` array.

    Falls back to the legacy ``role_permissions`` junction table for roles
    that have not been migrated yet.
    """
    db = get_database()
    mapping: dict[str, list[str]] = {}

    # ── Read from embedded permissions array (post-migration) ──
    for role in db.roles.find({}, {"role_name": 1, "permissions": 1}):
        role_name = role.get("role_name")
        perms = role.get("permissions", [])
        if role_name and perms:
            mapping[role_name] = perms

    # ── Fallback: junction table for unmigrated roles ──
    if not mapping:
        rows = list(db.role_permissions.find({}, {"_id": 0, "role_name": 1, "permission_code": 1}).sort([("role_name", 1), ("permission_code", 1)]))
        for item in rows:
            role_name = item.get("role_name")
            permission_code = item.get("permission_code")
            if not role_name or not permission_code:
                continue
            mapping.setdefault(role_name, []).append(permission_code)

    return mapping


def security_overview(limit: int = 20) -> dict[str, Any]:
    ensure_user_status_field()
    db = get_database()
    role_permissions = role_permission_map()
    roles = [_clean(item) for item in db.roles.find({}).sort("role_name", 1)]
    for role in roles:
        role_name = role.get("role_name")
        permissions = role_permissions.get(role_name, [])
        role["permission_codes"] = permissions
        expanded = expand_permissions(set(permissions))
        role["access_buttons"] = get_navigation_for_role(role_name, expanded)
    return {
        "users": [_clean(item) for item in db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit)],
        "roles": roles,
        "permissions": [_clean(item) for item in db.permissions.find({}).sort("permission_code", 1)],
        "sessions": [_clean(item) for item in db.user_sessions.find({}).sort("created_at", -1).limit(limit)],
        "activity": [_clean(item) for item in db.user_activity_logs.find({}).sort("created_at", -1).limit(limit)],
        "counts": {
            "users": db.users.count_documents({}),
            "roles": db.roles.count_documents({}),
            "permissions": db.permissions.count_documents({}),
            "sessions": db.user_sessions.count_documents({}),
            "activity": db.user_activity_logs.count_documents({}),
        },
    }


def users_overview(limit: int = 50) -> dict[str, Any]:
    ensure_user_status_field()
    db = get_database()
    users = [_clean(item) for item in db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit)]
    roles = {str(item["_id"]): item.get("role_name") for item in db.roles.find({})}
    for user in users:
        user["role_names"] = [roles.get(str(role_id), str(role_id)) for role_id in user.get("role_ids", [])]
    return {
        "users": users,
        "roles": [_clean(item) for item in db.roles.find({}).sort("role_name", 1)],
        "counts": {
            "users": db.users.count_documents({}),
            "roles": db.roles.count_documents({}),
        },
    }
