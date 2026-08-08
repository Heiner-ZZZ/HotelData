"""Collections bootstrap for the Fase 1 hotel-scoped RBAC model.

Two new collections back the per-hotel permission model:

- ``hotel_roles`` — per-property role instances cloned from global role
  templates (``roles``). ``based_on_role_id`` points at the template.
- ``role_assignments`` — junction table ``user × hotel × role`` (the
  industry-standard role-per-property pattern). Unique per (user, prop).

Hotel identity uses the integer ``prop_id`` (project convention — see
``assigned_hotels`` in users); role references use ObjectId FKs.
"""

from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from src.database.collections import ensure_collection

HOTEL_ROLES_COLLECTION = "hotel_roles"
ROLE_ASSIGNMENTS_COLLECTION = "role_assignments"

HOTEL_ROLES_INDEXES = [
    IndexModel(
        [("prop_id", ASCENDING), ("name", ASCENDING)],
        unique=True,
        name="idx_hr_prop_name",
    ),
    IndexModel(
        [("prop_id", ASCENDING), ("is_active", ASCENDING)],
        name="idx_hr_prop_active",
    ),
    IndexModel([("based_on_role_id", ASCENDING)], name="idx_hr_based_on"),
]

ROLE_ASSIGNMENTS_INDEXES = [
    IndexModel(
        [("user_id", ASCENDING), ("prop_id", ASCENDING)],
        unique=True,
        name="idx_ra_user_prop",
    ),
    IndexModel(
        [("prop_id", ASCENDING), ("role_id", ASCENDING)],
        name="idx_ra_prop_role",
    ),
    IndexModel([("role_id", ASCENDING)], name="idx_ra_role"),
]


def ensure_hotel_permission_collections() -> None:
    """Create ``hotel_roles`` + ``role_assignments`` with indexes. Idempotent."""
    ensure_collection(HOTEL_ROLES_COLLECTION, HOTEL_ROLES_INDEXES)
    ensure_collection(ROLE_ASSIGNMENTS_COLLECTION, ROLE_ASSIGNMENTS_INDEXES)
