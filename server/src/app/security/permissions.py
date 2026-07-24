"""Permission resolution with wildcard expansion.

Permission codes follow the format ``{resource}.{action}`` where:
- ``action`` is one of: create, read, update, delete, execute, manage
- ``manage`` is a wildcard that expands to all CRUD actions for that resource
- ``execute`` is for ETL/data-pipeline operations (no CRUD expansion)

Expansion example:
    ``reservations.manage``  →  reservations.create, .read, .update, .delete
    ``etl.execute``          →  etl.execute  (no expansion)

super_admin always gets a sentinel ``*.*`` that bypasses all checks.
"""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from src.app.security.role_helpers import get_role_name, is_super_admin


logger = logging.getLogger(__name__)

# Actions that ``.manage`` expands into
_MANAGE_CRUD_ACTIONS = ("create", "read", "update", "delete")


def expand_permissions(explicit_codes: set[str]) -> set[str]:
    """Expand wildcard ``resource.manage`` into individual CRUD permissions.

    - ``*.*`` (super_admin sentinel) is returned as-is.
    - ``resource.manage`` expands to resource.create, .read, .update, .delete
    - All other codes pass through unchanged.
    """
    if "*.*" in explicit_codes:
        return {"*.*"}
    expanded = set(explicit_codes)
    for code in explicit_codes:
        if "." not in code:
            continue
        resource, action = code.split(".", 1)
        if action == "manage":
            expanded.update({f"{resource}.{a}" for a in _MANAGE_CRUD_ACTIONS})
    return expanded


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
    """Return the expanded set of permission codes for a user.

    Reads from the ``roles.permissions`` embedded array (canonical source).
    """
    if not user:
        return set()
    if is_super_admin(user):
        return {"*.*"}

    role_ids = _normalize_role_ids(user)
    primary_role = get_role_name(user)
    if primary_role:
        role = db.roles.find_one({"role_name": primary_role})
        if role and role["_id"] not in role_ids:
            role_ids.append(role["_id"])
        elif not role:
            logger.debug(
                "permissions.primary_role_unresolved user=%s primary_role=%s",
                user.get("username"),
                primary_role,
            )
    if not role_ids:
        return set()

    # ── Read from roles.permissions embedded array (canonical source) ──
    explicit: set[str] = set()
    for r in db.roles.find({"_id": {"$in": role_ids}}, {"permissions": 1}):
        explicit.update(r.get("permissions", []))

    return expand_permissions(explicit)


def user_has_permission(db: Database, user: dict[str, Any] | None, permission_code: str) -> bool:
    """Check whether a user has a specific permission.

    ``super_admin`` always returns ``True``.
    Inactive users always return ``False``.
    """
    if not user or not user.get("is_active", True):
        return False
    if is_super_admin(user):
        return True
    codes = get_user_permission_codes(db, user)
    if "*.*" in codes:
        return True
    return permission_code in codes
