"""Tests for real-time room availability validation in early check-in.

The ``validate_room_availability`` service checks:
1. Current room status (vacant_clean, vacant_dirty, occupied_clean, maintenance_requested, out_of_service, etc.)
2. Overlapping reservations on the same physical room
3. Pending housekeeping/maintenance tasks
4. Room assignment existence

This is a READ-ONLY endpoint used by the frontend when the early check-in
dialog opens, so the receptionist sees current room status before authorizing.
"""
from __future__ import annotations

import pytest

from src.app.modules.reservations.service._room_availability import (
    validate_room_availability,
)

FIXED_DATE = "2026-08-14"


def _seed_booking(db, booking_id: str, *, assigned_rooms: list[str] | None = None) -> None:
    rooms = assigned_rooms if assigned_rooms is not None else ["ROOM-991-1"]
    if rooms:
        db.hotel_rooms.insert_one({"hotel_room_id": rooms[0], "room_label": "101", "floor": "1"})
        db.room_status_log.insert_one({"prop_id": 991, "room_label": "101", "status": "vacant_clean"})
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "guest_name": "Test Guest",
            "guest_email": "test@test.com",
            "check_in_date": FIXED_DATE,
            "check_out_date": "2026-08-16",
            "total_price": 218.0,
            "currency": "USD",
            "total_nights": 2,
            "rooms": 1,
            "assigned_rooms": rooms,
            "status": "confirmed",
            "stay_status": "pending",
            "is_test": True,
        }
    )


class TestRoomAvailabilityValidation:
    """Test cases for validate_room_availability service."""

    def test_returns_all_available_when_room_is_vacant_clean(self, db):
        """A vacant_clean room should be marked as available."""
        _seed_booking(db, "BK-AVAIL-001")
        result = validate_room_availability("BK-AVAIL-001")

        assert result["booking_id"] == "BK-AVAIL-001"
        assert result["all_available"] is True
        assert len(result["rooms"]) == 1
        assert result["rooms"][0]["status"] == "vacant_clean"
        assert result["rooms"][0]["is_vacant"] is True
        assert result["rooms"][0]["available"] is True
        assert result["issues"] == []

    def test_returns_all_available_when_room_is_vacant_dirty(self, db):
        """A vacant_dirty room should also be marked as available."""
        _seed_booking(db, "BK-AVAIL-002")
        db.room_status_log.update_one(
            {"prop_id": 991, "room_label": "101"},
            {"$set": {"status": "vacant_dirty"}},
        )
        result = validate_room_availability("BK-AVAIL-002")

        assert result["all_available"] is True
        assert result["rooms"][0]["status"] == "vacant_dirty"
        assert result["rooms"][0]["is_vacant"] is True
        assert result["rooms"][0]["available"] is True

    def test_marks_room_unavailable_when_occupied(self, db):
        """An occupied room should block early check-in."""
        _seed_booking(db, "BK-AVAIL-003")
        db.room_status_log.update_one(
            {"prop_id": 991, "room_label": "101"},
            {"$set": {"status": "occupied_clean"}},
        )
        result = validate_room_availability("BK-AVAIL-003")

        assert result["all_available"] is False
        assert result["rooms"][0]["status"] == "occupied_clean"
        assert result["rooms"][0]["is_vacant"] is False
        assert result["rooms"][0]["available"] is False
        assert len(result["issues"]) == 1
        assert "ocupada" in result["issues"][0].lower() or "disponible" in result["issues"][0].lower()

    def test_marks_room_unavailable_when_in_maintenance(self, db):
        """A room in maintenance should block early check-in."""
        _seed_booking(db, "BK-AVAIL-004")
        db.room_status_log.update_one(
            {"prop_id": 991, "room_label": "101"},
            {"$set": {"status": "maintenance_requested"}},
        )
        result = validate_room_availability("BK-AVAIL-004")

        assert result["all_available"] is False
        assert result["rooms"][0]["status"] == "maintenance_requested"
        assert result["rooms"][0]["is_vacant"] is False
        assert result["rooms"][0]["available"] is False

    def test_marks_room_unavailable_when_out_of_service(self, db):
        """An out-of-service room should block early check-in."""
        _seed_booking(db, "BK-AVAIL-OOS")
        db.room_status_log.update_one(
            {"prop_id": 991, "room_label": "101"},
            {"$set": {"status": "out_of_service"}},
        )
        result = validate_room_availability("BK-AVAIL-OOS")

        assert result["all_available"] is False
        assert result["rooms"][0]["status"] == "out_of_service"
        assert result["rooms"][0]["is_vacant"] is False
        assert result["rooms"][0]["available"] is False

    def test_detects_overlapping_reservations(self, db):
        """Another active booking on the same room should be detected."""
        _seed_booking(db, "BK-AVAIL-005")
        # Create an overlapping booking that starts DURING our stay
        # Our stay: 2026-08-14 → 2026-08-16
        # Overlap: 2026-08-15 → 2026-08-17 (starts during our stay)
        db.booking_orders.insert_one(
            {
                "booking_id": "BK-OVERLAP",
                "prop_id": 991,
                "guest_name": "Other Guest",
                "check_in_date": "2026-08-15",
                "check_out_date": "2026-08-17",
                "assigned_rooms": ["ROOM-991-1"],  # Same room as BK-AVAIL-005
                "status": "confirmed",
                "stay_status": "checked_in",
                "is_test": True,
            }
        )
        result = validate_room_availability("BK-AVAIL-005")

        assert result["all_available"] is False
        room = result["rooms"][0]
        assert "overlapping_bookings" in room
        assert len(room["overlapping_bookings"]) == 1
        assert room["overlapping_bookings"][0]["booking_id"] == "BK-OVERLAP"

    def test_no_overlap_when_reservations_are_sequential(self, db):
        """Non-overlapping dates should not flag an issue."""
        _seed_booking(db, "BK-AVAIL-006")
        # Create a non-overlapping booking (ends before ours starts)
        db.booking_orders.insert_one(
            {
                "booking_id": "BK-NO-OVERLAP",
                "prop_id": 991,
                "guest_name": "Previous Guest",
                "check_in_date": "2026-08-10",
                "check_out_date": "2026-08-13",  # Ends before our check-in
                "assigned_rooms": ["ROOM-991-1"],
                "status": "confirmed",
                "stay_status": "checked_out",
                "is_test": True,
            }
        )
        result = validate_room_availability("BK-AVAIL-006")

        assert result["all_available"] is True
        assert "overlapping_bookings" not in result["rooms"][0] or len(result["rooms"][0].get("overlapping_bookings", [])) == 0

    def test_shows_pending_housekeeping_tasks(self, db):
        """Pending housekeeping tasks should be informational, not blocking."""
        _seed_booking(db, "BK-AVAIL-007")
        db.housekeeping_tasks.insert_one(
            {
                "prop_id": 991,
                "room_label": "101",
                "task_type": "cleaning",
                "status": "pending",
                "is_test": True,
            }
        )
        result = validate_room_availability("BK-AVAIL-007")

        # Room is still available (tasks are informational)
        assert result["all_available"] is True
        assert "pending_tasks" in result["rooms"][0]
        assert "cleaning" in result["rooms"][0]["pending_tasks"]

    def test_blocks_on_active_maintenance_task_even_when_vacant(self, db):
        """An active (pending) maintenance work order blocks even if the room
        is vacant_clean — the task is the source of truth, not the room status."""
        _seed_booking(db, "BK-AVAIL-MT")
        db.maintenance_tasks.insert_one(
            {
                "prop_id": 991,
                "room_label": "101",
                "hotel_room_id": "ROOM-991-1",
                "status": "pending",
                "task_type": "preventivo",
                "title": "Reparación de A/C",
                "is_test": True,
            }
        )
        result = validate_room_availability("BK-AVAIL-MT")

        assert result["all_available"] is False
        assert result["rooms"][0]["available"] is False
        assert "maintenance_tasks" in result["rooms"][0]
        assert any("mantenimiento" in i.lower() for i in result["issues"])

    def test_completed_maintenance_task_does_not_block(self, db):
        """A completed maintenance work order must not block check-in."""
        _seed_booking(db, "BK-AVAIL-MT-DONE")
        db.maintenance_tasks.insert_one(
            {
                "prop_id": 991,
                "room_label": "101",
                "hotel_room_id": "ROOM-991-1",
                "status": "completed",
                "task_type": "preventivo",
                "title": "Reparación de A/C",
                "is_test": True,
            }
        )
        result = validate_room_availability("BK-AVAIL-MT-DONE")

        assert result["all_available"] is True
        assert result["rooms"][0]["available"] is True

    def test_raises_when_booking_not_found(self, db):
        """Non-existent booking should raise ValueError."""
        with pytest.raises(ValueError, match="Reserva no encontrada"):
            validate_room_availability("BK-DOES-NOT-EXIST")

    def test_handles_no_assigned_rooms(self, db):
        """Booking with no assigned rooms should report unavailable."""
        _seed_booking(db, "BK-AVAIL-008", assigned_rooms=[])
        result = validate_room_availability("BK-AVAIL-008")

        assert result["all_available"] is False
        assert len(result["rooms"]) == 0
        assert len(result["issues"]) == 1
        assert "no hay habitaciones" in result["issues"][0].lower()

    def test_validated_at_contains_current_date(self, db):
        """The response should include the validation timestamp."""
        _seed_booking(db, "BK-AVAIL-009")
        result = validate_room_availability("BK-AVAIL-009")

        assert "validated_at" in result
        # validated_at should be today's date (current runtime)
        from datetime import date
        assert result["validated_at"] == date.today().isoformat()

    def test_multiple_rooms_mixed_availability(self, db):
        """With multiple rooms, some available and some not, should reflect both."""
        # Create booking with two rooms
        db.hotel_rooms.insert_one({"hotel_room_id": "ROOM-991-1", "room_label": "101", "floor": "1"})
        db.hotel_rooms.insert_one({"hotel_room_id": "ROOM-991-2", "room_label": "102", "floor": "1"})
        db.room_status_log.insert_one({"prop_id": 991, "room_label": "101", "status": "vacant_clean"})
        db.room_status_log.insert_one({"prop_id": 991, "room_label": "102", "status": "maintenance_requested"})
        db.booking_orders.insert_one(
            {
                "booking_id": "BK-MULTI-ROOM",
                "prop_id": 991,
                "guest_name": "Multi Room Guest",
                "check_in_date": FIXED_DATE,
                "check_out_date": "2026-08-16",
                "assigned_rooms": ["ROOM-991-1", "ROOM-991-2"],
                "status": "confirmed",
                "stay_status": "pending",
                "is_test": True,
            }
        )

        result = validate_room_availability("BK-MULTI-ROOM")

        assert result["all_available"] is False  # Room 102 is in maintenance
        assert len(result["rooms"]) == 2

        room_101 = next(r for r in result["rooms"] if r["room_label"] == "101")
        room_102 = next(r for r in result["rooms"] if r["room_label"] == "102")

        assert room_101["available"] is True
        assert room_102["available"] is False
        assert room_102["status"] == "maintenance_requested"
