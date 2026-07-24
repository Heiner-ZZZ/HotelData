"""Backfill hotel_room_id into room_status_history documents.

For each room_status_history doc that has a room_label but no hotel_room_id,
resolves the FK by looking up hotel_rooms first, then room_status_log as fallback.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_room_status_history_room_id.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database
from src.app.modules.housekeeping.service.collections import ROOM_STATUS_HISTORY_COLLECTION

db = get_database()

# Find all history docs missing hotel_room_id
query = {"$or": [{"hotel_room_id": {"$exists": False}}, {"room_id": {"$type": "string"}}, {"room_id": None}, {"room_id": {"$exists": False}}]}
total_missing = db[ROOM_STATUS_HISTORY_COLLECTION].count_documents(query)
print(f"Found {total_missing} room_status_history docs without hotel_room_id")

if total_missing == 0:
    print("Nothing to migrate.")
    exit(0)

updated = 0
skipped = 0

for doc in db[ROOM_STATUS_HISTORY_COLLECTION].find(query):
    prop_id = doc.get("prop_id")
    room_label = doc.get("room_label", "")
    if not prop_id or not room_label:
        skipped += 1
        continue

    hotel_room_id = ""

    # Try hotel_rooms (canonical source)
    room = db.hotel_rooms.find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"_id": 1, "hotel_room_id": 1},
    )
    room_object_id = None
    if room and room.get("hotel_room_id"):
        hotel_room_id = room["hotel_room_id"]
        room_object_id = room["_id"]
    else:
        # Fallback to room_status_log
        status_doc = db.room_status_log.find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"hotel_room_id": 1},
        )
        if status_doc and status_doc.get("hotel_room_id"):
            hotel_room_id = status_doc["hotel_room_id"]

    if hotel_room_id:
        try:
            set_doc: dict = {"hotel_room_id": hotel_room_id}
            if room_object_id:
                set_doc["room_id"] = room_object_id
            db[ROOM_STATUS_HISTORY_COLLECTION].update_one(
                {"_id": doc["_id"]},
                {"$set": set_doc},
            )
            updated += 1
        except Exception as e:
            print(f"  ERROR updating {doc['_id']}: {e}")
            skipped += 1
    else:
        print(f"  WARNING: No hotel_room_id found for room_label={room_label} prop_id={prop_id}")
        skipped += 1

print(f"\nMigration complete: {updated} updated, {skipped} skipped")
