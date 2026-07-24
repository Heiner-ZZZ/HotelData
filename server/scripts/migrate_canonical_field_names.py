"""
Normalize canonical field names across dimension collections.

Phase 2 migration — ensures every document has the canonical label field
populated, copying from legacy field names when needed.

Collections & mappings:
  dim_hotels:           hotel_label → display_name (only if display_name missing)
  dim_destinations:     destination_label → destination_name (only if missing)
  dim_visitor_countries: visitor_country_label → country_name (only if missing)

Idempotent — safe to run multiple times.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path (works both locally and inside Docker)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import get_settings
from pymongo import MongoClient, UpdateOne

BATCH_SIZE = 5000


def migrate_dim_hotels(db) -> int:
    """Ensure every dim_hotels doc has display_name."""
    coll = db.dim_hotels
    # Find docs missing display_name (or display_name empty)
    cursor = coll.find(
        {"$or": [
            {"display_name": {"$exists": False}},
            {"display_name": None},
            {"display_name": ""},
        ]},
        {"_id": 1, "hotel_label": 1, "hotel_name": 1, "prop_id": 1},
    ).batch_size(BATCH_SIZE)

    ops = []
    updated = 0
    for doc in cursor:
        fallback = (
            doc.get("hotel_label")
            or doc.get("hotel_name")
            or f"Hotel {doc.get('prop_id', '?')}"
        )
        ops.append(UpdateOne(
            {"_id": doc["_id"]},
            {"$set": {"display_name": fallback.strip()}},
        ))
        if len(ops) >= BATCH_SIZE:
            result = coll.bulk_write(ops, ordered=False)
            updated += result.modified_count
            ops.clear()

    if ops:
        result = coll.bulk_write(ops, ordered=False)
        updated += result.modified_count

    print(f"  dim_hotels: {updated} docs updated with display_name")
    return updated


def migrate_dim_destinations(db) -> int:
    """Ensure every dim_destinations doc has destination_name."""
    coll = db.dim_destinations
    cursor = coll.find(
        {"$or": [
            {"destination_name": {"$exists": False}},
            {"destination_name": None},
            {"destination_name": ""},
        ]},
        {"_id": 1, "destination_label": 1, "srch_destination_id": 1},
    ).batch_size(BATCH_SIZE)

    ops = []
    updated = 0
    for doc in cursor:
        fallback = (
            doc.get("destination_label")
            or f"Destino {doc.get('srch_destination_id', '?')}"
        )
        ops.append(UpdateOne(
            {"_id": doc["_id"]},
            {"$set": {"destination_name": fallback.strip()}},
        ))
        if len(ops) >= BATCH_SIZE:
            result = coll.bulk_write(ops, ordered=False)
            updated += result.modified_count
            ops.clear()

    if ops:
        result = coll.bulk_write(ops, ordered=False)
        updated += result.modified_count

    print(f"  dim_destinations: {updated} docs updated with destination_name")
    return updated


def migrate_dim_visitor_countries(db) -> int:
    """Ensure every dim_visitor_countries doc has country_name."""
    coll = db.dim_visitor_countries
    cursor = coll.find(
        {"$or": [
            {"country_name": {"$exists": False}},
            {"country_name": None},
            {"country_name": ""},
        ]},
        {"_id": 1, "visitor_country_label": 1, "visitor_location_country_id": 1},
    ).batch_size(BATCH_SIZE)

    ops = []
    updated = 0
    for doc in cursor:
        fallback = (
            doc.get("visitor_country_label")
            or f"Pais visitante {doc.get('visitor_location_country_id', '?')}"
        )
        ops.append(UpdateOne(
            {"_id": doc["_id"]},
            {"$set": {"country_name": fallback.strip()}},
        ))
        if len(ops) >= BATCH_SIZE:
            result = coll.bulk_write(ops, ordered=False)
            updated += result.modified_count
            ops.clear()

    if ops:
        result = coll.bulk_write(ops, ordered=False)
        updated += result.modified_count

    print(f"  dim_visitor_countries: {updated} docs updated with country_name")
    return updated


def main():
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    print("=== Normalizando nombres canónicos de campos ===\n")

    total = 0
    total += migrate_dim_hotels(db)
    total += migrate_dim_destinations(db)
    total += migrate_dim_visitor_countries(db)

    print(f"\nTotal docs actualizados: {total}")
    client.close()


if __name__ == "__main__":
    main()
