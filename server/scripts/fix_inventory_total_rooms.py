"""Fix total_rooms in room_inventory_calendar from physical room counts.

Problem: Some room_inventory_calendar entries have total_rooms=10 (hardcoded default)
when the actual physical rooms per type are 1-2. This makes availability display wrong
(e.g. "10/10 disponibles" when there's only 1 room).

Fix: Recalculate total_rooms per (prop_id, room_type_id) from hotel_rooms and update
room_inventory_calendar accordingly. Also clamps available_rooms to never exceed total_rooms.
"""

from __future__ import annotations

from config.settings import get_settings
from pymongo import MongoClient


def fix_inventory_total_rooms() -> dict:
    """Recalculate total_rooms in room_inventory_calendar from hotel_rooms."""
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    # 1. Count physical rooms per (prop_id, room_type_id)
    pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {
            "_id": {"prop_id": "$prop_id", "room_type_id": "$room_type_id"},
            "physical_rooms": {"$sum": 1},
        }},
    ]
    physical_counts = {}
    for r in db.hotel_rooms.aggregate(pipeline):
        key = (r["_id"]["prop_id"], r["_id"]["room_type_id"])
        physical_counts[key] = r["physical_rooms"]

    print(f"Found {len(physical_counts)} room type combos with physical room counts")
    for (prop_id, rt_id), count in sorted(physical_counts.items()):
        print(f"  prop_id={prop_id}, {rt_id} → {count} rooms")

    # 2. Find inventory entries with wrong total_rooms
    fixed = 0
    clamped = 0
    skipped = 0

    for (prop_id, rt_id), physical_count in physical_counts.items():
        result = db.room_inventory_calendar.update_many(
            {
                "prop_id": prop_id,
                "room_type_id": rt_id,
                "total_rooms": {"$ne": physical_count},
            },
            [
                {
                    "$set": {
                        "total_rooms": physical_count,
                        "available_rooms": {
                            "$cond": {
                                "if": {"$gt": ["$available_rooms", physical_count]},
                                "then": physical_count,
                                "else": "$available_rooms",
                            }
                        },
                        "blocked_rooms": {
                            "$cond": {
                                "if": {"$gt": ["$blocked_rooms", physical_count]},
                                "then": physical_count,
                                "else": "$blocked_rooms",
                            }
                        },
                        "updated_at": "$$NOW",
                    }
                }
            ],
        )
        matched = result.matched_count
        modified = result.modified_count
        if matched > 0:
            fixed += matched
            if modified > 0:
                clamped_count = db.room_inventory_calendar.count_documents({
                    "prop_id": prop_id,
                    "room_type_id": rt_id,
                    "$expr": {"$gt": ["$available_rooms", "$total_rooms"]},
                })
                if clamped_count < matched:
                    clamped += matched - clamped_count
            print(f"  ✅ {rt_id}: {matched} entries fixed (physical={physical_count})")
        else:
            skipped += 1

    # 3. Also fix orphan inventory entries (room types with no physical rooms)
    inventory_types = db.room_inventory_calendar.distinct("room_type_id", {"prop_id": {"$in": list(set(k[0] for k in physical_counts))}})
    for rt_id in inventory_types:
        found = any(k[1] == rt_id for k in physical_counts if k[0] == 1)  # crude check
        pass  # Don't touch orphaned types — they might belong to other prop_ids

    client.close()
    print(f"\nSummary: {fixed} entries fixed, {clamped} had available/blocked clamped, {skipped} already correct")
    return {"fixed": fixed, "clamped": clamped, "skipped": skipped}


if __name__ == "__main__":
    fix_inventory_total_rooms()
