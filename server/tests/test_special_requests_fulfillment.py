"""Tests for the special-request fulfillment checklist on bookings.

Every selected special request starts as ``pending`` when the booking is
created. Reception/housekeeping can flip each request to ``fulfilled`` (and
back) during the active stay; the status is stored on the booking document
(``special_request_fulfillment``) and normalized for legacy bookings that
predate the field.
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
def seeded_hotel(db):
    prop_id = 989
    db.dim_hotels.insert_one({
        "prop_id": prop_id, "hotel_name": "Fulfillment Hotel", "display_name": "Fulfillment Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-989-standard", "prop_id": prop_id, "name": "Standard",
        "base_capacity": 2, "max_adults": 2, "max_children": 1, "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id, "hotel_room_id": "HR-989-101", "room_label": "101",
        "room_type_id": "RT-989-standard", "floor": 5, "is_active": True,
    })
    for offset in range(0, 6):
        day = _days_from_today(offset)
        db.room_inventory_calendar.insert_one({
            "prop_id": prop_id, "room_type_id": "RT-989-standard", "date": day,
            "total_rooms": 10, "available_rooms": 5, "is_available": True,
        })
        db.hotel_rate_calendar.insert_one({
            "prop_id": prop_id, "room_type_id": "RT-989-standard", "date": day,
            "rate_amount": 150.0, "currency": "USD", "is_closed": False,
        })
    return prop_id


def _booking_payload(prop_id: int, **overrides) -> ReservationInput:
    base = dict(
        prop_id=prop_id,
        guest_name="Fulfillment Guest",
        guest_email="fulfillment@test.com",
        guest_phone="+1234567890",
        cedula="1234567890",
        room_type_id="RT-989-standard",
        hotel_room_id="HR-989-101",
        check_in_date=_days_from_today(1),
        check_out_date=_days_from_today(3),
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


def _fulfillment_for(db, booking_id: str) -> list[dict]:
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    return booking.get("special_request_fulfillment") or []


class TestFulfillmentSeededAtCreation:
    def test_creation_seeds_each_request_as_pending(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, special_requests=["Cama extra", "Mascotas (Pet friendly)"]))
        fulfillment = _fulfillment_for(db, result["booking_id"])
        by_label = {item["label"]: item["status"] for item in fulfillment}
        assert by_label == {"Cama extra": "pending", "Mascotas (Pet friendly)": "pending"}

    def test_creation_without_requests_seeds_empty(self, db, seeded_hotel):
        result = create_booking(_booking_payload(seeded_hotel))
        assert _fulfillment_for(db, result["booking_id"]) == []


class TestDetailNormalization:
    def test_detail_defaults_legacy_bookings_to_pending(self, db, seeded_hotel):
        """Bookings created before the field existed report pending for every request."""
        result = create_booking(_booking_payload(
            seeded_hotel, special_requests=["Cama extra"]))
        db.booking_orders.update_one(
            {"booking_id": result["booking_id"]},
            {"$unset": {"special_request_fulfillment": ""}},
        )
        from src.app.modules.reservations.service.queries import get_booking_detail
        detail = get_booking_detail(result["booking_id"])
        fulfillment = detail["special_request_fulfillment"]
        assert fulfillment == [{"label": "Cama extra", "status": "pending", "fulfilled_at": None}]


class TestUpdateFulfillment:
    def test_mark_request_fulfilled(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, special_requests=["Cama extra", "Cuna para bebé"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_special_request_fulfillment
        updated = update_special_request_fulfillment(result["booking_id"], "Cama extra", "fulfilled")
        by_label = {item["label"]: item["status"] for item in updated}
        assert by_label["Cama extra"] == "fulfilled"
        assert by_label["Cuna para bebé"] == "pending"
        # persisted
        persisted = _fulfillment_for(db, result["booking_id"])
        assert {item["label"]: item["status"] for item in persisted}["Cama extra"] == "fulfilled"

    def test_can_revert_to_pending(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, special_requests=["Cama extra"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_special_request_fulfillment
        update_special_request_fulfillment(result["booking_id"], "Cama extra", "fulfilled")
        updated = update_special_request_fulfillment(result["booking_id"], "Cama extra", "pending")
        assert {item["label"]: item["status"] for item in updated}["Cama extra"] == "pending"

    def test_unknown_request_rejected(self, db, seeded_hotel):
        result = create_booking(_booking_payload(seeded_hotel, special_requests=["Cama extra"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_special_request_fulfillment
        with pytest.raises(ValueError, match="no pertenece"):
            update_special_request_fulfillment(result["booking_id"], "Piso alto", "fulfilled")

    def test_invalid_status_rejected(self, db, seeded_hotel):
        result = create_booking(_booking_payload(seeded_hotel, special_requests=["Cama extra"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_special_request_fulfillment
        with pytest.raises(ValueError, match="Estado inválido"):
            update_special_request_fulfillment(result["booking_id"], "Cama extra", "halfway")

    def test_unknown_booking_rejected(self, db, seeded_hotel):
        from src.app.modules.reservations.service.special_request_fulfillment import update_special_request_fulfillment
        with pytest.raises(ValueError, match="no encontrada"):
            update_special_request_fulfillment("BK-NOPE", "Cama extra", "fulfilled")
