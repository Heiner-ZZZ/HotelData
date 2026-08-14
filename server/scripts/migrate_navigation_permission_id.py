"""
Migrate navigation: backfill permission_id from permission_code string.

For every navigation node that has `permission_code` set, resolves it to
the corresponding `_id` in the `permissions` collection and stores it as
`permission_id` (ObjectId).

Also creates an index on `permission_id`.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_navigation_permission_id.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from pymongo import MongoClient, ASCENDING

from config.settings import get_settings

settings = get_settings()
client: MongoClient = MongoClient(settings.mongo_uri)
db = client[settings.mongo_database]

# Build lookup: permission_code → ObjectId
print("Building permission lookup from permissions collection...")
code_to_id: dict[str, object] = {}
for perm_doc in db.permissions.find({}, {"permission_code": 1}):
    code = perm_doc.get("permission_code", "").strip()
    if code:
        code_to_id[code] = perm_doc["_id"]

print(f"  → {len(code_to_id)} permissions loaded.")

# Find navigation nodes with permission_code but without permission_id
query = {
    "permission_code": {"$exists": True, "$ne": ""},
    "$or": [
        {"permission_id": {"$exists": False}},
        {"permission_id": None},
    ],
}

total = db.navigation.count_documents(query)
print(f"\nNavigation items needing migration: {total}")

if total == 0:
    print("Nothing to migrate. Checking index...")
else:
    updated = 0
    skipped = 0

    for doc in db.navigation.find(query, {"permission_code": 1}):
        code = (doc.get("permission_code") or "").strip()
        perm_id = code_to_id.get(code)

        if perm_id:
            db.navigation.update_one(
                {"_id": doc["_id"]},
                {"$set": {"permission_id": perm_id}},
            )
            updated += 1
        else:
            skipped += 1
            print(f"  ⚠ No permission match for '{code}' → nav item {doc['_id']}")

    print(f"\nDone. {updated} updated, {skipped} skipped (no matching permission).")

# Create index on permission_id
print("\nCreating permission_id index...")
try:
    db.navigation.create_index([("permission_id", ASCENDING)], name="idx_nav_permission_id")
    print("  → Index idx_nav_permission_id created.")
except Exception as e:
    print(f"  → Index may already exist: {e}")

client.close()
print("\nAll done.")
