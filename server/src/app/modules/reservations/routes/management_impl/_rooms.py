"""Room assignment — list available rooms and assign to booking."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from pymongo import ASCENDING

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._helpers import utc_now
from src.app.modules.partner.services.audit import register_action


def get_available_rooms(
    booking_id: str,
    db,
) -> dict[str, Any]:
    """List available physical rooms for a booking based on its room type and prop.

    Raises HTTPException if booking is not found.
    """
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "prop_id": 1, "room_type_id": 1, "check_in_date": 1, "check_out_date": 1, "rooms": 1},
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    prop_id = int(booking.get("prop_id", 0))
    room_type_id = booking.get("room_type_id", "")
    required = int(booking.get("rooms", 1))

    # Room type info
    room_type = None
    if room_type_id:
        rt = db.room_types.find_one(
            {"room_type_id": room_type_id, "prop_id": prop_id},
            {"_id": 0, "name": 1, "base_capacity": 1, "max_adults": 1},
        )
        if rt:
            room_type = rt

    # Available physical rooms
    room_filter: dict[str, Any] = {"prop_id": prop_id, "is_active": True}
    if room_type_id:
        room_filter["room_type_id"] = room_type_id
    available_rooms = list(
        db.hotel_rooms.find(
            room_filter,
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "floor": 1},
        )
        .sort([("room_label", ASCENDING)])
    )

    # Enrich with current status from room_status_log
    room_labels = [
        r.get("room_label", "")
        for r in available_rooms
        if r.get("room_label")
    ]
    status_map: dict[str, str] = {}
    if room_labels:
        for doc in db.room_status_log.find(
            {"prop_id": prop_id, "room_label": {"$in": room_labels}},
            {"_id": 0, "room_label": 1, "status": 1},
        ):
            status_map[doc["room_label"]] = doc["status"]

    for room in available_rooms:
        label = room.get("room_label", "")
        room["room_status"] = status_map.get(label, "unknown")

    assigned_rooms = []
    existing_assigned = list(
        db.booking_orders.find(
            {"booking_id": booking_id},
            {"_id": 0, "assigned_rooms": 1},
        )
    )
    if existing_assigned and existing_assigned[0].get("assigned_rooms"):
        assigned_rooms = existing_assigned[0]["assigned_rooms"]

    return {
        "prop_id": prop_id,
        "room_type": room_type,
        "rooms_required": required,
        "rooms_available": len(available_rooms),
        "available_rooms": available_rooms,
        "assigned_rooms": assigned_rooms,
    }


def assign_rooms_to_booking(
    booking_id: str,
    room_ids: list[str],
    current_user: dict,
    db,
) -> dict[str, Any]:
    """Assign specific physical rooms to a booking.

    Raises HTTPException if booking not found or room_ids is invalid.
    """
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "_id": 0,
            "prop_id": 1,
            "room_type_id": 1,
            "check_out_date": 1,
            "status": 1,
            "stay_status": 1,
            "is_test": 1,
        },
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not isinstance(room_ids, list):
        raise HTTPException(status_code=400, detail="room_ids must be a list")
    if any(not isinstance(room_id, str) or not room_id.strip() for room_id in room_ids):
        raise HTTPException(status_code=400, detail="room_ids must contain valid room ids")
    if len(set(room_ids)) != len(room_ids):
        raise HTTPException(status_code=400, detail="room_ids must not contain duplicates")

    if booking.get("status") in {"cancelled", "rejected"} or booking.get("stay_status") in {"checked_out", "cancelled"}:
        raise HTTPException(status_code=400, detail="Cannot reassign a cancelled or completed booking")

    check_out_date = str(booking.get("check_out_date") or "")[:10]
    if check_out_date and check_out_date < local_today():
        raise HTTPException(status_code=400, detail="Cannot reassign a booking after check-out")

    prop_id = int(booking.get("prop_id") or 0)
    if room_ids:
        room_filter: dict[str, Any] = {
            "hotel_room_id": {"$in": room_ids},
            "prop_id": prop_id,
            "is_active": True,
        }
        room_documents = list(db.hotel_rooms.find(
            room_filter,
            {"_id": 0, "hotel_room_id": 1, "room_type_id": 1},
        ))
        if len(room_documents) != len(room_ids):
            raise HTTPException(status_code=400, detail="One or more rooms do not belong to this hotel or are inactive")

        booking_room_type = booking.get("room_type_id")
        if booking_room_type and any(room.get("room_type_id") != booking_room_type for room in room_documents):
            raise HTTPException(status_code=400, detail="Assigned rooms must match the booking room type")

    now = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"assigned_rooms": room_ids, "updated_at": now}},
    )

    changed_by_username = current_user.get("username", "web")
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "confirmed"),
        "changed_at": now,
        "reason": f"rooms_assigned: {', '.join(room_ids)}",
        "changed_by": changed_by_username,
        "is_test": bool(booking.get("is_test")),
    })

    # ── Audit log ──
    try:
        booking_full = db.booking_orders.find_one(
            {"booking_id": booking_id},
            {"_id": 0, "prop_id": 1, "guest_name": 1},
        )
        if booking_full:
            register_action(
                prop_id=int(booking_full.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="reassign_room",
                summary=f"Habitaciones reasignadas a {', '.join(room_ids)} — {booking_full.get('guest_name', '')}",
                changed_by=changed_by_username,
                metadata={"assigned_rooms": room_ids, "guest_name": booking_full.get("guest_name", "")},
            )
    except Exception:
        pass  # audit failure must never block the operation

    return {"booking_id": booking_id, "assigned_rooms": room_ids, "assigned_count": len(room_ids)}
