"""Audit all hotels for room_label anomalies (type names instead of numbers)."""
import os
from collections import Counter
from pymongo import MongoClient

uri = os.environ.get('MONGO_URI', 'mongodb://mongo:27017')
db_name = os.environ.get('MONGO_DATABASE', 'hoteldata_hub')
c = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = c[db_name]

# Get all prop_ids
prop_ids = db.hotel_rooms.distinct("prop_id")
print(f"Hotels found: {sorted(prop_ids)}\n")

total_issues = 0
total_rooms = 0

for pid in sorted(prop_ids):
    rooms = list(db.hotel_rooms.find({"prop_id": pid}, {
        "_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1,
        "floor": 1, "room_type_name": 1
    }))
    total_rooms += len(rooms)
    
    # Get room type names for this hotel
    rtypes = list(db.room_types.find({"prop_id": pid}, {"name": 1}))
    type_names = {rt['name'] for rt in rtypes}
    
    issues = []
    for r in rooms:
        label = str(r.get('room_label', ''))
        rn = str(r.get('room_number', ''))
        floor = r.get('floor')
        type_name = r.get('room_type_name', '')
        
        problems = []
        # Label is a room type name (not a number)
        if label and not label.isdigit():
            problems.append(f"label='{label}' (no es número)")
        # Label doesn't match room_number
        if label and rn and label.isdigit() and label != rn:
            problems.append(f"label={label} != room_number={rn}")
        # Missing or empty room_type_name
        if not type_name or type_name == '?':
            problems.append(f"type_name vacío")
        # Floor is 0 or None
        if floor is None or floor == 0:
            problems.append(f"floor={floor}")
        
        if problems:
            issues.append((r['hotel_room_id'], problems))
    
    if issues:
        total_issues += len(issues)
        print(f"❌ prop_id={pid} — {len(issues)}/{len(rooms)} rooms con problemas:")
        for rid, probs in issues:
            print(f"    {rid}: {', '.join(probs)}")
    else:
        print(f"✅ prop_id={pid} — {len(rooms)} rooms OK")
    
    # Housekeeping check
    hk_missing_floor = db.housekeeping_tasks.count_documents(
        {"prop_id": pid, "$or": [{"floor": {"$exists": False}}, {"floor": None}, {"floor": 0}]}
    )
    if hk_missing_floor > 0:
        print(f"    ⚠️  housekeeping: {hk_missing_floor} tareas sin floor")
    
    # Housekeeping rooms with label matching a type name
    if type_names:
        hk_bad = list(db.housekeeping_tasks.find({
            "prop_id": pid, "room_label": {"$in": list(type_names)}
        }, {"_id": 0, "room_label": 1, "floor": 1}))
        if hk_bad:
            print(f"    ⚠️  housekeeping: {len(hk_bad)} tareas con room_label=nombre de tipo: {[h['room_label'] for h in hk_bad]}")

    print()

print(f"=== RESUMEN ===")
print(f"Total hoteles: {len(prop_ids)}")
print(f"Total rooms: {total_rooms}")
print(f"Total rooms con problemas: {total_issues}")
c.close()
