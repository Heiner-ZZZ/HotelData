"""Quick verification: guest_folios state."""
import sys
sys.path.insert(0, "/app")
from src.database.connection import get_database
from bson import ObjectId

db = get_database()
coll = db.guest_folios

total = coll.count_documents({})
objid = coll.count_documents({"room_id": {"$type": "objectId"}})
string = coll.count_documents({"room_id": {"$type": "string"}})
none_val = coll.count_documents({"room_id": None})
missing = coll.count_documents({"room_id": {"$exists": False}})
with_hrid = coll.count_documents({"hotel_room_id": {"$exists": True, "$ne": "", "$ne": None}})
without_hrid = total - with_hrid

print(f"TOTAL guest_folios: {total}")
print(f"  ObjectId room_id: {objid}")
print(f"  String room_id:   {string}")
print(f"  None room_id:     {none_val}")
print(f"  Missing room_id:  {missing}")
print(f"  With hotel_room_id: {with_hrid}")
print(f"  Without hotel_room_id: {without_hrid}")
print()

for f in coll.find({}).sort("folio_number", 1):
    rid = f.get("room_id")
    rid_type = type(rid).__name__
    fk_ok = ""
    if isinstance(rid, ObjectId):
        room = db.hotel_rooms.find_one({"_id": rid}, {"hotel_room_id": 1})
        fk_ok = "FK->" + room["hotel_room_id"] if room else "BROKEN"
    print(f"  {str(f.get('folio_number','?')):25} | booking={str(f.get('booking_id','?'))[:28]:28} | room_label={str(f.get('room_label','')):6} | hotel_room_id={str(f.get('hotel_room_id','')):10} | room_id_type={rid_type:8} | {fk_ok}")
