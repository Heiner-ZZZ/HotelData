"""Tests for the per-hotel special-requests catalog and its booking-time validation.

Special requests ("Peticiones especiales") move from a hardcoded frontend list
to a per-hotel catalog (``hotel_content_pages.special_requests``) with unit
prices and behavior flags:

- ``pet_related`` → validated against the hotel's ``pets_allowed`` policy.
- ``late_arrival`` → informational (late check-in marker).
- ``chargeable`` with price > 0 → generates an additional charge at creation.

(La validación de ``high_floor`` contra el piso se eliminó 2026-08.)
Defaults (labels/prices/flags) exist in code; hotels override by label.
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
def seeded_hotel_with_requests(db):
    """Hotel with two rooms (floor 2 and floor 5), inventory, rates and a pet policy."""
    prop_id = 988
    db.dim_hotels.insert_one({
        "prop_id": prop_id,
        "hotel_name": "Requests Hotel",
        "display_name": "Requests Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-988-standard",
        "prop_id": prop_id,
        "name": "Standard",
        "base_capacity": 2,
        "max_adults": 2,
        "max_children": 1,
        "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": "HR-988-101",
        "room_label": "101",
        "room_type_id": "RT-988-standard",
        # floor como string — los datos reales mezclan int y string
        "floor": "2",
        "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": "HR-988-102",
        "room_label": "102",
        "room_type_id": "RT-988-standard",
        "floor": 5,
        "is_active": True,
    })
    for offset in range(0, 6):
        day = _days_from_today(offset)
        db.room_inventory_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-988-standard",
            "date": day,
            "total_rooms": 10,
            "available_rooms": 5,
            "is_available": True,
        })
        db.hotel_rate_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-988-standard",
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
        guest_name="Request Guest",
        guest_email="req@test.com",
        guest_phone="+1234567890",
        cedula="1234567890",
        room_type_id="RT-988-standard",
        hotel_room_id="HR-988-101",
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


class TestSpecialRequestsCatalog:
    def test_default_catalog_has_requests_with_prices_and_flags(self, db, seeded_hotel_with_requests):
        from src.app.modules.partner.services.content.special_requests import special_requests_payload_for_prop
        catalog = special_requests_payload_for_prop(seeded_hotel_with_requests)
        by_label = {item["label"]: item for item in catalog}
        assert "Cama extra" in by_label
        assert by_label["Cama extra"]["unit_price"] == 15.0
        assert by_label["Cama extra"]["chargeable"] is True
        assert by_label["Cuna para bebé"]["unit_price"] == 10.0
        assert by_label["Mascotas (Pet friendly)"]["pet_related"] is True
        assert by_label["Mascotas (Pet friendly)"]["chargeable"] is True
        assert by_label["Llegada tarde"]["late_arrival"] is True
        assert by_label["Accesibilidad"]["unit_price"] == 0.0
        # "Piso alto" ya no se ofrece (eliminado 2026-08).
        assert "Piso alto" not in by_label

    def test_hotel_override_replaces_price_and_flags(self, db, seeded_hotel_with_requests):
        db.hotel_content_pages.insert_one({
            "prop_id": seeded_hotel_with_requests,
            "special_requests": [
                {"label": "Cama extra", "unit_price": 25.0, "flags": ["chargeable"]},
                {"label": "Pet Sitter", "unit_price": 5.0, "flags": ["pet_related", "chargeable"]},
            ],
        })
        from src.app.modules.partner.services.content.special_requests import special_requests_payload_for_prop
        catalog = special_requests_payload_for_prop(seeded_hotel_with_requests)
        by_label = {item["label"]: item for item in catalog}
        # override wins on price
        assert by_label["Cama extra"]["unit_price"] == 25.0
        assert by_label["Cama extra"]["chargeable"] is True
        # custom request appears
        assert by_label["Pet Sitter"]["pet_related"] is True
        # unconfigured defaults still present
        assert "Cuna para bebé" in by_label
        assert by_label["Cuna para bebé"]["unit_price"] == 10.0


class TestPetRequestValidation:
    def test_pet_request_blocked_when_hotel_disallows_pets(self, db, seeded_hotel_with_requests):
        db.hotel_policies.update_one(
            {"prop_id": seeded_hotel_with_requests, "room_type_id": "", "rate_plan_id": ""},
            {"$set": {"pets_allowed": False, "pet_policy": "No se admiten mascotas."}},
        )
        with pytest.raises(ValueError, match="no admite mascotas"):
            create_booking(_booking_payload(
                seeded_hotel_with_requests, _days_from_today(1), _days_from_today(3),
                special_requests=["Mascotas (Pet friendly)"]))

    def test_pet_request_allowed_when_hotel_allows_pets(self, db, seeded_hotel_with_requests):
        result = create_booking(_booking_payload(
            seeded_hotel_with_requests, _days_from_today(1), _days_from_today(3),
            special_requests=["Mascotas (Pet friendly)"]))
        assert result["status"] == "pending"

    def test_unknown_request_label_is_ignored(self, db, seeded_hotel_with_requests):
        result = create_booking(_booking_payload(
            seeded_hotel_with_requests, _days_from_today(1), _days_from_today(3),
            special_requests=["Algo inexistente"]))
        assert result["status"] == "pending"


class TestSpecialRequestCharges:
    def test_priced_request_generates_charge(self, db, seeded_hotel_with_requests):
        result = create_booking(_booking_payload(
            seeded_hotel_with_requests, _days_from_today(1), _days_from_today(3),
            special_requests=["Cama extra"]))
        charge = db.additional_charges.find_one({
            "booking_id": result["booking_id"],
            "concept": {"$regex": "Cama extra"},
        })
        assert charge is not None
        assert charge["amount"] == 15.0

    def test_free_request_creates_no_charge(self, db, seeded_hotel_with_requests):
        result = create_booking(_booking_payload(
            seeded_hotel_with_requests, _days_from_today(1), _days_from_today(3),
            special_requests=["Llegada tarde"]))
        assert db.additional_charges.count_documents({"booking_id": result["booking_id"]}) == 0


class TestPreviewReportsSpecialRequestIssues:
    @pytest.mark.asyncio
    async def test_preview_reports_unavailable_for_pet_request_when_disallowed(self, db, seeded_hotel_with_requests):
        from src.app.modules.reservations.routes.reservations_impl import preview_reservation

        db.hotel_policies.update_one(
            {"prop_id": seeded_hotel_with_requests, "room_type_id": "", "rate_plan_id": ""},
            {"$set": {"pets_allowed": False}},
        )
        result = preview_reservation({
            "prop_id": seeded_hotel_with_requests,
            "guest_name": "Preview Guest",
            "guest_email": "preview@test.com",
            "guest_phone": "+1234567890",
            "cedula": "1234567890",
            "room_type_id": "RT-988-standard",
            "hotel_room_id": "HR-988-101",
            "check_in_date": _days_from_today(1),
            "check_out_date": _days_from_today(3),
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "adults": 2,
            "children": 0,
            "rooms": 1,
            "special_requests": ["Mascotas (Pet friendly)"],
        })
        assert result["available"] is False
        assert "no admite mascotas" in result["availability_message"]
