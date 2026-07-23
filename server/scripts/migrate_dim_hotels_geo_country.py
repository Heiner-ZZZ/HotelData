"""
Migrate dim_hotels: backfill geo_country_code and geo_catalog_id from prop_country_id.

For each dim_hotels document, resolves the legacy numeric prop_country_id to:
1. dim_visitor_countries → country_name, then matches to geo_catalog (type=country)
2. geo_country_code: the geo_catalog.code (e.g., "MX", "US")
3. geo_catalog_id: the geo_catalog._id ObjectId

Documents already having geo_country_code are skipped.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_dim_hotels_geo_country.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

import sys
from pymongo import MongoClient, ASCENDING

from config.settings import get_settings

settings = get_settings()
client: MongoClient = MongoClient(settings.mongo_uri)
db = client[settings.mongo_database]

# Step 1: Build visitor_country_id → country_name lookup
print("Building visitor country lookup...")
vid_to_name: dict[int, str] = {}
for doc in db.dim_visitor_countries.find({}, {"visitor_location_country_id": 1, "country_display_name": 1, "country_name": 1, "visitor_country_label": 1}):
    vid = doc.get("visitor_location_country_id")
    name = doc.get("visitor_country_label") or doc.get("country_display_name") or doc.get("country_name")
    if vid is not None:
        vid_to_name[int(vid)] = name or ""

print(f"  → {len(vid_to_name)} visitor countries loaded.")

# Step 2: Build geo_catalog country lookups (name → code, name → _id)
print("Building geo_catalog country lookup...")
geo_name_to_code: dict[str, str] = {}
geo_name_to_id: dict[str, object] = {}
for doc in db.geo_catalog.find({"type": "country"}, {"code": 1, "name": 1}):
    name = doc.get("name", "").strip().lower()
    code = doc.get("code", "")
    if name and code:
        geo_name_to_code[name] = code
        geo_name_to_id[name] = doc["_id"]

print(f"  → {len(geo_name_to_code)} geo countries loaded.")

# Step 3: Find dim_hotels without geo_country_code
query = {
    "$or": [
        {"geo_country_code": {"$exists": False}},
        {"geo_country_code": None},
        {"geo_country_code": ""},
    ],
}

total = db.dim_hotels.count_documents(query)
print(f"\nHotels needing migration: {total}")

if total == 0:
    print("Nothing to migrate. Creating index...")
else:
    updated = 0
    skipped = 0
    for doc in db.dim_hotels.find(query, {"prop_id": 1, "prop_country_id": 1}):
        prop_id = doc.get("prop_id", 0)
        prop_country_id = doc.get("prop_country_id")
        geo_code = None
        geo_id = None

        if prop_country_id is not None:
            country_name = vid_to_name.get(int(prop_country_id), "")
            if country_name:
                name_lower = country_name.strip().lower()
                geo_code = geo_name_to_code.get(name_lower)
                geo_id = geo_name_to_id.get(name_lower)

        if geo_code:
            db.dim_hotels.update_one(
                {"_id": doc["_id"]},
                {"$set": {"geo_country_code": geo_code, "geo_catalog_id": geo_id}},
            )
            updated += 1
        else:
            skipped += 1
            if prop_country_id is not None:
                country_name = vid_to_name.get(int(prop_country_id), f"ID {prop_country_id}")
                print(f"  ⚠ No geo match for prop_id={prop_id} country={country_name}")

    print(f"\nDone. {updated} updated, {skipped} skipped.")

# Step 4: Create geo_country_code index
print("\nCreating geo_country_code index on dim_hotels...")
try:
    db.dim_hotels.create_index([("geo_country_code", ASCENDING)], name="idx_dim_hotels_geo_country")
    print("  → Index idx_dim_hotels_geo_country created.")
except Exception as e:
    print(f"  → Index may already exist: {e}")

client.close()
print("\nAll done.")
