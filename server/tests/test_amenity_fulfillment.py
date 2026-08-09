"""Tests for the amenity fulfillment checklist on bookings.

Every selected amenity starts as ``pending`` when the booking is created.
Reception/housekeeping can flip each amenity to ``fulfilled`` (and back)
during the active stay; the status is stored on the booking document
(``amenity_fulfillment``) together with the fulfillment timestamp
(``fulfilled_at``), mirroring the special-request checklist.
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
    prop_id = 988
    db.dim_hotels.insert_one({
        "prop_id": prop_id, "hotel_name": "Amenity Fulfillment Hotel", "display_name": "Amenity Fulfillment Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-988-standard", "prop_id": prop_id, "name": "Standard",
        "base_capacity": 2, "max_adults": 2, "max_children": 1, "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id, "hotel_room_id": "HR-988-101", "room_label": "101",
        "room_type_id": "RT-988-standard", "floor": 5, "is_active": True,
    })
    for offset in range(0, 6):
        day = _days_from_today(offset)
        db.room_inventory_calendar.insert_one({
            "prop_id": prop_id, "room_type_id": "RT-988-standard", "date": day,
            "total_rooms": 10, "available_rooms": 5, "is_available": True,
        })
        db.hotel_rate_calendar.insert_one({
            "prop_id": prop_id, "room_type_id": "RT-988-standard", "date": day,
            "rate_amount": 150.0, "currency": "USD", "is_closed": False,
        })
    return prop_id


def _booking_payload(prop_id: int, **overrides) -> ReservationInput:
    base = dict(
        prop_id=prop_id,
        guest_name="Amenity Guest",
        guest_email="amenity@test.com",
        guest_phone="+1234567890",
        cedula="1234567890",
        room_type_id="RT-988-standard",
        hotel_room_id="HR-988-101",
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
    return booking.get("amenity_fulfillment") or []


class TestAmenityFulfillmentSeededAtCreation:
    def test_creation_seeds_each_selected_amenity_as_pending(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, selected_amenities=["Wi-Fi", "Desayuno incluido"]))
        fulfillment = _fulfillment_for(db, result["booking_id"])
        by_label = {item["label"]: item["status"] for item in fulfillment}
        assert by_label == {"Wi-Fi": "pending", "Desayuno incluido": "pending"}
        # pending entries carry no fulfillment date yet
        assert all(item.get("fulfilled_at") is None for item in fulfillment)

    def test_creation_without_amenities_seeds_empty(self, db, seeded_hotel):
        result = create_booking(_booking_payload(seeded_hotel))
        assert _fulfillment_for(db, result["booking_id"]) == []


class TestDetailNormalization:
    def test_detail_defaults_legacy_bookings_to_pending(self, db, seeded_hotel):
        """Bookings created before the field existed report pending for every amenity."""
        result = create_booking(_booking_payload(
            seeded_hotel, selected_amenities=["Wi-Fi"]))
        db.booking_orders.update_one(
            {"booking_id": result["booking_id"]},
            {"$unset": {"amenity_fulfillment": ""}},
        )
        from src.app.modules.reservations.service.queries import get_booking_detail
        detail = get_booking_detail(result["booking_id"])
        fulfillment = detail["amenity_fulfillment"]
        assert fulfillment == [{"label": "Wi-Fi", "status": "pending", "fulfilled_at": None}]


class TestUpdateAmenityFulfillment:
    def test_mark_amenity_fulfilled_stores_fulfilled_at(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, selected_amenities=["Wi-Fi", "Piscina"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_amenity_fulfillment
        updated = update_amenity_fulfillment(result["booking_id"], "Wi-Fi", "fulfilled")
        by_label = {item["label"]: item["status"] for item in updated}
        assert by_label["Wi-Fi"] == "fulfilled"
        assert by_label["Piscina"] == "pending"
        # fulfilled entry records the date
        wi_fi = next(item for item in updated if item["label"] == "Wi-Fi")
        assert wi_fi["fulfilled_at"] is not None
        # persisted
        persisted = _fulfillment_for(db, result["booking_id"])
        stored = next(item for item in persisted if item["label"] == "Wi-Fi")
        assert stored["status"] == "fulfilled"
        assert stored["fulfilled_at"] is not None

    def test_revert_to_pending_clears_fulfilled_at(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, selected_amenities=["Wi-Fi"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_amenity_fulfillment
        update_amenity_fulfillment(result["booking_id"], "Wi-Fi", "fulfilled")
        updated = update_amenity_fulfillment(result["booking_id"], "Wi-Fi", "pending")
        wi_fi = next(item for item in updated if item["label"] == "Wi-Fi")
        assert wi_fi["status"] == "pending"
        assert wi_fi["fulfilled_at"] is None

    def test_special_request_fulfillment_also_stores_fulfilled_at(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, special_requests=["Cama extra"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_special_request_fulfillment
        updated = update_special_request_fulfillment(result["booking_id"], "Cama extra", "fulfilled")
        cama = next(item for item in updated if item["label"] == "Cama extra")
        assert cama["status"] == "fulfilled"
        assert cama["fulfilled_at"] is not None

    def test_unknown_amenity_rejected(self, db, seeded_hotel):
        result = create_booking(_booking_payload(seeded_hotel, selected_amenities=["Wi-Fi"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_amenity_fulfillment
        with pytest.raises(ValueError, match="no pertenece"):
            update_amenity_fulfillment(result["booking_id"], "Piscina", "fulfilled")

    def test_invalid_status_rejected(self, db, seeded_hotel):
        result = create_booking(_booking_payload(seeded_hotel, selected_amenities=["Wi-Fi"]))
        from src.app.modules.reservations.service.special_request_fulfillment import update_amenity_fulfillment
        with pytest.raises(ValueError, match="Estado inválido"):
            update_amenity_fulfillment(result["booking_id"], "Wi-Fi", "halfway")

    def test_unknown_booking_rejected(self, db, seeded_hotel):
        from src.app.modules.reservations.service.special_request_fulfillment import update_amenity_fulfillment
        with pytest.raises(ValueError, match="no encontrada"):
            update_amenity_fulfillment("BK-NOPE", "Wi-Fi", "fulfilled")
