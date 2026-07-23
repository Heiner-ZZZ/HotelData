"""Migrate users: add primary_role_id (ObjectId FK → roles._id) and backfill role_ids.

This script is idempotent:
  1. Resolves users.primary_role (string like "super_admin") → primary_role_id (ObjectId)
     by matching against roles.role_name.
  2. If role_ids is None/missing, initializes it to [primary_role_id].
  3. If role_ids exists but contains strings (legacy), converts to ObjectId array.

Does NOT remove the old primary_role string field — that's a separate cleanup step
after all backend code has been updated to use primary_role_id.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def migrate() -> None:
    db = get_database()

    # Build role_name → _id lookup
    print("Building role_name → _id lookup from roles collection...")
    role_map: dict[str, object] = {}
    for role in db.roles.find({}, {"role_name": 1}):
        rn = role.get("role_name", "").strip()
        if rn:
            role_map[rn] = role["_id"]
    print(f"  → {len(role_map)} roles mapped.")

    # Find users needing migration
    query = {
        "$or": [
            {"primary_role_id": {"$exists": False}},
            {"primary_role_id": None},
            {"role_ids": None},
            {"role_ids": {"$exists": False}},
        ]
    }

    users = list(db.users.find(query, {"username": 1, "primary_role": 1, "role_ids": 1}))
    print(f"\nUsers needing migration: {len(users)}")

    updated_primary = 0
    updated_role_ids = 0
    skipped: list[str] = []

    for user in users:
        uid = user["_id"]
        username = user.get("username", "?")
        primary_role = (user.get("primary_role") or "").strip()

        set_fields: dict = {}

        # 1. Resolve primary_role → primary_role_id
        if primary_role:
            role_id = role_map.get(primary_role)
            if role_id:
                set_fields["primary_role_id"] = role_id
                updated_primary += 1
            else:
                skipped.append(f"{username}: primary_role={primary_role!r} not found in roles")
        elif not user.get("primary_role_id"):
            skipped.append(f"{username}: primary_role is empty/null, no role to map")

        # 2. Backfill role_ids if missing/null
        role_ids = user.get("role_ids")
        if role_ids is None or (isinstance(role_ids, list) and len(role_ids) == 0):
            if primary_role and primary_role in role_map:
                set_fields["role_ids"] = [role_map[primary_role]]
                updated_role_ids += 1
            elif "primary_role_id" in set_fields:
                set_fields["role_ids"] = [set_fields["primary_role_id"]]
                updated_role_ids += 1

        if set_fields:
            db.users.update_one({"_id": uid}, {"$set": set_fields})

    print(f"\nDone: {updated_primary} primary_role_id set, {updated_role_ids} role_ids backfilled.")
    if skipped:
        print(f"Skipped {len(skipped)}:")
        for s in skipped:
            print(f"  - {s}")


if __name__ == "__main__":
    migrate()
