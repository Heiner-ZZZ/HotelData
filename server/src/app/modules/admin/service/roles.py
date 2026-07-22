"""Role editor payloads with DB-backed navigation catalog."""

from __future__ import annotations

from typing import Any

from src.app.security.navigation import get_all_navigation_items, get_navigation_for_role
from src.app.security.permissions import expand_permissions
from src.database.connection import get_database

from ._helpers import _clean
from .security import role_permission_map


def _all_permission_codes(db) -> list[str]:
    return [p["permission_code"] for p in db.permissions.find({}, {"permission_code": 1}).sort("permission_code", 1)]


def role_editor_payload(role_name: str) -> dict[str, Any] | None:
    db = get_database()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        return None
    role_clean = _clean(role)
    permissions = [_clean(item) for item in db.permissions.find({}).sort("permission_code", 1)]
    permission_map = role_permission_map()
    selected_codes = permission_map.get(role_name, [])
    if role_name == "super_admin":
        selected_codes = _all_permission_codes(db)
    role_clean["permission_codes"] = selected_codes
    expanded = expand_permissions(set(selected_codes))
    role_clean["access_buttons"] = get_navigation_for_role(role_name, expanded)
    role_clean["navigation_catalog"] = get_all_navigation_items(expanded)
    return {
        "role": role_clean,
        "permissions": permissions,
    }


def role_editor_payload_api(role_name: str) -> dict[str, Any] | None:
    db = get_database()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        return None
    role_clean = _clean(role)
    permissions = [
        {"permission_code": p["permission_code"], "description": p.get("description", "")}
        for p in db.permissions.find({}).sort("permission_code", 1)
    ]
    permission_map = role_permission_map()
    selected_codes = permission_map.get(role_name, [])
    if role_name == "super_admin":
        selected_codes = _all_permission_codes(db)
    role_clean["permission_codes"] = selected_codes
    expanded = expand_permissions(set(selected_codes))
    role_clean["access_buttons"] = get_navigation_for_role(role_name, expanded)
    role_clean["navigation_catalog"] = get_all_navigation_items(expanded)
    return {
        "role": role_clean,
        "permissions": permissions,
    }
