"""Shared FK resolvers: int/str labels → ObjectId references.

These helpers resolve legacy integer/string foreign keys to proper
MongoDB ObjectId references. All write paths should use these before
inserting documents to ensure referential integrity.

Usage::

    from src.app.core.resolvers import resolve_hotel_id, resolve_employee_id

    hotel_id = resolve_hotel_id(prop_id)  # int → ObjectId
    employee_id = resolve_employee_id("Carlos Mendoza")  # str → ObjectId
"""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from src.database.connection import get_database

logger = logging.getLogger(__name__)

# ── Cache (module-level, invalidated on server restart) ──────────────
_hotel_id_cache: dict[int, ObjectId] = {}
_employee_id_cache: dict[str, ObjectId] = {}
_user_id_cache: dict[str, ObjectId] = {}


def resolve_hotel_id(prop_id: int) -> ObjectId | None:
    """Resolve a ``prop_id`` (int) to ``dim_hotels._id`` (ObjectId).

    Returns ``None`` if the hotel is not found. The result is cached
    at module level for the lifetime of the server process.
    """
    if prop_id in _hotel_id_cache:
        return _hotel_id_cache[prop_id]

    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 1})
    if hotel is None:
        logger.warning("resolve_hotel_id: no dim_hotels row for prop_id=%s", prop_id)
        return None

    oid = hotel["_id"]
    _hotel_id_cache[prop_id] = oid
    return oid


def resolve_employee_id(name: str) -> ObjectId | None:
    """Resolve an employee name to ``employees._id`` (ObjectId).

    Performs a case-insensitive match on ``full_name``.  Returns
    ``None`` if no employee matches.  The result is cached at module
    level.
    """
    clean = name.strip()
    if not clean:
        return None

    if clean in _employee_id_cache:
        return _employee_id_cache[clean]

    db = get_database()
    import re
    pattern = re.compile(f"^{re.escape(clean)}$", re.IGNORECASE)
    emp = db.employees.find_one({"full_name": pattern}, {"_id": 1})
    if emp is None:
        logger.warning("resolve_employee_id: no employee matching name=%r", clean)
        return None

    oid = emp["_id"]
    _employee_id_cache[clean] = oid
    return oid


def resolve_user_id(username: str) -> ObjectId | None:
    """Resolve a ``users.username`` (login principal) to ``users._id`` (ObjectId).

    Performs a case-insensitive exact match. Returns ``None`` if the user
    is not found. The result is cached at module level.

    Use this for **audit-grade FKs** where you need a hard reference to
    the authenticated IAM entity that performed an action (e.g. who
    opened/closed a cash register shift). For HR/roster references that
    match a free-text label, prefer ``resolve_employee_id`` instead.
    """
    clean = (username or "").strip()
    if not clean:
        return None

    if clean in _user_id_cache:
        return _user_id_cache[clean]

    db = get_database()
    import re
    pattern = re.compile(f"^{re.escape(clean)}$", re.IGNORECASE)
    user = db.users.find_one({"username": pattern}, {"_id": 1})
    if user is None:
        logger.warning("resolve_user_id: no users row for username=%r", clean)
        return None

    oid = user["_id"]
    _user_id_cache[clean] = oid
    return oid


def resolve_hotel_name(prop_id: int) -> str:
    """Resolve a ``prop_id`` to the hotel's ``display_name``.

    Returns a fallback string if the hotel is not found.
    """
    db = get_database()
    hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"display_name": 1, "hotel_name": 1, "_id": 0},
    )
    if hotel:
        return hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}"
    return f"Hotel {prop_id}"
