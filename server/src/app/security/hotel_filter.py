from __future__ import annotations

from typing import Any

from src.app.security.session import get_current_user, SESSION_COOKIE_NAME
from src.database.connection import get_database
from starlette.requests import Request


UNFILTERED_ROLES = {"super_admin", "admin_sistema", "cliente"}


def assigned_hotels_for_user(user: dict[str, Any] | None) -> list[int]:
    """Return the list of prop_ids the user is allowed to access.

    - super_admin, admin_sistema, cliente → empty list (no restriction)
    - Others with assigned_hotels → their assigned list
    - Others without assigned_hotels → empty list (no restriction)
    """
    if not user:
        return []
    role = user.get("primary_role", "")
    if role in UNFILTERED_ROLES:
        return []
    assigned = user.get("assigned_hotels")
    if isinstance(assigned, list) and len(assigned) > 0:
        return [int(p) for p in assigned]
    return []


def hotel_filter_from_user(user: dict[str, Any] | None) -> dict[str, Any]:
    """Build a MongoDB filter dict to restrict results to the user's assigned hotels.

    Returns an empty dict when no filtering is needed.
    """
    ids = assigned_hotels_for_user(user)
    if not ids:
        return {}
    return {"prop_id": {"$in": ids}}


def user_can_access_hotel(user: dict[str, Any] | None, prop_id: int) -> bool:
    """Check whether *user* is allowed to access a specific hotel property.

    super_admin, admin_sistema, cliente → always True.
    Others → True only if prop_id is in assigned_hotels (or assigned_hotels is empty).
    """
    if not user:
        return True
    role = user.get("primary_role", "")
    if role in UNFILTERED_ROLES:
        return True
    assigned = user.get("assigned_hotels")
    if isinstance(assigned, list) and len(assigned) > 0:
        int_ids = [int(p) for p in assigned]
        return prop_id in int_ids
    return True


def resolve_hotel_filter(request: Request) -> dict[str, Any]:
    """Shortcut: resolve the hotel filter from the current HTTP request.

    Reads the session cookie, looks up the user, and returns the filter.
    """
    db = get_database()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user, _ = get_current_user(db, token)
    return hotel_filter_from_user(user)
