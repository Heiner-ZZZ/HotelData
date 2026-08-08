from __future__ import annotations

from typing import Any

from src.app.security.role_helpers import get_role_name, is_unfiltered_role
from src.app.security.session import get_current_user, SESSION_COOKIE_NAME
from src.database.connection import get_database
from starlette.requests import Request


# UNFILTERED_ROLES is now defined in src.app.security.role_helpers
# Use is_unfiltered_role() for role-based hotel access checks.


def _coerce_prop_ids(values: Any) -> list[int]:
    """Best-effort conversion of a raw ``assigned_hotels`` value to ints.

    Skips non-numeric entries instead of raising: a malformed value must not
    turn a scope check into a 500.
    """
    if not isinstance(values, list):
        return []
    ids: list[int] = []
    for p in values:
        try:
            ids.append(int(p))
        except (TypeError, ValueError):
            continue
    return ids


def assigned_hotels_for_user(user: dict[str, Any] | None) -> list[int] | None:
    """Return the list of prop_ids the user is allowed to access.

    Three states (deny-by-default for restricted roles):

    - ``None`` → no restriction (anonymous, super_admin, admin_sistema, cliente)
    - ``[]`` → restricted role with NO assigned hotels → access to NO hotel
      (this used to mean "no restriction" = access to the whole system — the
      bug class fixed by the hotel-scope hardening; callers MUST treat [] as
      "none", not "all")
    - ``[1, 2, 3]`` → those hotels
    """
    if not user:
        return None
    if is_unfiltered_role(user):
        return None
    return _coerce_prop_ids(user.get("assigned_hotels"))


def hotel_filter_from_user(user: dict[str, Any] | None) -> dict[str, Any]:
    """Build a MongoDB filter dict to restrict results to the user's assigned hotels.

    - ``{}`` → no filtering (unrestricted scope: anonymous/unfiltered roles)
    - ``{"prop_id": {"$in": []}}`` → restricted role without hotels: matches
      NOTHING (deny-by-default; an empty dict here used to mean "all hotels")
    - ``{"prop_id": {"$in": ids}}`` → only the assigned hotels
    """
    ids = assigned_hotels_for_user(user)
    if ids is None:
        return {}
    if not ids:
        return {"prop_id": {"$in": []}}
    return {"prop_id": {"$in": ids}}


def user_can_access_hotel(user: dict[str, Any] | None, prop_id: int) -> bool:
    """Check whether *user* is allowed to access a specific hotel property.

    - ``None`` (anonymous) → True (public routes guard the check elsewhere).
    - super_admin, admin_sistema, cliente → always True (unfiltered roles).
    - Others → True ONLY if prop_id is in ``assigned_hotels``. A restricted
      user with an EMPTY ``assigned_hotels`` list is denied for every hotel
      (deny-by-default). Previously an empty list meant "no restriction" —
      the security bug this function now closes at the root.
    """
    if not user:
        return True
    if is_unfiltered_role(user):
        return True
    ids = _coerce_prop_ids(user.get("assigned_hotels"))
    return bool(ids) and prop_id in ids


def resolve_hotel_filter(request: Request) -> dict[str, Any]:
    """Shortcut: resolve the hotel filter from the current HTTP request.

    Reads the session cookie, looks up the user, and returns the filter.
    """
    db = get_database()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user, _ = get_current_user(db, token)
    return hotel_filter_from_user(user)
