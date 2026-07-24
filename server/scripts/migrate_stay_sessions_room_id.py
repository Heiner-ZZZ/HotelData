"""Link existing stay_sessions to hotel_rooms via hotel_room_id.

This script is idempotent: it only updates sessions that don't yet have a
room_id or hotel_room_id. It handles two cases:
  1. room_label is a plain number like "110" → resolve via hotel_rooms lookup
  2. room_label is already a hotel_room_id like "HR-1-110" → use directly
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def migrate() -> None:
    db = get_database()
    collection = db["stay_sessions"]

    query = {
        "$or": [
            {"room_id": {"$exists": False}},
            {"room_id": ""},
            {"room_id": None},
            {"hotel_room_id": {"$exists": False}},
            {"hotel_room_id": ""},
            {"hotel_room_id": None},
            {"room_id": {"$type": "string"}},
        ]
    }

    sessions = list(collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1}))
    updated = 0
    not_found: list[tuple[str, int, str]] = []

    for session in sessions:
        sid = session["_id"]
        prop_id = session.get("prop_id", 0)
        label = (session.get("room_label") or "").strip()

        if not label:
            not_found.append((str(sid), prop_id, label))
            continue

        room_id: str | None = None
        room_label: str | None = None

        # Case 1: label is already a hotel_room_id (e.g. "HR-1-110")
        if label.startswith("HR-"):
            room = db["hotel_rooms"].find_one(
                {"hotel_room_id": label},
                {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1},
            )
            if room:
                room_id = room["_id"]
                hotel_room_id_val = room["hotel_room_id"]
                room_label = room.get("room_label") or label
        else:
            # Case 2: plain number → resolve via lookup
            room = db["hotel_rooms"].find_one(
                {
                    "prop_id": prop_id,
                    "room_label": label,
                },
                {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1},
            )
            if room:
                room_id = room["_id"]
                hotel_room_id_val = room["hotel_room_id"]
                room_label = room.get("room_label") or label

        if not room_id:
            not_found.append((str(sid), prop_id, label))
            continue

        collection.update_one(
            {"_id": sid},
            {"$set": {
                "room_id": room_id,
                "hotel_room_id": hotel_room_id_val,
                "room_label": room_label or label,
            }},
        )
        updated += 1

    print(f"Migrated {updated}/{len(sessions)} stay_sessions to room_id.")
    if not_found:
        print(f"Could not resolve {len(not_found)} sessions:")
        for sid, prop_id, label in not_found:
            print(f"  - session {sid} (prop_id={prop_id}, label={label})")


if __name__ == "__main__":
    migrate()
