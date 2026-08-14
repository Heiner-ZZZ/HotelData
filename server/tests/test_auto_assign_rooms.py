"""Auto-assignment of physical rooms must not mutate the housekeeping status log."""
from __future__ import annotations

from src.app.modules.reservations.service._transitions._inventory import _auto_assign_rooms


def test_auto_assign_rooms_does_not_touch_room_status_log(db):
    """Assigning a room to a booking must leave the physical housekeeping status intact."""
    db.hotel_rooms.insert_one({
        "prop_id": 953,
        "hotel_room_id": "HR-953-101",
        "room_type_id": "standard",
        "room_label": "101",
        "is_active": True,
    })
    db.booking_orders.insert_one({
        "prop_id": 953,
        "booking_id": "BK-953-001",
        "room_type_id": "standard",
        "rooms": 1,
        "status": "pending",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-12",
    })
    # A pre-existing physical status: the room is vacant and clean.
    db.room_status_log.insert_one({
        "prop_id": 953,
        "room_type_id": "standard",
        "room_label": "101",
        "status": "vacant_clean",
        "note": "initial",
        "updated_at": "2026-08-09T10:00:00Z",
    })

    assigned = _auto_assign_rooms(
        prop_id=953,
        room_type_id="standard",
        check_in_date="2026-08-10",
        check_out_date="2026-08-12",
        rooms_required=1,
        booking_id="BK-953-001",
    )

    assert assigned == ["HR-953-101"]
    booking = db.booking_orders.find_one({"booking_id": "BK-953-001"})
    assert booking["assigned_rooms"] == ["HR-953-101"]

    # The physical status must remain exactly as it was: one record, still
    # vacant_clean, no auto-assignment note.
    statuses = list(db.room_status_log.find({"prop_id": 953, "room_label": "101"}))
    assert len(statuses) == 1
    assert statuses[0]["status"] == "vacant_clean"
    assert "Auto-asignada" not in statuses[0].get("note", "")
