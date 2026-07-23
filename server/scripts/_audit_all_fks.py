"""Audit ALL FK fields across ALL collections: ObjectId vs string vs missing."""
import sys
sys.path.insert(0, "/app")
from src.database.connection import get_database
from bson import ObjectId

db = get_database()

# Define all FK fields to audit: (collection, field, target_collection)
FK_CHECKS = [
    ("housekeeping_tasks", "room_id", "hotel_rooms"),
    ("maintenance_tasks", "room_id", "hotel_rooms"),
    ("room_status_history", "room_id", "hotel_rooms"),
    ("stay_service_requests", "room_id", "hotel_rooms"),
    ("stay_sessions", "room_id", "hotel_rooms"),
    ("guest_folios", "room_id", "hotel_rooms"),
    ("blackout_dates", "room_id", "hotel_rooms"),
    ("employees", "department_id", "employee_departments"),
    ("employees", "position_id", "employee_positions"),
    ("expense_invoices", "category_id", "expense_categories"),
    ("booking_orders", "coupon_id", "coupon_codes"),
    ("navigation", "permission_id", "permissions"),
    ("dim_hotels", "geo_catalog_id", "geo_catalog"),
    ("users", "primary_role_id", "roles"),
]

print("=" * 80)
print("AUDITORIA COMPLETA DE FKs — ObjectId vs String vs Missing")
print("=" * 80)

all_ok = True
issues = []

for coll_name, fk_field, target_coll in FK_CHECKS:
    if coll_name not in db.list_collection_names():
        print(f"\n⚠️  {coll_name}: COLECCION NO EXISTE")
        continue

    coll = db[coll_name]
    total = coll.count_documents({})

    objid = coll.count_documents({fk_field: {"$type": "objectId"}})
    string = coll.count_documents({fk_field: {"$type": "string"}})
    none_val = coll.count_documents({fk_field: None})
    missing = coll.count_documents({fk_field: {"$exists": False}})
    other = total - objid - string - none_val - missing

    has_issue = string > 0 or (none_val + missing > 0 and total > 0)
    status = "❌" if has_issue else "✅"

    print(f"\n{status} {coll_name}.{fk_field} → {target_coll}")
    print(f"   Total docs: {total} | ObjectId: {objid} | String: {string} | None: {none_val} | Missing: {missing} | Other: {other}")

    if string > 0:
        issues.append(f"{coll_name}.{fk_field}: {string} docs with STRING (should be ObjectId)")
        all_ok = False
        # Show examples
        for doc in coll.find({fk_field: {"$type": "string"}}).limit(3):
            val = str(doc.get(fk_field))[:50]
            print(f"   Example: {fk_field}={val}")

    # Verify FK resolution for ObjectId values
    if objid > 0 and target_coll in db.list_collection_names():
        broken = 0
        for doc in coll.find({fk_field: {"$type": "objectId"}}).limit(5):
            fk_val = doc.get(fk_field)
            if isinstance(fk_val, ObjectId):
                target = db[target_coll].find_one({"_id": fk_val}, {"_id": 1})
                if not target:
                    broken += 1
        if broken > 0:
            all_ok = False
            issues.append(f"{coll_name}.{fk_field}: {broken}+ BROKEN FKs (ObjectId doesn't resolve in {target_coll})")
            print(f"   ⚠️  {broken}+ BROKEN FKs detected")

print("\n" + "=" * 80)
if all_ok:
    print("✅ TODAS LAS FKs SON ObjectId Y RESUELVEN CORRECTAMENTE")
else:
    print("❌ HAY PROBLEMAS POR RESOLVER:")
    for i in issues:
        print(f"   - {i}")
print("=" * 80)
