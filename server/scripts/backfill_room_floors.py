"""
Backfill floor field in hotel_rooms and room_status_log.

For rooms with numeric room_labels (e.g., '301') but no floor set,
auto-derives floor = room_label // 100 (e.g., '3').

NOTE: Only works when room_label is still a plain numeric string (e.g. "101").
If labels were enriched to "Habitacion 101 - Standard", this script will find
no matches (harmless no-op).

Also propagates the resolved floor to room_status_log for consistency.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/backfill_room_floors.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from pymongo import MongoClient
from config.settings import get_settings

settings = get_settings()
client: MongoClient = MongoClient(settings.mongo_uri)
db = client[settings.mongo_database]

# ── hotel_rooms ──
query = {
    "$or": [
        {"floor": {"$exists": False}},
        {"floor": None},
        {"floor": ""},
    ],
    "room_label": {"$exists": True, "$ne": "", "$regex": r"^\d+$"},
}

total_rooms = db.hotel_rooms.count_documents(query)
print(f"hotel_rooms with numeric room_label but no floor: {total_rooms}")

hotel_updated = 0
if total_rooms > 0:
    for room in db.hotel_rooms.find(query, {"room_label": 1}):
        rn = room.get("room_label", "")
        if rn.isdigit():
            floor = str(int(rn) // 100)
            db.hotel_rooms.update_one(
                {"_id": room["_id"]},
                {"$set": {"floor": floor}},
            )
            hotel_updated += 1
    print(f"  Updated: {hotel_updated}")

# ── room_status_log ──
query2 = {
    "$or": [
        {"floor": {"$exists": False}},
        {"floor": None},
        {"floor": ""},
    ],
    "room_label": {"$exists": True, "$ne": "", "$regex": r"^\d+$"},
}

total_status = db.room_status_log.count_documents(query2)
print(f"\nroom_status_log with numeric room_label but no floor: {total_status}")

status_updated = 0
if total_status > 0:
    for doc in db.room_status_log.find(query2, {"room_label": 1}):
        rn = doc.get("room_label", "")
        if rn.isdigit():
            floor = str(int(rn) // 100)
            db.room_status_log.update_one(
                {"_id": doc["_id"]},
                {"$set": {"floor": floor}},
            )
            status_updated += 1
    print(f"  Updated: {status_updated}")

client.close()
print(f"\nDone. hotel_rooms={hotel_updated}, room_status_log={status_updated}")
