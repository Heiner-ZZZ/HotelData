"""Link existing housekeeping_tasks to hotel_rooms via hotel_room_id.

This script is idempotent: it only updates tasks that don't yet have a
room_id or that have an empty one. It denormalizes room_label, room_number
and room_type_id from the matched hotel_room.
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

    query = {
        "$or": [
            {"room_id": {"$exists": False}},
            {"room_id": ""},
            {"room_id": None},
        ]
    }

    tasks = list(collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1, "room_number": 1}))
    updated = 0
    not_found: list[tuple[str, int, str]] = []

    for task in tasks:
        task_id = task["_id"]
        prop_id = task.get("prop_id")
        label = task.get("room_label") or task.get("room_number") or ""

        if not prop_id or not label:
            not_found.append((str(task_id), prop_id or 0, label))
            continue

        room = db["hotel_rooms"].find_one(
            {
                "prop_id": prop_id,
                "$or": [
                    {"room_label": label},
                    {"room_number": label},
                ],
            },
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1, "room_type_id": 1},
        )

        if not room:
            not_found.append((str(task_id), prop_id, label))
            continue

        collection.update_one(
            {"_id": task_id},
            {"$set": {
                "room_id": room["hotel_room_id"],
                "room_label": room.get("room_label") or room.get("room_number") or label,
                "room_number": room.get("room_number", ""),
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
