"""Migrate the global roles to templates and backfill per-hotel RBAC (Fase 1).

Fase 1 introduces two new collections that power the per-hotel permission
model (``docs/PERMISOS_POR_HOTEL.md``):

- ``hotel_roles`` — per-property role instances cloned from global role
  templates (``roles``), so the same job title can hold different
  permissions in different hotels (Oracle OPERA "Property Roles" pattern).
- ``role_assignments`` — junction table ``user × hotel × role``.

This script is idempotent and does the following:

  1. Marks every existing role in ``roles`` as a template (``is_template: true``).
  2. For every user with a non-empty ``assigned_hotels`` list, clones their
     primary role into ``hotel_roles`` for each assigned prop_id (one shared
     clone per ``(prop_id, role_name)`` — NOT per user).
  3. Backfills ``role_assignments`` linking each user to their hotel role
     for each assigned prop_id.
  4. Stamps all inserted docs with ``metadata.migration_id`` for audit
     traceability (project convention from ``migrate_inventory_layers.py``).

Idempotency: existence checks before every insert, so re-running is safe
and never creates duplicates.

Run: python /app/scripts/migrate_hotel_roles.py [--dry-run] [--only-prop-id N]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app.security.collections import ensure_hotel_permission_collections
from src.database.connection import get_database

MIGRATION_ID = "hotel_roles_fase1"
CREATED_BY = f"migration:{MIGRATION_ID}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_role_name(
    roles_by_id: dict[Any, dict[str, Any]],
    user: dict[str, Any],
) -> str:
    """Resolve the user's primary role_name preferring the ObjectId FK."""
    role_id = user.get("primary_role_id")
    if role_id:
        role = roles_by_id.get(role_id)
        if role and role.get("role_name"):
            return role["role_name"]
    return (user.get("primary_role") or "").strip()


def migrate_hotel_roles(
    db: Any,
    *,
    dry_run: bool = False,
    only_prop_id: int | None = None,
) -> dict[str, Any]:
    """Idempotent migration. Returns a summary dict (never raises)."""
    # Ensure collections + unique indexes exist even when run standalone
    # (before the server lifespan had a chance to create them). Idempotent.
    ensure_hotel_permission_collections()
    now = utc_now()
    summary: dict[str, Any] = {
        "roles_marked_template": 0,
        "hotel_roles_created": 0,
        "assignments_created": 0,
        "users_processed": 0,
        "users_skipped": 0,
        "dry_run": dry_run,
        "only_prop_id": only_prop_id,
    }

    # 1) Mark existing roles as templates.
    for role in db.roles.find({}, {"_id": 1, "is_template": 1}):
        if not role.get("is_template"):
            if not dry_run:
                db.roles.update_one(
                    {"_id": role["_id"]},
                    {"$set": {"is_template": True}},
                )
            summary["roles_marked_template"] += 1

    # 2) Role lookup maps for cloning.
    roles = {
        r["_id"]: r
        for r in db.roles.find({}, {"role_name": 1, "display_name": 1, "permissions": 1})
    }
    role_by_name = {r["role_name"]: r for r in roles.values() if r.get("role_name")}

    # 3) Per user with assigned_hotels → ensure hotel_role + assignment.
    users = db.users.find(
        {"assigned_hotels": {"$exists": True, "$ne": []}},
        {
            "_id": 1,
            "username": 1,
            "assigned_hotels": 1,
            "primary_role": 1,
            "primary_role_id": 1,
        },
    )
    for user in users:
        role_name = _resolve_role_name(roles, user)
        template = role_by_name.get(role_name)
        if not template:
            summary["users_skipped"] += 1
            continue

        prop_ids: list[int] = []
        for raw in user.get("assigned_hotels", []):
            try:
                prop_ids.append(int(raw))
            except (TypeError, ValueError):
                continue  # valor no numérico: no debe abortar la migración
        prop_ids = [p for p in prop_ids if p >= 1]
        if only_prop_id is not None:
            prop_ids = [p for p in prop_ids if p == only_prop_id]
        if not prop_ids:
            summary["users_skipped"] += 1
            continue
        summary["users_processed"] += 1

        for prop_id in prop_ids:
            hotel_role = db.hotel_roles.find_one(
                {"prop_id": prop_id, "name": role_name},
                {"_id": 1},
            )
            if hotel_role is None:
                hr_id: Any = None
                if not dry_run:
                    hr_id = db.hotel_roles.insert_one(
                        {
                            "prop_id": prop_id,
                            "name": role_name,
                            "display_name": template.get("display_name")
                            or role_name.title(),
                            "permissions": list(template.get("permissions", [])),
                            "based_on_role_id": template["_id"],
                            "is_active": True,
                            "is_system": False,
                            "created_by": CREATED_BY,
                            "created_at": now,
                            "updated_at": now,
                            "metadata": {"migration_id": MIGRATION_ID},
                        }
                    ).inserted_id
                summary["hotel_roles_created"] += 1
            else:
                hr_id = hotel_role["_id"]

            existing = db.role_assignments.find_one(
                {"user_id": user["_id"], "prop_id": prop_id},
                {"_id": 1},
            )
            if existing is None:
                if not dry_run and hr_id is not None:
                    db.role_assignments.insert_one(
                        {
                            "user_id": user["_id"],
                            "prop_id": prop_id,
                            "role_id": hr_id,
                            "assigned_by": CREATED_BY,
                            "assigned_at": now,
                            "metadata": {"migration_id": MIGRATION_ID},
                        }
                    )
                summary["assignments_created"] += 1

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fase 1: roles → plantillas + hotel_roles + role_assignments (idempotente)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reporta lo que haría sin escribir en la base.",
    )
    parser.add_argument(
        "--only-prop-id",
        type=int,
        default=None,
        help="Restringe el backfill a un solo hotel (prop_id).",
    )
    args = parser.parse_args(argv)

    db = get_database()
    summary = migrate_hotel_roles(db, dry_run=args.dry_run, only_prop_id=args.only_prop_id)

    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    action = "Would create" if args.dry_run else "Created"
    print(
        f"{action}: {summary['hotel_roles_created']} hotel_role(s), "
        f"{summary['assignments_created']} assignment(s), "
        f"{summary['roles_marked_template']} template(s) marcado(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
