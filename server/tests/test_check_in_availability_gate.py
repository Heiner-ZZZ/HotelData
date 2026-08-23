"""Mandatory room-availability gate at check-in (2026-08).

``complete_check_in`` reuses ``validate_room_availability`` as a hard gate —
not just the informational ``GET /check-ins/{id}/room-availability`` endpoint.
Room status, overlapping reservations, and active maintenance work orders all
block the check-in before any state write.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service import complete_check_in


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_booking(db, booking_id: str) -> None:
    db.hotel_rooms.insert_one(
        {"hotel_room_id": "ROOM-991-1", "room_label": "101", "floor": "1", "room_type_id": "RT-991"}
    )
    db.room_status_log.insert_one({"prop_id": 991, "room_label": "101", "status": "vacant_clean"})
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "guest_name": "Gate Guest",
            "guest_email": "gate@test.com",
            "status": "confirmed",
            "check_in_date": _days_from_today(0),
            "check_out_date": _days_from_today(2),
            "total_nights": 2,
            "total_price": 200.0,
            "currency": "USD",
            "rooms": 1,
            "assigned_rooms": ["ROOM-991-1"],
            "is_test": True,
        }
    )


class TestCheckInRoomAvailabilityGate:
    def test_blocks_when_room_is_occupied(self, db) -> None:
        _seed_booking(db, "BK-GATE-OCC")
        db.room_status_log.update_one(
            {"prop_id": 991, "room_label": "101"},
            {"$set": {"status": "occupied_clean"}},
        )

        with pytest.raises(ValueError, match="no disponible"):
            complete_check_in("BK-GATE-OCC", changed_by="recep.prueba")

    def test_blocks_on_overlapping_reservation(self, db) -> None:
        _seed_booking(db, "BK-GATE-OVL")
        db.booking_orders.insert_one(
            {
                "booking_id": "BK-OTHER",
                "prop_id": 991,
                "guest_name": "Other Guest",
                "check_in_date": _days_from_today(1),
                "check_out_date": _days_from_today(3),
                "assigned_rooms": ["ROOM-991-1"],
                "status": "confirmed",
                "stay_status": "checked_in",
                "is_test": True,
            }
        )

        with pytest.raises(ValueError, match="ocupada"):
            complete_check_in("BK-GATE-OVL", changed_by="recep.prueba")

    def test_blocks_on_active_maintenance_task(self, db) -> None:
        _seed_booking(db, "BK-GATE-MT")
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

        with pytest.raises(ValueError, match="mantenimiento"):
            complete_check_in("BK-GATE-MT", changed_by="recep.prueba")

    def test_allows_when_room_is_available(self, db) -> None:
        _seed_booking(db, "BK-GATE-OK")

        result = complete_check_in("BK-GATE-OK", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"
