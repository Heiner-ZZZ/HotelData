"""Role resolution helpers for the primary_role → primary_role_id migration.

All helpers work with the transitional state where BOTH fields may exist:
- ``primary_role`` (string, e.g. "super_admin") — legacy, still present
- ``primary_role_id`` (ObjectId → roles._id) — new FK, added by migration

Prefer ``primary_role_id`` for security checks and queries; fall back to
``primary_role`` string for display/pass-through (backward compat).
"""

from __future__ import annotations

from typing import Any

from bson import ObjectId

# Stable role _id for super_admin (never changes)
SUPER_ADMIN_ROLE_ID = ObjectId("6a3b607b914644ec8536df0f")

# Role names that bypass hotel filtering
UNFILTERED_ROLES = {"super_admin", "admin_sistema", "cliente"}


def get_role_name(user: dict[str, Any] | None) -> str:
    """Get the role_name string for a user.

    Prefers resolving from ``primary_role_id`` (ObjectId FK) via roles
    collection. Falls back to the legacy ``primary_role`` string for
    backward compatibility with any docs that still lack the FK.
    """
    if not user:
        return ""
    prid = user.get("primary_role_id")
    if prid:
        from src.database.connection import get_database
        db = get_database()
        role = db.roles.find_one({"_id": prid}, {"role_name": 1})
        if role:
            return role.get("role_name") or ""
    pr = user.get("primary_role") or ""
    return pr


def is_super_admin(user: dict[str, Any] | None) -> bool:
    """Check whether a user has the super_admin role.

    Checks the ObjectId FK first, falling back to the legacy string.
    """
    if not user:
        return False
    if user.get("primary_role_id") == SUPER_ADMIN_ROLE_ID:
        return True
    return user.get("primary_role") == "super_admin"


def resolve_role_id(role_name: str) -> ObjectId | None:
    """Resolve a role_name string to its ObjectId from the roles collection."""
    if not role_name:
        return None
    from src.database.connection import get_database
    db = get_database()
    role = db.roles.find_one({"role_name": role_name}, {"_id": 1})
    return role["_id"] if role else None


def resolve_role_ids(role_names: list[str]) -> list[ObjectId]:
    """Resolve a list of role_name strings to their ObjectIds."""
    if not role_names:
        return []
    from src.database.connection import get_database
    db = get_database()
    ids: list[ObjectId] = []
    for role in db.roles.find({"role_name": {"$in": role_names}}, {"_id": 1}):
        ids.append(role["_id"])
    return ids


def build_role_query(role_names: list[str]) -> dict[str, Any]:
    """Build a MongoDB filter for querying users by role.

    Uses ``primary_role_id`` (ObjectId FK) when roles can be resolved,
    with an ``$or`` fallback to ``primary_role`` string for any roles
    that couldn't be resolved. This ensures the query is never too narrow
    when some role names don't match the catalog.
    """
    if not role_names:
        return {}
    role_ids = resolve_role_ids(role_names)
    if not role_ids:
        return {"primary_role": {"$in": role_names}}
    # All roles resolved → use FK filter exclusively
    if len(role_ids) == len(role_names):
        return {"primary_role_id": {"$in": role_ids}}
    # Partial resolution → $or to cover both resolved and unresolved
    resolved_names: set[str] = set()
    from src.database.connection import get_database
    db = get_database()
    for r in db.roles.find({"_id": {"$in": role_ids}}, {"role_name": 1}):
        resolved_names.add(r.get("role_name", ""))
    unresolved = [n for n in role_names if n not in resolved_names]
    conditions = [{"primary_role_id": {"$in": role_ids}}]
    if unresolved:
        conditions.append({"primary_role": {"$in": unresolved}})
    return {"$or": conditions}


def assign_role(user_doc: dict[str, Any], role_name: str) -> None:
    """Mutate a user document dict to set BOTH primary_role (string) AND primary_role_id (ObjectId).

    Call this when creating or updating a user to ensure both fields stay in sync.
    """
    role_id = resolve_role_id(role_name)
    user_doc["primary_role"] = role_name
    if role_id:
        user_doc["primary_role_id"] = role_id


def is_unfiltered_role(user: dict[str, Any] | None) -> bool:
    """Check if user's role bypasses hotel filtering."""
    return get_role_name(user) in UNFILTERED_ROLES
