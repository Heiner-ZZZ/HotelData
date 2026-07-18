"""Fix inventory data for prop_id=1:
- Recalculate total_rooms from actual physical hotel_rooms count per room_type_id
- Remove records for virtual room types that have 0 physical rooms
- Fill missing room_type_name from room_types collection
"""
import sys
sys.path.insert(0, "/app")
from src.database.connection import get_database

db = get_database()
prop_id = 1

# 1. Get physical room counts per room_type_id
room_counts = {}
room_type_names = {}
rooms = list(db.hotel_rooms.find({"prop_id": prop_id}, {
    "_id": 0, "room_type_id": 1, "room_type_name": 1
}))
for r in rooms:
    rtid = r.get("room_type_id", "")
    if rtid:
        room_counts[rtid] = room_counts.get(rtid, 0) + 1
        if r.get("room_type_name"):
            room_type_names[rtid] = r["room_type_name"]

# 2. Also get names from room_types collection
type_docs = list(db.room_types.find({"prop_id": prop_id}, {
    "_id": 0, "room_type_id": 1, "name": 1
}))
for t in type_docs:
    rtid = t.get("room_type_id", "")
    if rtid and t.get("name") and rtid not in room_type_names:
        room_type_names[rtid] = t["name"]

print("=== Physical room counts per room_type_id ===")
for rtid, count in sorted(room_counts.items()):
    name = room_type_names.get(rtid, "(sin nombre)")
    print(f"  {rtid:>35}  count={count}  name='{name}'")

# 3. Get all distinct room_type_ids in inventory
inv_types = db.room_inventory_calendar.distinct("room_type_id", {"prop_id": prop_id})
print(f"\n=== Room types in inventory ({len(inv_types)}) ===")

updated = 0
removed = 0
filled_name = 0

for rtid in inv_types:
    physical_count = room_counts.get(rtid, 0)
    name = room_type_names.get(rtid, "")

    if physical_count == 0:
        # This is a virtual room type — remove its inventory records
        result = db.room_inventory_calendar.delete_many({"prop_id": prop_id, "room_type_id": rtid})
        removed += result.deleted_count
        print(f"  🗑️  {rtid:>35}  DELETED {result.deleted_count} records (0 physical rooms)")
    else:
        # Update total_rooms for all records of this type
        result = db.room_inventory_calendar.update_many(
            {"prop_id": prop_id, "room_type_id": rtid},
            {"$set": {"total_rooms": physical_count}}
        )
        updated += result.modified_count
        print(f"  ✅ {rtid:>35}  total_rooms={physical_count}  updated={result.modified_count} records")

        # Fill room_type_name if missing
        if name:
            result2 = db.room_inventory_calendar.update_many(
                {"prop_id": prop_id, "room_type_id": rtid,
                 "$or": [{"room_type_name": {"$exists": False}}, {"room_type_name": ""}]},
                {"$set": {"room_type_name": name}}
            )
            filled_name += result2.modified_count

print("\n=== Summary ===")
print(f"  Updated total_rooms: {updated} records")
print(f"  Deleted (virtual types): {removed} records")
print(f"  Filled missing room_type_name: {filled_name} records")

# 4. Verify final state
remaining = db.room_inventory_calendar.count_documents({"prop_id": prop_id})
print(f"  Remaining inventory records: {remaining}")

print("\n=== Final inventory by room_type_id ===")
pipeline = [
    {"$match": {"prop_id": prop_id}},
    {"$group": {
        "_id": {"room_type_id": "$room_type_id", "room_type_name": "$room_type_name"},
        "records": {"$sum": 1},
        "max_total": {"$max": "$total_rooms"},
        "min_total": {"$min": "$total_rooms"},
    }},
    {"$sort": {"_id.room_type_id": 1}},
]
for g in db.room_inventory_calendar.aggregate(pipeline):
    print(f"  {g['_id']['room_type_id']:>35}  name='{g['_id']['room_type_name']}'  records={g['records']}  total={g['min_total']}-{g['max_total']}")
