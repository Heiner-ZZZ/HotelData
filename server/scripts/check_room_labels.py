import sys
sys.path.insert(0, '/app')
from src.database.connection import get_database

db = get_database()
rooms = list(db.hotel_rooms.find(
    {"prop_id": 1},
    {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_type_name": 1}
).sort("room_label", 1).limit(15))

for r in rooms:
    print(f"{r.get('hotel_room_id',''):>30}  label={r.get('room_label','')}  type={r.get('room_type_name','')}")

total = db.hotel_rooms.count_documents({"prop_id": 1})
print(f"\nTotal rooms for prop_id=1: {total}")
