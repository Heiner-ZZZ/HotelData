"""
Fix room_label in hotel_rooms to use just the room number.
Also sync room_status_log to match.
"""
import sys
sys.path.insert(0, '/app')
from src.database.connection import get_database

db = get_database()
updated = 0

# 1. Update hotel_rooms
rooms = list(db.hotel_rooms.find({"prop_id": 1}, {"_id": 1, "hotel_room_id": 1, "room_number": 1, "room_label": 1}))
for r in rooms:
    room_num = str(r.get("room_number", ""))
    if not room_num:
        continue
    old_label = r.get("room_label", "")
    if old_label != room_num:
        db.hotel_rooms.update_one({"_id": r["_id"]}, {"$set": {"room_label": room_num}})
        print(f"  hotel_rooms: {r['hotel_room_id']}  {old_label:>30} → {room_num}")
        updated += 1

# 2. Sync room_status_log to use same labels
status_logs = list(db.room_status_log.find({"prop_id": 1}, {"_id": 1, "room_label": 1, "room_number": 1}))
for s in status_logs:
    room_num = str(s.get("room_number", ""))
    old_label = s.get("room_label", "")
    if room_num and old_label != room_num:
        db.room_status_log.update_one({"_id": s["_id"]}, {"$set": {"room_label": room_num}})
        print(f"  room_status_log: {old_label:>30} → {room_num}")

# 3. Update housekeeping tasks that reference the old labels
tasks = list(db.housekeeping_tasks.find({"prop_id": 1}, {"_id": 1, "room_label": 1}))
for t in tasks:
    old = t.get("room_label", "")
    # If the label starts with "Habitación " or "door_front ", extract the number
    import re
    m = re.search(r'(\d+)$', old)
    if m:
        new_label = m.group(1)
        if old != new_label:
            db.housekeeping_tasks.update_one({"_id": t["_id"]}, {"$set": {"room_label": new_label}})
            print(f"  housekeeping_task: {old:>30} → {new_label}")

print(f"\nDone. Updated {updated} hotel_rooms.")
