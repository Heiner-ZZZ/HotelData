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
    room_map = {r["hotel_room_id"]: r for r in rooms}
    
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
    
    # Housekeeping checks (FK-based via room_id)
    hk_missing_room_id = db.housekeeping_tasks.count_documents(
        {"prop_id": pid, "$or": [{"room_id": {"$exists": False}}, {"room_id": None}, {"room_id": ""}]}
    )
    if hk_missing_room_id > 0:
        print(f"    ⚠️  housekeeping: {hk_missing_room_id} tareas sin room_id")

    # Housekeeping tasks where denormalized room_label doesn't match linked hotel_room
    hk_bad_label = 0
    for t in db.housekeeping_tasks.find({"prop_id": pid, "room_id": {"$exists": True, "$ne": ""}}):
        room_id = t.get("room_id")
        linked = room_map.get(room_id)
        if not linked:
            continue
        expected = str(linked.get("room_label", "") or linked.get("room_number", ""))
        actual = str(t.get("room_label", ""))
        if expected and actual and expected != actual:
            hk_bad_label += 1
    if hk_bad_label > 0:
        print(f"    ⚠️  housekeeping: {hk_bad_label} tareas con room_label desactualizado")

    print()

print(f"=== RESUMEN ===")
print(f"Total hoteles: {len(prop_ids)}")
print(f"Total rooms: {total_rooms}")
print(f"Total rooms con problemas: {total_issues}")
c.close()
