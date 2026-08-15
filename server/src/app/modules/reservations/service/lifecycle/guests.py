"""Room guests: per-room passenger manifest management."""

from __future__ import annotations

from typing import Any

from src.database.connection import get_database

from .._helpers import utc_now
from ..collections import ensure_reservation_collections

ROOM_GUESTS = "booking_room_guests"


def get_room_guests(booking_id: str) -> list[dict[str, Any]]:
    db = get_database()
    items = list(db[ROOM_GUESTS].find({"booking_id": booking_id}, {"_id": 0}).sort("room_index", 1))
    # If no room guests saved yet, auto-populate room 0 with the booking's main guest
    if not items:
        booking = db.booking_orders.find_one(
            {"booking_id": booking_id},
            {"_id": 0, "guest_name": 1, "guest_email": 1, "guest_phone": 1, "rooms": 1},
        )
        if booking and booking.get("guest_name"):
            total_rooms = max(int(booking.get("rooms") or 1), 1)
            items = []
            for ri in range(total_rooms):
                if ri == 0:
                    items.append({
                        "booking_id": booking_id,
                        "room_index": 0,
                        "guests": [{
                            "guest_name": booking.get("guest_name", ""),
                            "guest_email": booking.get("guest_email", ""),
                            "guest_phone": booking.get("guest_phone", ""),
                            "age": None,
                            "is_child": False,
                            "is_primary_for_room": True,
                        }],
                    })
                else:
                    items.append({
                        "booking_id": booking_id,
                        "room_index": ri,
                        "guests": [],
                    })
    return items


def save_room_guests(booking_id: str, room_guests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = get_database()
    ensure_reservation_collections()
    now = utc_now()

    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        raise ValueError("No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError(
            "No se pueden modificar los huéspedes de una reserva cancelada o rechazada. "
            "Creá una reserva nueva para registrar a los huéspedes."
        )

    max_rooms = int(booking.get("rooms", 1))
    for entry in room_guests:
        ri = int(entry.get("room_index", 0))
        if ri < 0 or ri >= max_rooms:
            raise ValueError(
                f"El índice de habitación {ri} está fuera de rango (0-{max_rooms - 1}). "
                "Verificá que la habitación pertenezca a esta reserva."
            )

    db[ROOM_GUESTS].delete_many({"booking_id": booking_id})
    docs = []
    for entry in room_guests:
        doc = {
            "booking_id": booking_id,
            "room_index": int(entry.get("room_index", 0)),
            "guests": [
                {
                    "guest_name": g.get("guest_name", "").strip(),
                    "guest_email": g.get("guest_email", "").strip(),
                    "guest_phone": g.get("guest_phone", "").strip(),
                    "age": int(g["age"]) if g.get("age") is not None else None,
                    "is_child": bool(g.get("is_child", False)),
                    "is_primary_for_room": bool(g.get("is_primary_for_room", False)),
                }
                for g in entry.get("guests", [])
            ],
            "created_at": now, "updated_at": now,
            "is_test": bool(booking.get("is_test")),
        }
        docs.append(doc)
    if docs:
        db[ROOM_GUESTS].insert_many(docs)

    return get_room_guests(booking_id)


def get_check_in_status(booking_id: str) -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        return {"status": "unknown", "message": "No se encontró la reserva."}

    total_rooms = int(booking.get("rooms", 1))
    room_guests = list(db[ROOM_GUESTS].find({"booking_id": booking_id}).sort("room_index", 1))

    rooms_with_data = len(room_guests)
    all_complete = True
    per_room = []
    for ri in range(total_rooms):
        room_doc = next((r for r in room_guests if r.get("room_index") == ri), None)
        if room_doc:
            guest_count = len(room_doc.get("guests", []))
            per_room.append({"room_index": ri, "guest_count": guest_count, "complete": guest_count > 0})
            if guest_count == 0:
                all_complete = False
        else:
            per_room.append({"room_index": ri, "guest_count": 0, "complete": False})
            all_complete = False

    return {
        "booking_id": booking_id, "total_rooms": total_rooms,
        "rooms_with_data": rooms_with_data, "all_complete": all_complete,
        "per_room": per_room,
    }
