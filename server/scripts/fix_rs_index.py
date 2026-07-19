"""Fix room_status_log unique index: hotel_room_id -> room_label."""
import os
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

print("=== Current indexes on room_status_log ===")
for idx in db.room_status_log.list_indexes():
    print(f"  name={idx['name']} key={idx['key']}")

# Check what the current idx_rs_prop_room looks like
idx = next((i for i in db.room_status_log.list_indexes() if i['name'] == 'idx_rs_prop_room'), None)
if idx:
    keys = list(idx['key'].keys())
    print(f"\nCurrent idx_rs_prop_room keys: {keys}")
    if 'hotel_room_id' in keys:
        print("FIX: dropping idx_rs_prop_room (uses hotel_room_id) and recreating with room_label...")
        db.room_status_log.drop_index('idx_rs_prop_room')
        db.room_status_log.create_index(
            [("prop_id", 1), ("room_label", 1)],
            name="idx_rs_prop_room",
            unique=True
        )
        print("Done.")
    elif 'room_label' in keys:
        print("Already correct (uses room_label). No change needed.")
else:
    print("\nidx_rs_prop_room not found, creating with (prop_id, room_label)...")
    db.room_status_log.create_index(
        [("prop_id", 1), ("room_label", 1)],
        name="idx_rs_prop_room",
        unique=True
    )
    print("Done.")

print("\n=== After fix ===")
for idx in db.room_status_log.list_indexes():
    print(f"  name={idx['name']} key={idx['key']}")

c.close()
