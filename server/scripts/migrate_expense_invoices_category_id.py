"""
Migrate expense_invoices: backfill category_id from category string.

For every invoice that has a `category` string value, resolves it to the
corresponding `_id` in the `expense_categories` collection and stores it as
`category_id` (ObjectId). Invoices without a matching category are skipped.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_expense_invoices_category_id.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from pymongo import MongoClient, ASCENDING

from config.settings import get_settings

settings = get_settings()
client: MongoClient = MongoClient(settings.mongo_uri)
db = client[settings.mongo_database]

INVOICES_COLLECTION = "expense_invoices"
CATEGORIES_COLLECTION = "expense_categories"

# Build lookup: category_name → ObjectId
print("Building category lookup from expense_categories...")
cat_lookup: dict[str, object] = {}
for cat_doc in db[CATEGORIES_COLLECTION].find({}, {"name": 1}):
    name = cat_doc.get("name", "").strip()
    if name:
        cat_lookup[name] = cat_doc["_id"]

print(f"  → {len(cat_lookup)} categories loaded.")

# Find invoices without category_id
query = {
    "category": {"$exists": True, "$ne": ""},
    "$or": [
        {"category_id": {"$exists": False}},
        {"category_id": None},
    ],
}

total = db[INVOICES_COLLECTION].count_documents(query)
print(f"\nInvoices needing migration: {total}")

if total == 0:
    print("Nothing to migrate. Done.")
    sys.exit(0)

updated = 0
skipped = 0

for doc in db[INVOICES_COLLECTION].find(query, {"category": 1}):
    cat_name = doc.get("category", "").strip()
    cat_id = cat_lookup.get(cat_name)

    if cat_id:
        db[INVOICES_COLLECTION].update_one(
            {"_id": doc["_id"]},
            {"$set": {"category_id": cat_id}},
        )
        updated += 1
    else:
        skipped += 1
        print(f"  ⚠ No category match for '{cat_name}' → invoice {doc['_id']}")

print(f"\nDone. {updated} updated, {skipped} skipped (no matching category).")
client.close()
