"""Diagnose inventory data issues for prop_id=1."""
import sys
sys.path.insert(0, "/app")
from src.database.connection import get_database

db = get_database()
prop_id = 1

print("=== HOTEL ROOMS ===")
rooms = list(db.hotel_rooms.find({"prop_id": prop_id}, {"_id": 0}).sort("room_label", 1))
for r in rooms:
    print(f"  room#{r.get('room_label','')}  type_id={r.get('room_type_id','')}  type_name={r.get('room_type_name','')}")

print()
print("=== ROOM TYPES ===")
types = list(db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1}).sort("room_type_id", 1))
for t in types:
    count = db.hotel_rooms.count_documents({"prop_id": prop_id, "room_type_id": t["room_type_id"]})
    print(f"  {t['room_type_id']:>20}  name={t.get('name','')}  physical_rooms={count}")

print()
print("=== INVENTORY SUMMARY (per room_type_id) ===")
pipeline = [
    {"$match": {"prop_id": prop_id}},
    {"$group": {
        "_id": {"room_type_id": "$room_type_id", "room_type_name": "$room_type_name"},
        "records": {"$sum": 1},
        "max_total": {"$max": "$total_rooms"},
        "min_total": {"$min": "$total_rooms"},
        "sample_dates": {"$push": {"date": "$date", "total": "$total_rooms"}},
    }},
    {"$sort": {"_id.room_type_id": 1}},
]
for g in db.room_inventory_calendar.aggregate(pipeline):
    sample = g["sample_dates"][:3]
    print(f"  {g['_id']['room_type_id']:>20}  name='{g['_id']['room_type_name']}'  records={g['records']}  total_range={g['min_total']}-{g['max_total']}")
    for s in sample:
        print(f"      {s['date']} total={s['total']}")

print()
print("=== INVENTORY ROWS WITH WRONG TOTAL (not 2 or not default) ===")
bad = list(db.room_inventory_calendar.find(
    {"prop_id": prop_id, "total_rooms": {"$ne": 2}},
    {"_id": 0, "date": 1, "room_type_id": 1, "room_type_name": 1, "total_rooms": 1, "available_rooms": 1}
).sort([("date", 1), ("room_type_id", 1)]).limit(20))
for r in bad:
    print(f"  {r['date']:>12}  {r.get('room_type_id',''):>20}  total={r['total_rooms']}  disp={r.get('available_rooms','?')}")
if not bad:
    print("  ✅ All records have total_rooms=2")
