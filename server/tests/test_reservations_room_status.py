"""Tests for room-status-aware reservation validation.

When a booking targets a specific physical room (``hotel_room_id`` from the
reception Timeline), the reservation must consult the housekeeping room
status (``room_status_log``):

- Rooms out of order / out of service / under maintenance can't be booked at
  all, and the scheduled maintenance date is surfaced when one covers the
  stay.
- Rooms still dirty or being cleaned can't be booked for the SAME day (the
  hotel needs time to clean them before a same-day arrival).
- Future dates are unaffected by dirtiness (housekeeping cleans before
  arrival), and bookings without a specific physical room keep ignoring
  per-room status.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._helpers import ReservationInput
from src.app.modules.reservations.service.lifecycle import create_booking


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


@pytest.fixture
def seeded_hotel_with_room(db):
    """Hotel with a physical room + inventory + rates around today's date."""
    prop_id = 987
    db.dim_hotels.insert_one({
        "prop_id": prop_id,
        "hotel_name": "Status Hotel",
        "display_name": "Status Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-987-standard",
        "prop_id": prop_id,
        "name": "Standard",
        "base_capacity": 2,
        "max_adults": 2,
        "max_children": 1,
        "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": "HR-987-101",
        "room_label": "101",
        "room_type_id": "RT-987-standard",
        "is_active": True,
    })
    for offset in range(0, 6):
        day = _days_from_today(offset)
        db.room_inventory_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-987-standard",
            "date": day,
            "total_rooms": 10,
            "available_rooms": 5,
            "is_available": True,
        })
        db.hotel_rate_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-987-standard",
            "date": day,
            "rate_amount": 150.0,
            "currency": "USD",
            "is_closed": False,
        })
    return prop_id


def _booking_payload(prop_id: int, check_in: str, check_out: str, **overrides) -> ReservationInput:
    base = dict(
        prop_id=prop_id,
        guest_name="Room Guest",
        guest_email="room@test.com",
        guest_phone="+1234567890",
        cedula="1234567890",
        room_type_id="RT-987-standard",
        hotel_room_id="HR-987-101",
        check_in_date=check_in,
        check_out_date=check_out,
        check_in_time="15:00",
        check_out_time="12:00",
        adults=2,
        children=0,
        rooms=1,
        comment="",
        source="test",
        is_test=True,
    )
    base.update(overrides)
    return ReservationInput(**base)


def _set_room_status(db, prop_id: int, status: str) -> None:
    db.room_status_log.delete_many({"prop_id": prop_id})
    db.room_status_log.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": "HR-987-101",
        "room_label": "101",
        "room_type_id": "RT-987-standard",
        "status": status,
    })


class TestRoomStatusSameDayDirty:
    def test_booking_blocked_when_room_dirty_today(self, db, seeded_hotel_with_room):
        _set_room_status(db, seeded_hotel_with_room, "vacant_dirty")
        with pytest.raises(ValueError, match="limpieza pendiente"):
            create_booking(_booking_payload(
                seeded_hotel_with_room, _days_from_today(0), _days_from_today(2)))

    def test_booking_blocked_when_room_cleaning_today(self, db, seeded_hotel_with_room):
        _set_room_status(db, seeded_hotel_with_room, "cleaning_in_progress")
        with pytest.raises(ValueError, match="limpieza pendiente"):
            create_booking(_booking_payload(
                seeded_hotel_with_room, _days_from_today(0), _days_from_today(2)))

    def test_booking_allowed_when_room_clean_today(self, db, seeded_hotel_with_room):
        _set_room_status(db, seeded_hotel_with_room, "vacant_clean")
        result = create_booking(_booking_payload(
            seeded_hotel_with_room, _days_from_today(0), _days_from_today(2)))
        assert result["status"] == "pending"

    def test_booking_allowed_for_future_date_when_room_dirty(self, db, seeded_hotel_with_room):
        _set_room_status(db, seeded_hotel_with_room, "vacant_dirty")
        result = create_booking(_booking_payload(
            seeded_hotel_with_room, _days_from_today(1), _days_from_today(3)))
        assert result["status"] == "pending"


class TestRoomStatusBlocksOffline:
    @pytest.mark.parametrize("status", ["out_of_order", "out_of_service", "maintenance_requested"])
    def test_booking_blocked_when_room_offline(self, db, seeded_hotel_with_room, status):
        _set_room_status(db, seeded_hotel_with_room, status)
        with pytest.raises(ValueError, match="no está disponible|no puede reservarse"):
            create_booking(_booking_payload(
                seeded_hotel_with_room, _days_from_today(1), _days_from_today(3)))

    def test_maintenance_message_surfaces_scheduled_date(self, db, seeded_hotel_with_room):
        _set_room_status(db, seeded_hotel_with_room, "maintenance_requested")
        db.maintenance_tasks.insert_one({
            "prop_id": seeded_hotel_with_room,
            "hotel_room_id": "HR-987-101",
            "room_label": "101",
            "status": "scheduled",
            "auto_block": True,
            "scheduled_date": _days_from_today(1),
        })
        with pytest.raises(ValueError, match="mantenimiento hasta"):
            create_booking(_booking_payload(
                seeded_hotel_with_room, _days_from_today(1), _days_from_today(3)))

    def test_maintenance_task_blocks_even_when_status_log_is_clean(self, db, seeded_hotel_with_room):
        """Una tarea de mantenimiento programada bloquea aunque el
        ``room_status_log`` esté desactualizado (p. ej. limpieza lo
        sobrescribió): la fecha programada es la fuente de la prohibición.
        """
        _set_room_status(db, seeded_hotel_with_room, "vacant_clean")
        db.maintenance_tasks.insert_one({
            "prop_id": seeded_hotel_with_room,
            "hotel_room_id": "HR-987-101",
            "room_label": "101",
            "status": "scheduled",
            "auto_block": True,
            "scheduled_date": _days_from_today(1),
        })
        with pytest.raises(ValueError, match="mantenimiento hasta"):
            create_booking(_booking_payload(
                seeded_hotel_with_room, _days_from_today(1), _days_from_today(3)))

    def test_completed_maintenance_does_not_block(self, db, seeded_hotel_with_room):
        """Mantenimiento completado/borrado no bloquea la reserva futura."""
        _set_room_status(db, seeded_hotel_with_room, "vacant_clean")
        db.maintenance_tasks.insert_one({
            "prop_id": seeded_hotel_with_room,
            "hotel_room_id": "HR-987-101",
            "room_label": "101",
            "status": "completed",
            "auto_block": True,
            "scheduled_date": _days_from_today(1),
        })
        result = create_booking(_booking_payload(
            seeded_hotel_with_room, _days_from_today(1), _days_from_today(3)))
        assert result["status"] == "pending"


class TestRoomStatusNotRequiredWithoutPhysicalRoom:
    def test_booking_without_physical_room_ignores_room_status(self, db, seeded_hotel_with_room):
        _set_room_status(db, seeded_hotel_with_room, "vacant_dirty")
        result = create_booking(_booking_payload(
            seeded_hotel_with_room, _days_from_today(0), _days_from_today(2), hotel_room_id=""))
        assert result["status"] == "pending"


class TestPreviewReportsRoomStatus:
    @pytest.mark.asyncio
    async def test_preview_reports_unavailable_for_dirty_room_today(self, db, seeded_hotel_with_room):
        from src.app.modules.reservations.routes.reservations_impl import preview_reservation

        _set_room_status(db, seeded_hotel_with_room, "vacant_dirty")
        result = preview_reservation({
            "prop_id": seeded_hotel_with_room,
            "guest_name": "Preview Guest",
            "guest_email": "preview@test.com",
            "guest_phone": "+1234567890",
            "cedula": "1234567890",
            "room_type_id": "RT-987-standard",
            "hotel_room_id": "HR-987-101",
            "check_in_date": _days_from_today(0),
            "check_out_date": _days_from_today(2),
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "adults": 2,
            "children": 0,
            "rooms": 1,
        })
        assert result["available"] is False
        assert "limpieza pendiente" in result["availability_message"]
