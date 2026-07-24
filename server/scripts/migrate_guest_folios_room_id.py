"""Link existing guest_folios to hotel_rooms via ObjectId FK.

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
    collection = db["guest_folios"]

    query = {
        "$or": [
            {"hotel_room_id": {"$exists": False}},
            {"hotel_room_id": ""},
            {"hotel_room_id": None},
            {"room_id": {"$type": "string"}},
        ]
    }

    folios = list(collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1, "room_id": 1, "booking_id": 1}))
    updated = 0
    not_found: list[tuple[str, int, str]] = []

    for folio in folios:
        fid = folio["_id"]
        prop_id = folio.get("prop_id", 0)
        label = (folio.get("room_label") or "").strip()

        # Build room query — try label first, then existing room_id string
        room_query: dict = {
            "prop_id": prop_id,
            "$or": [],
        }
        if label:
            room_query["$or"].extend([
                {"room_label": label},
                {"room_number": label},
            ])
        existing_room_id = folio.get("room_id")
        if existing_room_id and isinstance(existing_room_id, str) and existing_room_id:
            room_query["$or"].append({"hotel_room_id": existing_room_id})

        # Fallback: resolve via booking_orders.assigned_rooms when label is empty
        if not room_query["$or"]:
            booking_id = folio.get("booking_id", "")
            if booking_id:
                booking = db.booking_orders.find_one(
                    {"booking_id": booking_id},
                    {"assigned_rooms": 1},
                )
                assigned = (booking or {}).get("assigned_rooms", []) or []
                for room_str in assigned:
                    if isinstance(room_str, str) and room_str:
                        room_query["$or"].append({"hotel_room_id": room_str})

        if not room_query["$or"]:
            not_found.append((str(fid), prop_id, label))
            continue

        room = db["hotel_rooms"].find_one(
            room_query,
            {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_number": 1, "room_type_id": 1},
        )

        if not room:
            not_found.append((str(fid), prop_id, label))
            continue

        collection.update_one(
            {"_id": fid},
            {"$set": {
                "room_id": room["_id"],
                "hotel_room_id": room["hotel_room_id"],
                "room_label": room.get("room_label") or room.get("room_number") or label,
            }},
        )
        updated += 1

    print(f"Migrated {updated}/{len(folios)} guest_folios to room_id.")
    if not_found:
        print(f"Could not resolve {len(not_found)} folios:")
        for fid, prop_id, label in not_found:
            print(f"  - folio {fid} (prop_id={prop_id}, label={label!r})")


if __name__ == "__main__":
    migrate()
