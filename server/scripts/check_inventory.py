"""
Check room_inventory_calendar for prop_id=1 to understand available_rooms vs total_rooms.
"""
import sys
sys.path.insert(0, '/app')
from src.database.connection import get_database

db = get_database()

# Check room_inventory_calendar for prop_id=1
print("=== room_inventory_calendar (prop_id=1) ===")
data = list(db.room_inventory_calendar.find(
    {"prop_id": 1},
    {"_id": 0, "date": 1, "room_type_id": 1, "available_rooms": 1, "total_rooms": 1, "blocked_rooms": 1}
).sort([("date", 1), ("room_type_id", 1)]).limit(30))

for d in data:
    print(f'{d["date"]:>12}  type={str(d.get("room_type_id","")):>30}  avail={str(d.get("available_rooms","")):>4}  total={str(d.get("total_rooms","")):>4}  blocked={str(d.get("blocked_rooms","")):>4}')

# Check room types for prop_id=1
print("\n=== room_types (prop_id=1) ===")
types = list(db.room_types.find(
    {"prop_id": 1},
    {"_id": 0, "room_type_id": 1, "name": 1, "max_adults": 1, "base_capacity": 1}
))
for t in types:
    print(f'{t.get("room_type_id",""):>30}  name={t.get("name",""):>25}  adults={t.get("max_adults",""):>2}  cap={t.get("base_capacity",""):>2}')

# Check hotel_rooms for prop_id=1
print("\n=== hotel_rooms (prop_id=1) ===")
rooms = list(db.hotel_rooms.find(
    {"prop_id": 1},
    {"_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1, "room_type_id": 1, "room_type_name": 1}
).sort("room_number", 1))
for r in rooms:
    print(f'{r.get("hotel_room_id",""):>30}  N.{r.get("room_number",""):>4}  label={r.get("room_label",""):>20}  type_id={str(r.get("room_type_id","")):>30}  type_name={r.get("room_type_name","")}')
