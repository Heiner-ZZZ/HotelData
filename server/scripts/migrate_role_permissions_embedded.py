"""Phase 4 — Migrate role_permissions junction table → roles.permissions embedded array.

Copies all permission codes from ``role_permissions`` into a ``permissions``
array directly on each role document. After this migration:
- ``roles.permissions: [...]`` is the canonical source of truth
- ``role_permissions`` collection should be dropped manually after verification
- ``permissions.py`` reads from the embedded array directly

Usage:
  docker compose -f infra/docker-compose.yml exec -T server python scripts/migrate_role_permissions_embedded.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[mongo_database]


def main() -> None:
    db = get_database()

    # ── Group role_permissions by role_name ──
    pipeline = [
        {"$group": {"_id": "$role_name", "codes": {"$push": "$permission_code"}}},
    ]
    mapping: dict[str, list[str]] = {}
    total_rows = 0
    for doc in db.role_permissions.aggregate(pipeline):
        role_name = doc["_id"]
        codes = sorted(set(doc["codes"]))
        mapping[role_name] = codes
        total_rows += len(doc["codes"])

    print(f"Found {total_rows} role_permission rows across {len(mapping)} roles\n")

    # ── Write permissions array to each role ──
    updated = 0
    skipped = 0
    for role_name, codes in mapping.items():
        role = db.roles.find_one({"role_name": role_name})
        if not role:
            print(f"  ⚠ {role_name}: role not found in roles collection, skipping")
            skipped += 1
            continue

        db.roles.update_one(
            {"_id": role["_id"]},
            {
                "$set": {
                    "permissions": codes,
                    "updated_at": utc_now(),
                }
            },
        )
        updated += 1
        short = codes[:5]
        suffix = f"... (+{len(codes)-5})" if len(codes) > 5 else ""
        print(f"  ✓ {role_name}: {len(codes)} permissions — {short}{suffix}")

    # ── Verify ──
    print(f"\nMigration complete: {updated} roles updated, {skipped} skipped")

    # Check consistency
    all_roles = list(db.roles.find({}, {"role_name": 1, "permissions": 1}))
    with_perms = sum(1 for r in all_roles if r.get("permissions"))
    without_perms = sum(1 for r in all_roles if not r.get("permissions"))
    print(f"Roles with permissions: {with_perms}")
    print(f"Roles without permissions: {without_perms}")


if __name__ == "__main__":
    main()
