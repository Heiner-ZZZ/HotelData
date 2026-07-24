"""
[DEPRECATED] Fix room_label in hotel_rooms collection for prop_id=1.

Previously combined room_number + room_type_name (e.g., "Habitacion 110 - Standard").
room_number was $unset from hotel_rooms — this script is no longer effective
since it reads room_label as input to produce room_label.

Kept for reference. Use fix_room_labels_v2.py or cleanup_housekeeping.py instead.
"""
import sys
sys.path.insert(0, '/app')

from src.database.connection import get_database

db = get_database()
rooms = list(db.hotel_rooms.find(
    {"prop_id": 1},
    {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_name": 1}
).sort("room_label", 1))

print(f"Found {len(rooms)} rooms for prop_id=1\n")

updated = 0
for r in rooms:
    old_label = r.get("room_label", "")
    room_num = r.get("room_label", "")
    type_name = r.get("room_type_name", "")
    
    # Build a meaningful label: "Habitación {number} - {room_type}"
    if room_num and type_name:
        new_label = f"Habitación {room_num} - {type_name}"
    elif room_num:
        new_label = f"Habitación {room_num}"
    elif type_name:
        new_label = f"Habitación - {type_name}"
    else:
        new_label = r.get("hotel_room_id", "Habitación")
    
    if old_label != new_label:
        db.hotel_rooms.update_one(
            {"_id": r["_id"]},
            {"$set": {"room_label": new_label}}
        )
        print(f"  {r['hotel_room_id']:>30}")
        print(f"    before: {old_label}")
        print(f"    after:  {new_label}")
        updated += 1

print(f"\nUpdated {updated} room(s)")
