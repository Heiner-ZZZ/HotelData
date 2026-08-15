"""Tests for estimated arrival time and the late check-in marker.

A reservation can carry an optional ``estimated_arrival_time`` (HH:MM) chosen
by the guest at booking time. A booking is flagged ``late_checkin`` when:

- the guest selected a special request flagged ``late_arrival`` in the hotel
  catalog (default label "Llegada tarde"), or
- the estimated arrival time is at/after the late threshold (20:00).

Both fields are exposed in the operational check-ins list so reception can
spot late arrivals at a glance, and in the reception calendar.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._helpers import ReservationInput
from src.app.modules.reservations.service.lifecycle import create_booking
from src.app.modules.reservations.service._view_ops import list_check_ins
from src.app.modules.reservations.service.validation import validate_booking_form_requirements


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


@pytest.fixture
def seeded_hotel(db):
    """Hotel with one room, inventory, rates and a pet-allowing policy."""
    prop_id = 991
    db.dim_hotels.insert_one({
        "prop_id": prop_id,
        "hotel_name": "Arrival Hotel",
        "display_name": "Arrival Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-991-standard",
        "prop_id": prop_id,
        "name": "Standard",
        "base_capacity": 2,
        "max_adults": 2,
        "max_children": 1,
        "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": "HR-991-101",
        "room_label": "101",
        "room_type_id": "RT-991-standard",
        "floor": 2,
        "is_active": True,
    })
    for offset in range(0, 6):
        day = _days_from_today(offset)
        db.room_inventory_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-991-standard",
            "date": day,
            "total_rooms": 10,
            "available_rooms": 5,
            "is_available": True,
        })
        db.hotel_rate_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-991-standard",
            "date": day,
            "rate_amount": 150.0,
            "currency": "USD",
            "is_closed": False,
        })
    db.hotel_policies.insert_one({
        "prop_id": prop_id,
        "room_type_id": "",
        "rate_plan_id": "",
        "season_id": "",
        "pets_allowed": True,
        "pet_policy": "Mascotas permitidas con cargo.",
        "pet_fee": 20.0,
    })
    return prop_id


def _booking_payload(prop_id: int, check_in: str, check_out: str, **overrides) -> ReservationInput:
    base = dict(
        prop_id=prop_id,
        guest_name="Arrival Guest",
        guest_email="arrival@test.com",
        guest_phone="+1234567890",
        cedula="1234567890",
        room_type_id="RT-991-standard",
        hotel_room_id="HR-991-101",
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


class TestEstimatedArrivalStorage:
    def test_booking_stores_estimated_arrival_time(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="21:30"))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["estimated_arrival_time"] == "21:30"

    def test_booking_stores_empty_arrival_when_omitted(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3)))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["estimated_arrival_time"] == ""


class TestLateCheckinDerivation:
    def test_late_checkin_true_when_late_arrival_request_selected(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            special_requests=["Llegada tarde"]))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["late_checkin"] is True

    def test_late_checkin_true_when_arrival_at_threshold(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="20:00"))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["late_checkin"] is True

    def test_late_checkin_true_when_arrival_after_threshold(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="22:45"))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["late_checkin"] is True

    def test_late_checkin_false_for_early_arrival_without_request(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="18:00"))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["late_checkin"] is False

    def test_late_checkin_false_when_nothing_set(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3)))
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc["late_checkin"] is False


class TestOperationalExposure:
    def test_check_ins_list_exposes_arrival_and_late_marker(self, db, seeded_hotel):
        check_in = _days_from_today(1)
        result = create_booking(_booking_payload(
            seeded_hotel, check_in, _days_from_today(3),
            estimated_arrival_time="21:30"))
        view = list_check_ins(operation_date=check_in, prop_id=seeded_hotel)
        item = next(i for i in view["items"] if i["booking_id"] == result["booking_id"])
        assert item["estimated_arrival_time"] == "21:30"
        assert item["late_checkin"] is True

    def test_check_ins_list_defaults_false_when_not_late(self, db, seeded_hotel):
        check_in = _days_from_today(1)
        result = create_booking(_booking_payload(
            seeded_hotel, check_in, _days_from_today(3)))
        view = list_check_ins(operation_date=check_in, prop_id=seeded_hotel)
        item = next(i for i in view["items"] if i["booking_id"] == result["booking_id"])
        assert item["estimated_arrival_time"] == ""
        assert item["late_checkin"] is False

    def test_check_in_detail_exposes_arrival_and_late_marker(self, db, seeded_hotel):
        result = create_booking(_booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="22:10", special_requests=["Llegada tarde"]))
        from src.app.modules.reservations.service._checkin_detail import get_check_in_detail
        detail = get_check_in_detail(result["booking_id"])
        assert detail["estimated_arrival_time"] == "22:10"
        assert detail["late_checkin"] is True


class TestArrivalValidation:
    def test_validation_accepts_valid_hhmm(self, seeded_hotel):
        payload = _booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="19:45")
        errors = validate_booking_form_requirements(payload)
        assert "estimated_arrival_time" not in " ".join(errors).lower()

    def test_validation_rejects_bad_arrival_format(self, seeded_hotel):
        payload = _booking_payload(
            seeded_hotel, _days_from_today(1), _days_from_today(3),
            estimated_arrival_time="25:99")
        errors = validate_booking_form_requirements(payload)
        assert any("llegada" in e.lower() and "HH:MM" in e for e in errors)
