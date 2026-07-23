"""
Migrate booking_orders.assigned_rooms: backfill room labels → hotel_room_id.

Current state: new writes already store hotel_room_id strings (e.g., "HR-1-101").
Legacy documents may store room labels ("101", "Suite 1"), room_number values,
or dicts with room_label/room_number keys.

This script resolves each legacy value to its hotel_room_id from the hotel_rooms
collection and replaces the array. Already-migrated entries (HR-* prefix) are kept.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_booking_assigned_rooms.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from bson import ObjectId
from pymongo import MongoClient

from config.settings import get_settings

settings = get_settings()
client: MongoClient = MongoClient(settings.mongo_uri)
db = client[settings.mongo_database]

# Find bookings with assigned_rooms that need migration
# Criteria: have assigned_rooms, but at least one entry is NOT a hotel_room_id (doesn't start with "HR-")
# or is a dict (legacy format)
query = {
    "assigned_rooms": {"$exists": True, "$ne": [], "$type": "array"},
}

total = db.booking_orders.count_documents(query)
print(f"Bookings with assigned_rooms: {total}")

if total == 0:
    print("Nothing to migrate. Done.")
    sys.exit(0)

# Build lookup: room_label → hotel_room_id AND room_number → hotel_room_id
print("Building hotel_rooms lookup...")
label_to_hrid: dict[str, str] = {}
number_to_hrid: dict[str, str] = {}
for room in db.hotel_rooms.find({}, {"hotel_room_id": 1, "room_label": 1, "room_number": 1, "prop_id": 1}):
    hrid = room.get("hotel_room_id", "")
    if hrid:
        label = room.get("room_label", "")
        number = room.get("room_number", "")
        prop_id = room.get("prop_id", 0)
        if label:
            label_to_hrid[f"{prop_id}:{label}"] = hrid
        if number:
            number_to_hrid[f"{prop_id}:{number}"] = hrid

print(f"  → {len(label_to_hrid)} label→hrid, {len(number_to_hrid)} number→hrid mappings.")

updated = 0
skipped = 0
already_migrated = 0

for doc in db.booking_orders.find(query, {"assigned_rooms": 1, "prop_id": 1}):
    assigned = doc.get("assigned_rooms") or []
    if not assigned:
        continue

    prop_id = doc.get("prop_id", 0)
    new_ids: list[str] = []
    needs_update = False

    for entry in assigned:
        if isinstance(entry, dict):
            # Legacy dict format: {"room_label": "101", "room_number": "101"}
            label = entry.get("room_label", "") or entry.get("room_number", "")
            hrid = label_to_hrid.get(f"{prop_id}:{label}") or number_to_hrid.get(f"{prop_id}:{label}")
            if hrid:
                new_ids.append(hrid)
                needs_update = True
            else:
                # Keep as-is if we can't resolve
                new_ids.append(str(label))
                skipped += 1
        elif isinstance(entry, str):
            if entry.startswith("HR-"):
                # Already migrated
                new_ids.append(entry)
            else:
                # Legacy label string
                hrid = label_to_hrid.get(f"{prop_id}:{entry}") or number_to_hrid.get(f"{prop_id}:{entry}")
                if hrid:
                    new_ids.append(hrid)
                    needs_update = True
                else:
                    new_ids.append(entry)
                    skipped += 1
        else:
            new_ids.append(str(entry))

    if not needs_update:
        already_migrated += 1
        continue

    # Use $set to replace the entire array
    db.booking_orders.update_one(
        {"_id": doc["_id"]},
        {"$set": {"assigned_rooms": new_ids}},
    )
    updated += 1

print(f"\nDone.")
print(f"  Already migrated (no change needed): {already_migrated}")
print(f"  Updated: {updated}")
print(f"  Unresolvable entries: {skipped}")
client.close()
