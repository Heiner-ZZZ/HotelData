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


def ensure_read_dependencies(
    explicit_codes: set[str],
    available_codes: set[str] | None = None,
) -> set[str]:
    """Ensure every non-read action has its resource's ``read`` permission.

    The editor and API both use this invariant: an actor cannot be granted
    create/update/delete/manage/execute access to a resource without being
    able to read that resource's UI/data. When a catalog is supplied, only
    existing permission codes are added.
    """
    normalized = set(explicit_codes)
    for code in tuple(explicit_codes):
        if "." not in code:
            continue
        resource, action = code.split(".", 1)
        if action == "read":
            continue
        read_code = f"{resource}.read"
        if available_codes is None or read_code in available_codes:
            normalized.add(read_code)
    return normalized


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


def _get_hotel_scoped_codes(
    db: Database,
    user: dict[str, Any],
    prop_id: int,
) -> set[str]:
    """Resolve hotel-scoped permission codes for ``user`` in ``prop_id``.

    Fase 1 RBAC por hotel (``docs/PERMISOS_POR_HOTEL.md``). Deny-by-default:

    1. Look up the user's ``role_assignments`` row for the hotel.
    2. No assignment → empty set (deny). The global role is NEVER used as a
       fallback here — doing so would let a restricted hotel-1 employee gain
       the global role's permissions on hotel-2 routes (cross-hotel escalation).
    3. Assignment found → the ``hotel_roles`` doc is authoritative: an
       inactive or missing hotel role also denies (empty set).
    """
    assignment = db.role_assignments.find_one(
        {"user_id": user["_id"], "prop_id": int(prop_id)}
    )
    if not assignment:
        return set()
    role = db.hotel_roles.find_one(
        {"_id": assignment.get("role_id"), "is_active": True}
    )
    if not role:
        return set()
    return expand_permissions(set(role.get("permissions", [])))


def get_user_permission_codes(
    db: Database,
    user: dict[str, Any],
    prop_id: int | None = None,
) -> set[str]:
    """Return the expanded set of permission codes for a user.

    Reads from the ``roles.permissions`` embedded array (canonical source)
    when no hotel context is given.

    When ``prop_id`` is provided (Fase 1 hotel-scoped RBAC), permissions are
    resolved STRICTLY from ``role_assignments`` → ``hotel_roles`` for that
    hotel: no assignment for the hotel means no permissions (deny-by-default,
    per ``docs/PERMISOS_POR_HOTEL.md``). The global role resolution below is
    only used when no hotel context is given (legacy ``require_permission``
    paths and system roles).
    """
    if not user:
        return set()
    if is_super_admin(user):
        return {"*.*"}

    if prop_id is not None:
        return _get_hotel_scoped_codes(db, user, prop_id)

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


def user_has_permission(
    db: Database,
    user: dict[str, Any] | None,
    permission_code: str,
    prop_id: int | None = None,
) -> bool:
    """Check whether a user has a specific permission.

    ``super_admin`` always returns ``True``.
    Inactive users always return ``False``.

    When ``prop_id`` is provided (Fase 1 hotel-scoped RBAC), permissions are
    resolved strictly from the user's ``role_assignments`` → ``hotel_roles``
    for that hotel — no assignment means deny (no global fallback).
    """
    if not user or not user.get("is_active", True):
        return False
    if is_super_admin(user):
        return True
    codes = get_user_permission_codes(db, user, prop_id=prop_id)
    if "*.*" in codes:
        return True
    return permission_code in codes
