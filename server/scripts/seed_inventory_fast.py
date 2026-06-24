"""Quick inventory seed without index creation."""
from datetime import datetime, timedelta, timezone

from src.database.connection import get_database

db = get_database()
today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
now = datetime.now(timezone.utc).isoformat()

prop_ids = db.fact_hotel_reservations.distinct("prop_id")[:10]
if not prop_ids:
    prop_ids = list(range(1, 11))

room_types = [
    {"room_type_id": "standard", "total": 15},
    {"room_type_id": "deluxe", "total": 10},
    {"room_type_id": "suite", "total": 5},
]

count = 0
for pid in prop_ids:
    for rt in room_types:
        for day_offset in range(120):
            d = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            available = max(rt["total"] - (day_offset % 3), 0)
            db.room_inventory_calendar.update_one(
                {"prop_id": pid, "room_type_id": rt["room_type_id"], "date": d},
                {"$set": {"available_rooms": available, "total_rooms": rt["total"], "updated_at": now},
                 "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            count += 1

total = db.room_inventory_calendar.count_documents({})
print(f"Inserted/updated {count} inventory records. Total in collection: {total}")
