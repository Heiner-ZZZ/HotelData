"""Bulk fix: enrich room_type_name for all hotels + add floor to housekeeping."""
import os
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

prop_ids = db.hotel_rooms.distinct("prop_id")
print(f"Processing hotels: {sorted(prop_ids)}\n")

total_fixed_types = 0
total_fixed_hk = 0

for pid in sorted(prop_ids):
    if pid == 1:
        continue  # Already cleaned
    
    # Build room_type lookup
    rtypes = list(db.room_types.find({"prop_id": pid}, {"room_type_id": 1, "name": 1}))
    type_map = {rt['room_type_id']: rt['name'] for rt in rtypes if rt.get('room_type_id')}
    
    if not type_map:
        print(f"  prop_id={pid}: NO room_types found, skipping")
        continue
    
    # Fix hotel_rooms
    rooms = list(db.hotel_rooms.find({"prop_id": pid}))
    fixed = 0
    for room in rooms:
        tid = room.get('room_type_id', '')
        current = room.get('room_type_name', '') or ''
        if tid in type_map and current != type_map[tid]:
            db.hotel_rooms.update_one(
                {"hotel_room_id": room['hotel_room_id']},
                {"$set": {"room_type_name": type_map[tid]}}
            )
            fixed += 1
    
    # Fix housekeeping floor
    hk_fixed = db.housekeeping_tasks.update_many(
        {"prop_id": pid, "$or": [{"floor": {"$exists": False}}, {"floor": None}, {"floor": 0}]},
        {"$set": {"floor": 1}}
    ).modified_count
    
    print(f"  prop_id={pid}: {fixed}/{len(rooms)} rooms enriched, {hk_fixed} HK tasks fixed")
    total_fixed_types += fixed
    total_fixed_hk += hk_fixed

print(f"\nTotal: {total_fixed_types} room_type_names fixed, {total_fixed_hk} HK tasks fixed")
c.close()
