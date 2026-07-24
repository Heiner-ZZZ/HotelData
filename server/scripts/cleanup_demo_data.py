"""Clean up demo data and re-seed with clean room types and hotel rooms.

1. Delete all room_types, hotel_rooms with demo_seed=True
2. Delete hotel_products with seed_source='seed_hotel_products'
3. Create clean room_types without 'Demo' suffix
4. Create hotel_rooms with proper room numbers (101, 102, etc.)
5. Re-sync room_status_log with proper labels and Spanish statuses
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database

ROOM_TYPE_SPECS = [
    {"slug": "standard", "name": "Habitación Standard", "base_capacity": 2, "max_adults": 2, "max_children": 1},
    {"slug": "deluxe", "name": "Habitación Deluxe", "base_capacity": 3, "max_adults": 3, "max_children": 1},
    {"slug": "premium", "name": "Habitación Premium", "base_capacity": 2, "max_adults": 2, "max_children": 2},
    {"slug": "suite", "name": "Suite Ejecutiva", "base_capacity": 4, "max_adults": 4, "max_children": 2},
    {"slug": "family", "name": "Habitación Familiar", "base_capacity": 5, "max_adults": 4, "max_children": 3},
]

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def main() -> int:
    db = get_database()

    # ── Step 1: Delete demo data ──
    print("=== Eliminando datos demo ===")
    
    del_room_types = db.room_types.delete_many({"demo_seed": True})
    print(f"  room_types eliminados: {del_room_types.deleted_count}")
    
    del_hotel_rooms = db.hotel_rooms.delete_many({"demo_seed": True})
    print(f"  hotel_rooms eliminados: {del_hotel_rooms.deleted_count}")
    
    del_products = db.hotel_products.delete_many({"seed_source": "seed_hotel_products"})
    print(f"  hotel_products eliminados: {del_products.deleted_count}")
    
    # Also clean room_status_log entries that referenced demo rooms
    del_status = db.room_status_log.delete_many({"room_label": {"$regex": "Demo$"}})
    print(f"  room_status_log demo eliminados: {del_status.deleted_count}")
    
    # Fix any 'available' status to 'vacant_clean'
    fix_status = db.room_status_log.update_many(
        {"status": "available"},
        {"$set": {"status": "vacant_clean", "updated_at": utc_now()}}
    )
    print(f"  room_status_log 'available' → 'vacant_clean': {fix_status.modified_count}")
    
    # Fix room_labels that are room type names (not numbers)
    # Find entries where room_label is not a number-like string
    all_status = list(db.room_status_log.find({}, {"_id": 0, "room_label": 1, "hotel_room_id": 1}))
    for s in all_status:
        label = s.get("room_label", "")
        hr_id = s.get("hotel_room_id", "")
        if label and not label.isdigit() and "Demo" not in label:
            # Try to find the hotel_room to get its proper room_label
            if hr_id:
                hr = db.hotel_rooms.find_one({"hotel_room_id": hr_id}, {"_id": 0, "room_label": 1})
                if hr:
                    new_label = hr.get("room_label") or label
                    if new_label != label:
                        db.room_status_log.update_one(
                            {"hotel_room_id": hr_id},
                            {"$set": {"room_label": new_label, "updated_at": utc_now()}}
                        )
                        print(f"  room_status_log label corregido: '{label}' → '{new_label}'")

    # ── Step 2: Get existing properties ──
    hotels = list(
        db.dim_hotels.find({}, {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1})
        .sort("prop_id", 1)
        .limit(5)
    )
    
    if not hotels:
        print("No se encontraron hoteles en dim_hotels")
        return 1

    print(f"\n=== Creando datos limpios para {len(hotels)} hoteles ===")
    
    total_room_types = 0
    total_hotel_rooms = 0
    
    for hotel in hotels:
        prop_id = int(hotel["prop_id"])
        name = hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}"
        
        room_start = 100 + (prop_id * 10)  # Room numbers: 110, 120, 130, etc.
        
        for i, spec in enumerate(ROOM_TYPE_SPECS):
            room_type_id = f"RT-{prop_id}-{spec['slug']}"
            
            # Create room type
            db.room_types.update_one(
                {"room_type_id": room_type_id},
                {"$set": {
                    "room_type_id": room_type_id,
                    "prop_id": prop_id,
                    "name": spec["name"],
                    "description": f"{spec['name']} para {name}",
                    "base_capacity": spec["base_capacity"],
                    "max_adults": spec["max_adults"],
                    "max_children": spec["max_children"],
                    "is_active": True,
                    "updated_at": utc_now(),
                }, "$setOnInsert": {"created_at": utc_now()}},
                upsert=True,
            )
            total_room_types += 1
            
            # Create 2 physical rooms per room type with proper room numbers
            for j in range(2):
                room_num = room_start + i * 2 + j
                hotel_room_id = f"HR-{prop_id}-{room_num}"
                
                db.hotel_rooms.update_one(
                    {"hotel_room_id": hotel_room_id},
                    {"$set": {
                        "hotel_room_id": hotel_room_id,
                        "prop_id": prop_id,
                        "room_type_id": room_type_id,
                        "room_label": str(room_num),
                        "floor": str(room_num // 100),
                        "is_active": True,
                        "updated_at": utc_now(),
                    }, "$setOnInsert": {"created_at": utc_now()}},
                    upsert=True,
                )
                total_hotel_rooms += 1
                
                # Create room_status_log with Spanish status
                db.room_status_log.update_one(
                    {"prop_id": prop_id, "room_label": str(room_num)},
                    {"$set": {
                        "prop_id": prop_id,
                        "hotel_room_id": hotel_room_id,
                        "room_type_id": room_type_id,
                        "room_label": str(room_num),
                        "status": "vacant_clean",
                        "note": "Disponible",
                        "updated_at": utc_now(),
                    }, "$setOnInsert": {"created_at": utc_now()}},
                    upsert=True,
                )

    # ── Summary ──
    print("\n=== Resumen ===")
    print(f"  room_types creados: {total_room_types}")
    print(f"  hotel_rooms creados: {total_hotel_rooms}")
    print(f"  room_status_log total: {db.room_status_log.count_documents({})}")
    
    # Verify
    remaining_available = db.room_status_log.count_documents({"status": "available"})
    print(f"  room_status_log con 'available' (debería ser 0): {remaining_available}")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
