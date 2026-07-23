"""Backfill hotel_room_id into stay_service_requests documents.

For each stay_service_requests doc that has a room_label but no hotel_room_id,
resolves the FK by looking up hotel_rooms first, then room_status_log as fallback.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_stay_service_requests_room_id.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database

db = get_database()

query = {"hotel_room_id": {"$exists": False}}
total_missing = db.stay_service_requests.count_documents(query)
print(f"Found {total_missing} stay_service_requests docs without hotel_room_id")

if total_missing == 0:
    print("Nothing to migrate.")
    exit(0)

updated = 0
skipped = 0

for doc in db.stay_service_requests.find(query):
    prop_id = doc.get("prop_id")
    room_label = doc.get("room_label", "")
    if not prop_id or not room_label:
        skipped += 1
        continue

    hotel_room_id = ""

    room = db.hotel_rooms.find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"hotel_room_id": 1},
    )
    if room and room.get("hotel_room_id"):
        hotel_room_id = room["hotel_room_id"]
    else:
        status_doc = db.room_status_log.find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"hotel_room_id": 1},
        )
        if status_doc and status_doc.get("hotel_room_id"):
            hotel_room_id = status_doc["hotel_room_id"]

    # Third fallback: room_label is already a hotel_room_id (e.g., "HR-1-111")
    if not hotel_room_id and room_label.startswith("HR-"):
        exists = db.hotel_rooms.find_one(
            {"prop_id": prop_id, "hotel_room_id": room_label},
            {"_id": 1},
        )
        if exists:
            hotel_room_id = room_label

    if hotel_room_id:
        try:
            db.stay_service_requests.update_one(
                {"_id": doc["_id"]},
                {"$set": {"hotel_room_id": hotel_room_id}},
            )
            updated += 1
        except Exception as e:
            print(f"  ERROR updating {doc['_id']}: {e}")
            skipped += 1
    else:
        print(f"  WARNING: No hotel_room_id found for room_label={room_label} prop_id={prop_id}")
        skipped += 1

print(f"\nMigration complete: {updated} updated, {skipped} skipped")
