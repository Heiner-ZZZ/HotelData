"""Quick inventory seed — queries room types dynamically per hotel."""
from datetime import datetime, timedelta, timezone

from src.database.connection import get_database

db = get_database()
today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
now = datetime.now(timezone.utc).isoformat()

prop_ids = db.fact_hotel_reservations.distinct("prop_id")[:10]
if not prop_ids:
    prop_ids = list(range(1, 11))

count = 0
for pid in prop_ids:
    room_types = list(db.room_types.find({"prop_id": pid}, {"_id": 0, "room_type_id": 1}))
    if not room_types:
        print(f"  Hotel {pid}: no room types, skipping")
        continue
    for rt in room_types:
        rid = rt["room_type_id"]
        total = rt.get("inventory_total") or 10
        for day_offset in range(120):
            d = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            avail = max(total - (day_offset % 3), 0)
            db.room_inventory_calendar.update_one(
                {"prop_id": pid, "room_type_id": rid, "date": d},
                {"$set": {"available_rooms": avail, "total_rooms": total, "updated_at": now},
                 "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            count += 1

total = db.room_inventory_calendar.estimated_document_count()
print(f"Inserted/updated {count} inventory records. Total in collection: {total}")
