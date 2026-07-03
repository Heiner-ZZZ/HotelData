"""Availability check — validate hotel room types and inventory for a date range."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException

from src.database.connection import get_database


def check_hotel_availability(
    prop_id: int,
    check_in: str,
    check_out: str,
) -> dict:
    """Check if a hotel has room types and inventory available for a given date range."""
    db = get_database()

    # 1. Check if the hotel has room types
    room_types_count = db.room_types.count_documents({"prop_id": prop_id})
    has_room_types = room_types_count > 0

    # 2. Check if there's inventory for the date range
    try:
        cin = datetime.strptime(check_in, "%Y-%m-%d")
        cout = datetime.strptime(check_out, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    dates = [(cin + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(max(1, (cout - cin).days))]

    if not has_room_types:
        return {
            "hasInventory": False, "hasRoomTypes": False,
            "totalRooms": 0, "availableRooms": 0,
            "message": "El hotel no tiene tipos de habitación configurados.",
        }

    inventory_records = list(
        db.room_inventory_calendar.find(
            {"prop_id": prop_id, "date": {"$in": dates}},
            {"_id": 0, "available_rooms": 1, "total_rooms": 1},
        )
    )

    if not inventory_records:
        return {
            "hasInventory": False, "hasRoomTypes": True,
            "totalRooms": 0, "availableRooms": 0,
            "message": "No hay datos de inventario para las fechas seleccionadas.",
        }

    total_rooms = max(r.get("total_rooms", 0) or 0 for r in inventory_records)
    min_available = min(r.get("available_rooms", 0) or 0 for r in inventory_records)
    has_inventory = min_available > 0

    return {
        "hasInventory": has_inventory,
        "hasRoomTypes": True,
        "totalRooms": total_rooms,
        "availableRooms": min_available,
        "message": (
            f"{min_available} habitación(es) disponible(s) en las fechas seleccionadas."
            if has_inventory
            else "Sin disponibilidad en las fechas seleccionadas."
        ),
    }
