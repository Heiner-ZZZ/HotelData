"""Inventory management for booking transitions."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from pymongo import ASCENDING

from src.database.connection import get_database
from .._helpers import utc_now

logger = logging.getLogger(__name__)


def _auto_assign_rooms(
    prop_id: int,
    room_type_id: str,
    check_in_date: str,
    check_out_date: str,
    rooms_required: int,
    booking_id: str,
    is_test: bool = False,
) -> list[str]:
    """Auto-assign physical rooms from hotel_rooms to a confirmed booking."""
    if not room_type_id or rooms_required < 1:
        return []

    db = get_database()

    all_rooms = list(
        db.hotel_rooms.find(
            {"prop_id": prop_id, "room_type_id": room_type_id, "is_active": True},
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1},
        ).sort([("room_number", ASCENDING)])
    )
    if not all_rooms:
        logger.info("No physical rooms found for prop_id=%s room_type=%s — skipping auto-assign", prop_id, room_type_id)
        return []

    overlapping = list(
        db.booking_orders.find(
            {
                "booking_id": {"$ne": booking_id},
                "prop_id": prop_id,
                "status": {"$in": ["confirmed", "checked_in"]},
                "check_in_date": {"$lt": check_out_date},
                "check_out_date": {"$gt": check_in_date},
                "assigned_rooms.0": {"$exists": True},
            },
            {"_id": 0, "assigned_rooms": 1},
        )
    )
    assigned_elsewhere: set[str] = set()
    for book in overlapping:
        for room_id in book.get("assigned_rooms", []):
            assigned_elsewhere.add(room_id)

    available = [r for r in all_rooms if r["hotel_room_id"] not in assigned_elsewhere]
    to_assign = available[:rooms_required]
    if not to_assign:
        logger.warning(
            "No available rooms to auto-assign for booking %s (prop=%s, type=%s, needed=%d)",
            booking_id, prop_id, room_type_id, rooms_required,
        )
        return []

    assigned_ids = [r["hotel_room_id"] for r in to_assign]
    now_iso = utc_now()

    for room in to_assign:
        room_label = room.get("room_label", "")
        if room_label:
            try:
                db.room_status_log.update_one(
                    {"prop_id": prop_id, "room_label": room_label},
                    {
                        "$set": {"status": "occupied", "note": f"Auto-asignada desde reserva {booking_id}", "updated_at": now_iso},
                        "$setOnInsert": {"created_at": now_iso, "prop_id": prop_id, "room_type_id": room_type_id,
                                         "room_label": room_label, "hotel_room_id": room["hotel_room_id"],
                                         "room_number": room.get("room_number", "")},
                    },
                    upsert=True,
                )
            except Exception:
                logger.exception("Failed to update room_status_log for %s", room_label)

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": {"assigned_rooms": assigned_ids, "updated_at": now_iso}})
    db.booking_status_history.insert_one({
        "booking_id": booking_id, "status": "confirmed",
        "changed_at": now_iso, "reason": f"rooms_auto_assigned: {', '.join(assigned_ids)}",
        "changed_by": "system", "is_test": is_test,
    })
    logger.info("Auto-assigned %d room(s) to booking %s", len(assigned_ids), booking_id)
    return assigned_ids


def _deduct_inventory(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str,
) -> None:
    """Decrement available_rooms in room_inventory_calendar with optimistic locking."""
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    for date_str in dates:
        result = db.room_inventory_calendar.find_one_and_update(
            {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str, "available_rooms": {"$gte": rooms}},
            {"$inc": {"available_rooms": -rooms}},
            projection={"_id": 0, "available_rooms": 1},
        )
        if result is None:
            existing = db.room_inventory_calendar.find_one(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
                {"_id": 0, "available_rooms": 1},
            )
            if existing is None:
                raise ValueError(
                    f"No hay datos de inventario para la fecha {date_str}. "
                    f"No se puede confirmar la reserva sin inventario disponible."
                )
            else:
                current_avail = existing.get("available_rooms", 0)
                raise ValueError(
                    f"Inventario insuficiente para {date_str}: "
                    f"se requieren {rooms} habitación(es) pero solo hay {current_avail} disponible(s)."
                )


def _restore_inventory(
    prop_id: int,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    room_type_id: str,
) -> None:
    """Increment available_rooms in room_inventory_calendar. Called on check-out/cancel."""
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return

    db = get_database()
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((check_out - check_in).days)]
    for date_str in dates:
        db.room_inventory_calendar.update_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "date": date_str},
            {"$inc": {"available_rooms": rooms}},
        )
