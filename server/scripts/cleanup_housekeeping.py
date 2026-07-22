"""Clean up housekeeping data inconsistencies for prop_id=1 (GTA7)."""
import os
from typing import Any

from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

print("=== CLEANUP START ===")

# 1. Build room_type lookup (name + capacity) for enrichment
rtypes = list(db.room_types.find({"prop_id": 1}, {"room_type_id": 1, "name": 1, "base_capacity": 1}))
type_map = {rt['room_type_id']: rt for rt in rtypes}
print(f"Room type map: {list(type_map.keys())}")

# 2. Fix hotel_rooms for prop_id=1
rooms = list(db.hotel_rooms.find({"prop_id": 1}))
fixed_labels = 0
fixed_types = 0
fixed_floors = 0

for room in rooms:
    rid = room['hotel_room_id']
    updates = {}
    
    # Fix room_label: if it looks like a room type name instead of a number
    label = room.get('room_label', '')
    room_num = room.get('room_number', '')
    
    # If label is a room type name (not a number), fix it to the room_number
    if label and not str(label).isdigit():
        if str(room_num).isdigit():
            updates['room_label'] = str(room_num)
            print(f"  FIX label: {rid} label '{label}' -> '{room_num}'")
            fixed_labels += 1
    
    # Enrich room_type_name from room_types
    type_id = room.get('room_type_id', '')
    if type_id and type_id in type_map:
        type_name = type_map[type_id]['name']
        current_type_name = room.get('room_type_name', '')
        if current_type_name != type_name:
            updates['room_type_name'] = type_name
            print(f"  FIX type_name: {rid} '{current_type_name}' -> '{type_name}'")
            fixed_types += 1
    
    # Ensure floor is populated
    floor = room.get('floor')
    if floor is None or floor == '' or floor == 0:
        updates['floor'] = 1
        print(f"  FIX floor: {rid} -> 1")
        fixed_floors += 1
    
    if updates:
        db.hotel_rooms.update_one({"hotel_room_id": rid}, {"$set": updates})

print(f"\nFixed labels: {fixed_labels}")
print(f"Fixed type_names: {fixed_types}")
print(f"Fixed floors: {fixed_floors}")

# 3. Add floor to housekeeping_tasks for prop_id=1
hk_result = db.housekeeping_tasks.update_many(
    {"prop_id": 1, "floor": {"$exists": False}},
    {"$set": {"floor": 1}}
)
print(f"\nHousekeeping tasks with floor added: {hk_result.modified_count}")

# Also fix housekeeping_tasks with floor = 0 or empty
hk_result2 = db.housekeeping_tasks.update_many(
    {"prop_id": 1, "floor": {"$in": [0, "", None]}},
    {"$set": {"floor": 1}}
)
print(f"Housekeeping tasks with floor fixed (was 0/empty): {hk_result2.modified_count}")

# 3b. Backfill room_id and sync denormalized room_label/type in housekeeping_tasks
print("\n=== Sync housekeeping_tasks room_id/room_label ===")
rooms_for_hk = list(db.hotel_rooms.find({"prop_id": 1}, {
    "_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1,
    "room_type_id": 1, "room_type_name": 1
}))
room_by_id = {r["hotel_room_id"]: r for r in rooms_for_hk}
room_by_label: dict[str, Any] = {}
for r in rooms_for_hk:
    label = str(r.get("room_label", "") or r.get("room_number", ""))
    if label:
        room_by_label[label] = r

hk_fk_updates = 0
hk_label_updates = 0
for t in db.housekeeping_tasks.find({"prop_id": 1}):
    room = None
    if t.get("room_id"):
        room = room_by_id.get(t["room_id"])
    if room is None and t.get("room_label"):
        room = room_by_label.get(str(t["room_label"]))
    if not room:
        continue
    updates: dict[str, Any] = {}
    if t.get("room_id") != room["hotel_room_id"]:
        updates["room_id"] = room["hotel_room_id"]
        updates["room_type_id"] = room.get("room_type_id")
        updates["room_type_name"] = room.get("room_type_name")
        hk_fk_updates += 1
    expected_label = str(room.get("room_label", "") or room.get("room_number", ""))
    if expected_label and str(t.get("room_label", "")) != expected_label:
        updates["room_label"] = expected_label
        hk_label_updates += 1
    if updates:
        db.housekeeping_tasks.update_one({"_id": t["_id"]}, {"$set": updates})

print(f"Housekeeping tasks room_id backfilled: {hk_fk_updates}")
print(f"Housekeeping tasks room_label synced: {hk_label_updates}")

# 4. VERIFICATION
print("\n=== POST-CLEANUP VERIFICATION ===")
rooms_after = list(db.hotel_rooms.find({"prop_id": 1}, {
    "_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1,
    "floor": 1, "room_type_name": 1
}))
for r in rooms_after:
    print(f"  {r['hotel_room_id']} | num={r.get('room_number')} | label={r.get('room_label')} | floor={r.get('floor')} | type={r.get('room_type_name')}")

hk_after = list(db.housekeeping_tasks.find({"prop_id": 1}, {
    "_id": 0, "room_id": 1, "room_label": 1, "floor": 1, "status": 1
}))
print(f"\nHousekeeping tasks after cleanup ({len(hk_after)} docs):")
for hk in hk_after:
    print(f"  id={hk.get('room_id')} | label={hk.get('room_label')} | floor={hk.get('floor')} | status={hk.get('status')}")

c.close()
print("\n=== CLEANUP COMPLETE ===")
