"""
Recalcular room_inventory_calendar desde las habitaciones físicas reales (hotel_rooms).
"""
import sys
sys.path.insert(0, '/app')
from datetime import datetime, timedelta, timezone
from src.database.connection import get_database

db = get_database()

for prop_id in [1]:
    print(f"\n=== Propiedad {prop_id} ===")
    
    rooms_by_type = list(db.hotel_rooms.aggregate([
        {"$match": {"prop_id": prop_id, "is_active": {"$ne": False}}},
        {"$group": {"_id": "$room_type_id", "count": {"$sum": 1}, "room_type_name": {"$first": "$room_type_name"}}}
    ]))
    
    type_counts = {}
    for t in rooms_by_type:
        tid = t["_id"] or "unknown"
        name = t.get("room_type_name") or tid
        type_counts[tid] = {"total": t["count"], "name": name}
        print(f"  Tipo: {name:>25} ({tid}) -> {t['count']} habitaciones")
    
    dates = list(db.room_inventory_calendar.distinct("date", {"prop_id": prop_id}))
    print(f"\n  {len(dates)} fechas en inventario")
    
    updated = 0
    for date in dates:
        for room_type_id, info in type_counts.items():
            real_total = info["total"]
            booked = db.booking_orders.count_documents({
                "prop_id": prop_id,
                "room_type_id": room_type_id,
                "status": {"$in": ["confirmed", "checked_in"]},
                "check_in_date": {"$lte": date},
                "check_out_date": {"$gt": date},
            })
            new_available = max(0, real_total - booked)
            result = db.room_inventory_calendar.update_one(
                {"prop_id": prop_id, "date": date, "room_type_id": room_type_id},
                {"$set": {"total_rooms": real_total, "available_rooms": new_available, "blocked_rooms": 0}}
            )
            if result.modified_count > 0:
                updated += 1
    
    print(f"  Actualizados {updated} registros")
    
    # Crear registros faltantes
    all_dates = sorted(dates) if dates else []
    if not all_dates:
        today = datetime.now(timezone.utc)
        all_dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(-30, 60)]
    
    created = 0
    for date in all_dates:
        for room_type_id, info in type_counts.items():
            existing = db.room_inventory_calendar.find_one({
                "prop_id": prop_id, "date": date, "room_type_id": room_type_id
            })
            if not existing:
                booked = db.booking_orders.count_documents({
                    "prop_id": prop_id,
                    "room_type_id": room_type_id,
                    "status": {"$in": ["confirmed", "checked_in"]},
                    "check_in_date": {"$lte": date},
                    "check_out_date": {"$gt": date},
                })
                new_available = max(0, info["total"] - booked)
                db.room_inventory_calendar.insert_one({
                    "prop_id": prop_id,
                    "date": date,
                    "room_type_id": room_type_id,
                    "total_rooms": info["total"],
                    "available_rooms": new_available,
                    "blocked_rooms": 0,
                    "is_closed": False,
                })
                created += 1
    
    print(f"  Creados {created} registros faltantes")

print("\n✅ Inventario recalculado.")
