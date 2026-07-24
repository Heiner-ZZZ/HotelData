"""Link existing housekeeping_tasks to hotel_rooms via ObjectId FK.

Idempotent: resolves room_label/room_number against hotel_rooms and sets:
  - room_id       → hotel_rooms._id (ObjectId FK)
  - hotel_room_id → hotel_rooms.hotel_room_id (string, denormalized)
  - room_label, room_number, room_type_id (denormalized)
"""
from __future__ import annotations

import sys
import os

# Make src imports available when running inside Docker or from server/scripts
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def migrate() -> None:
    db = get_database()
    collection = db["housekeeping_tasks"]

    # Catch docs missing hotel_room_id (regardless of room_id content)
    query = {
        "$or": [
            {"hotel_room_id": {"$exists": False}},
            {"hotel_room_id": ""},
            {"hotel_room_id": None},
            {"room_id": {"$type": "string"}},
        ]
    }

    tasks = list(collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1, "room_id": 1}))
    updated = 0
    not_found: list[tuple[str, int, str]] = []

    for task in tasks:
        task_id = task["_id"]
        prop_id = task.get("prop_id")
        label = task.get("room_label") or ""

        # Build room query — try label first, then existing room_id string
        room_query: dict = {"prop_id": prop_id, "$or": []}
        if label:
            room_query["$or"].append({"room_label": label})
        existing_room_id = task.get("room_id")
        if existing_room_id and isinstance(existing_room_id, str) and existing_room_id:
            room_query["$or"].append({"hotel_room_id": existing_room_id})

        if not prop_id or not room_query["$or"]:
            not_found.append((str(task_id), prop_id or 0, label))
            continue

        room = db["hotel_rooms"].find_one(
            room_query,
            {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1},
        )

        if not room:
            not_found.append((str(task_id), prop_id, label))
            continue

        collection.update_one(
            {"_id": task_id},
            {"$set": {
                "room_id": room["_id"],
                "hotel_room_id": room["hotel_room_id"],
                "room_label": room.get("room_label") or label,
                "room_type_id": room.get("room_type_id", ""),
            }},
        )
        updated += 1

    print(f"Migrated {updated}/{len(tasks)} housekeeping_tasks to room_id.")
    if not_found:
        print(f"Could not resolve {len(not_found)} tasks:")
        for task_id, prop_id, label in not_found:
            print(f"  - task {task_id} (prop_id={prop_id}, label={label})")


if __name__ == "__main__":
    migrate()
