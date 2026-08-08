"""Add the Fase 2 permission ``hotel.manage_roles`` to the dev/current DB.

Idempotent; accepts ``--dry-run``.

Applies three targeted updates (no resets):
  1. Upserts the permission code in the ``permissions`` catalog.
  2. ``$addToSet`` the code into ``roles.permissions`` for the two
     hotel-admin templates (``hotel_partner``, ``gerente_hotel``).
  3. ``$addToSet`` the code into the existing ``hotel_roles.permissions``
     clones of those templates (created by ``migrate_hotel_roles.py`` BEFORE
     this permission existed) so hotel-scoped resolution grants it too.

The canonical seed definitions live in ``init_security_model_ga03.py``
(PERMISSION_CATALOG + ROLE_PERMISSION_CODES) and ``sync_role_permissions.py``
(ROLE_PERMISSIONS) — this script only backfills a running DB.

Run: python scripts/sync_hotel_manage_roles.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database

PERMISSION_CODE = "hotel.manage_roles"
PERMISSION_DESCRIPTION = "Gestionar roles y permisos del equipo en un hotel"
ADMIN_TEMPLATE_ROLES = ("hotel_partner", "gerente_hotel")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sync_hotel_manage_roles(db: Any, *, dry_run: bool = False) -> dict[str, Any]:
    now = utc_now()
    summary = {
        "permission_upserted": False,
        "templates_updated": 0,
        "hotel_roles_updated": 0,
        "dry_run": dry_run,
    }

    # 1) Catalog upsert.
    existing_perm = db.permissions.find_one({"permission_code": PERMISSION_CODE}, {"_id": 1})
    if existing_perm is None:
        if not dry_run:
            db.permissions.update_one(
                {"permission_code": PERMISSION_CODE},
                {
                    "$set": {
                        "permission_code": PERMISSION_CODE,
                        "description": PERMISSION_DESCRIPTION,
                        "is_system": True,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        summary["permission_upserted"] = True

    # 2) Templates (roles collection).
    if not dry_run:
        result = db.roles.update_many(
            {"role_name": {"$in": list(ADMIN_TEMPLATE_ROLES)}},
            {"$addToSet": {"permissions": PERMISSION_CODE}},
        )
        summary["templates_updated"] = result.modified_count
    else:
        summary["templates_updated"] = db.roles.count_documents(
            {
                "role_name": {"$in": list(ADMIN_TEMPLATE_ROLES)},
                "permissions": {"$ne": PERMISSION_CODE},
            }
        )

    # 3) Existing hotel_roles clones.
    if not dry_run:
        result = db.hotel_roles.update_many(
            {"name": {"$in": list(ADMIN_TEMPLATE_ROLES)}},
            {"$addToSet": {"permissions": PERMISSION_CODE}},
        )
        summary["hotel_roles_updated"] = result.modified_count
    else:
        summary["hotel_roles_updated"] = db.hotel_roles.count_documents(
            {
                "name": {"$in": list(ADMIN_TEMPLATE_ROLES)},
                "permissions": {"$ne": PERMISSION_CODE},
            }
        )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill hotel.manage_roles (catálogo + plantillas + hotel_roles)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reporta lo que haría sin escribir.",
    )
    args = parser.parse_args(argv)

    db = get_database()
    summary = sync_hotel_manage_roles(db, dry_run=args.dry_run)
    print(summary)
    action = "Would apply" if args.dry_run else "Applied"
    print(
        f"{action}: permission={summary['permission_upserted']}, "
        f"templates={summary['templates_updated']}, hotel_roles={summary['hotel_roles_updated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
