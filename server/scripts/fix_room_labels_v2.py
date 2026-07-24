"""
[DEPRECATED] Fix room_label in hotel_rooms to use just the room number.
Also sync room_status_log to match.

Previously read room_number to determine the correct numeric label.
Since room_number was $unset from both hotel_rooms and room_status_log,
this script now reads room_label to set room_label — a no-op.

Kept for reference.
"""
import sys
sys.path.insert(0, '/app')
from src.database.connection import get_database

db = get_database()
updated = 0

# 1. Update hotel_rooms
rooms = list(db.hotel_rooms.find({"prop_id": 1}, {"_id": 1, "hotel_room_id": 1, "room_label": 1}))
for r in rooms:
    room_num = str(r.get("room_label", ""))
    if not room_num:
        continue
    old_label = r.get("room_label", "")
    if old_label != room_num:
        db.hotel_rooms.update_one({"_id": r["_id"]}, {"$set": {"room_label": room_num}})
        print(f"  hotel_rooms: {r['hotel_room_id']}  {old_label:>30} → {room_num}")
        updated += 1

# 2. Sync room_status_log to use same labels
status_logs = list(db.room_status_log.find({"prop_id": 1}, {"_id": 1, "room_label": 1}))
for s in status_logs:
    room_num = str(s.get("room_label", ""))
    old_label = s.get("room_label", "")
    if room_num and old_label != room_num:
        db.room_status_log.update_one({"_id": s["_id"]}, {"$set": {"room_label": room_num}})
        print(f"  room_status_log: {old_label:>30} → {room_num}")

# 3. Sync housekeeping_tasks via room_id
rooms = list(db.hotel_rooms.find({"prop_id": 1}, {
    "_id": 1, "hotel_room_id": 1, "room_label": 1,
    "room_type_id": 1, "room_type_name": 1
}))
room_by_id = {r["hotel_room_id"]: r for r in rooms}
room_by_label = {str(r.get("room_label", "")): r for r in rooms if r.get("room_label")}
tasks = list(db.housekeeping_tasks.find({"prop_id": 1}, {"_id": 1, "room_id": 1, "room_label": 1}))
hk_updated = 0
for t in tasks:
    room = None
    if t.get("room_id"):
        room = room_by_id.get(t["room_id"])
    if room is None and t.get("room_label"):
        room = room_by_label.get(str(t["room_label"]))
    if not room:
        continue
    new_label = str(room.get("room_label", ""))
    set_data = {
        "room_id": room["_id"],
        "hotel_room_id": room["hotel_room_id"],
        "room_label": new_label,
        "room_type_id": room.get("room_type_id"),
        "room_type_name": room.get("room_type_name"),
    }
    if t.get("room_id") != room["hotel_room_id"] or t.get("room_label") != new_label:
        db.housekeeping_tasks.update_one({"_id": t["_id"]}, {"$set": set_data})
        hk_updated += 1

print(f"\nDone. Updated {updated} hotel_rooms. Synced {hk_updated} housekeeping_tasks.")
