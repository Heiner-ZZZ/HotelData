"""Link blackout_dates created by maintenance to hotel_rooms via ObjectId FK.

Idempotent: resolves room_label/room_number against hotel_rooms and sets:
  - room_id       → hotel_rooms._id (ObjectId FK)
  - hotel_room_id → hotel_rooms.hotel_room_id (string, denormalized)
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def migrate() -> None:
    db = get_database()
    collection = db["blackout_dates"]

    query = {
        "source": "maintenance",
        "$or": [
            {"hotel_room_id": {"$exists": False}},
            {"hotel_room_id": ""},
            {"hotel_room_id": None},
            {"room_id": {"$type": "string"}},
        ]
    }

    blackouts = list(collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1, "room_id": 1}))
    updated = 0
    not_found: list[tuple[str, int, str]] = []

    for blk in blackouts:
        bid = blk["_id"]
        prop_id = blk.get("prop_id", 0)
        label = (blk.get("room_label") or "").strip()

        # Build room query — try label first, then existing room_id string
        room_query: dict = {
            "prop_id": prop_id,
            "$or": [],
        }
        if label:
            room_query["$or"].append({"room_label": label})
        existing_room_id = blk.get("room_id")
        if existing_room_id and isinstance(existing_room_id, str) and existing_room_id:
            room_query["$or"].append({"hotel_room_id": existing_room_id})

        if not room_query["$or"]:
            not_found.append((str(bid), prop_id, label))
            continue

        room = db["hotel_rooms"].find_one(
            room_query,
            {"_id": 1, "hotel_room_id": 1, "room_label": 1},
        )

        if not room:
            not_found.append((str(bid), prop_id, label))
            continue

        collection.update_one(
            {"_id": bid},
            {"$set": {
                "room_id": room["_id"],
                "hotel_room_id": room["hotel_room_id"],
                "room_label": room.get("room_label") or label,
            }},
        )
        updated += 1

    print(f"Migrated {updated}/{len(blackouts)} maintenance blackout_dates to room_id.")
    if not_found:
        print(f"Could not resolve {len(not_found)} blackouts:")
        for bid, prop_id, label in not_found:
            print(f"  - blackout {bid} (prop_id={prop_id}, label={label!r})")


if __name__ == "__main__":
    migrate()
