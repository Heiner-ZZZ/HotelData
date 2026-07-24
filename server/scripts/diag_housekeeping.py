"""Diagnose housekeeping data for hotel GTA7 (prop_id=1)."""
import os
from collections import Counter
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

print("=== HOTEL_ROOMS for prop_id=1 ===")
rooms = list(db.hotel_rooms.find({"prop_id": 1}, {
    "_id": 0, "hotel_room_id": 1, "room_label": 1,
    "floor": 1, "room_type_name": 1, "room_type_id": 1, "status": 1
}))
for r in rooms:
    print(f"  room_label={r.get('room_label','?')} | floor={r.get('floor')} | type={r.get('room_type_name','?')} | id={r.get('hotel_room_id','?')} | status={r.get('status')}")

print(f"\nTotal hotel_rooms: {len(rooms)}")

print("\n=== ROOM_TYPES for prop_id=1 ===")
rtypes = list(db.room_types.find({"prop_id": 1}, {
    "_id": 0, "room_type_id": 1, "name": 1, "base_capacity": 1, "hotel_room_ids": 1
}))
for rt in rtypes:
    print(f"  name={rt.get('name','?')} | id={rt.get('room_type_id','?')} | capacity={rt.get('base_capacity')} | room_ids={rt.get('hotel_room_ids')}")

print(f"\nTotal room_types: {len(rtypes)}")

# Check housekeeping collection
print("\n=== HOUSEKEEPING ===")
hk_collections = [c for c in db.list_collection_names() if 'housekeep' in c.lower()]
print(f"HK collections found: {hk_collections}")
for hk_col in hk_collections:
    hk_data = list(db[hk_col].find({"prop_id": 1}).limit(50))
    print(f"\n  Collection '{hk_col}' — {len(hk_data)} docs (limit 50):")
    for hk in hk_data[:35]:
        rid = hk.get('room_id') or hk.get('hotel_room_id') or hk.get('room_label') or hk.get('_id', '?')
        floor = hk.get('floor', '?')
        status = hk.get('status') or hk.get('state') or '?'
        label = hk.get('room_label') or hk.get('label') or ''
        prop = hk.get('prop_id', '?')
        print(f"    id={rid} | floor={floor} | status={status} | label={label} | prop={prop}")
    # Show all fields for first doc to understand schema
    if hk_data:
        print(f"\n  Full keys of first doc: {list(hk_data[0].keys())}")

# Check for anomalies
print("\n=== ANOMALIES ===")

# Missing room_id in housekeeping collections
for hk_col in hk_collections:
    missing_room_id = db[hk_col].count_documents({
        "prop_id": 1,
        "$or": [
            {"room_id": {"$exists": False}},
            {"room_id": None},
            {"room_id": ""}
        ]
    })
    if missing_room_id:
        print(f"  WARNING: '{hk_col}' has {missing_room_id} docs missing room_id")

room_type_names = [rt['name'] for rt in rtypes]
print(f"Room type names: {room_type_names}")
for r in rooms:
    rn = r.get('room_label', '')
    if rn in room_type_names:
        print(f"  WARNING: room_label '{rn}' matches room_type name! Room id={r.get('hotel_room_id')}")

room_labels = [r.get('room_label', '') for r in rooms]
dupes = {k: v for k, v in Counter(room_labels).items() if v > 1}
if dupes:
    print(f"  DUPLICATE room_labels in hotel_rooms: {dupes}")
else:
    print("  No duplicate room_labels in hotel_rooms.")

for r in rooms:
    rn = str(r.get('room_label', ''))
    if 'HR-' in rn or 'hr-' in rn.lower():
        print(f"  HR- anomaly: id={r.get('hotel_room_id')} room_label={rn}")

# Check if any housekeeping entries reference non-existent rooms
if hk_collections:
    valid_room_ids = {r['hotel_room_id'] for r in rooms}
    for hk_col in hk_collections:
        for hk in db[hk_col].find({"prop_id": 1}):
            hk_room_id = hk.get('hotel_room_id') or hk.get('room_id')
            if hk_room_id and hk_room_id not in valid_room_ids:
                print(f"  ORPHAN HK: '{hk_col}' doc references room_id={hk_room_id} which is NOT in hotel_rooms!")

c.close()
print("\nDone.")
