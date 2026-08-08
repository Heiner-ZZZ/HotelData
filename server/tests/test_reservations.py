"""Tests for reservation creation with spec 007 gap fixes.

Covers:
- GAP-032: room_type_id stored in booking document
- GAP-033: guest_phone stored in booking and booking_guests
- GAP-034: total_price, currency, total_nights calculated from hotel_rate_calendar
- GAP-035: status is "pending" (not "requested")
- GAP-036: availability check in room_inventory_calendar
"""
from __future__ import annotations

import pytest
from bson import ObjectId

from src.app.modules.reservations.service._helpers import (
    ReservationInput,
    generate_prefixed_id,
    utc_now,
)
from src.app.modules.reservations.service.lifecycle import (
    _calculate_total_price,
    _check_availability,
    create_booking,
)
from src.app.modules.reservations.service.queries import list_bookings
from src.app.modules.reservations.service.validation import (
    _valid_phone,
    build_reservation_input,
    validate_reservation_input,
)

# ---------------------------------------------------------------------------
# Fixtures: seed a minimal hotel + inventory + rate for tests that need DB
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_hotel(db):
    """Insert one hotel with a room type, inventory, and rate for 3 nights."""
    # dim_hotels entry
    db.dim_hotels.insert_one({
        "prop_id": 999,
        "hotel_name": "Test Hotel",
        "display_name": "Test Hotel",
        "prop_starrating": 4,
        "prop_review_score": 85,
        "prop_country_id": 840,
    })
    # room_type
    db.room_types.insert_one({
        "room_type_id": "RT-999-deluxe",
        "prop_id": 999,
        "name": "Deluxe Room",
        "base_capacity": 2,
        "max_adults": 2,
        "max_children": 1,
        "is_active": True,
    })
    # room_inventory_calendar: 3 dates, 5 rooms available each
    for day_offset in range(3):
        date_str = f"2026-08-{10 + day_offset:02d}"
        db.room_inventory_calendar.insert_one({
            "prop_id": 999,
            "room_type_id": "RT-999-deluxe",
            "date": date_str,
            "total_rooms": 10,
            "available_rooms": 5,
            "is_available": True,
        })
    # hotel_rate_calendar: 3 dates, $150/night each
    for day_offset in range(3):
        date_str = f"2026-08-{10 + day_offset:02d}"
        db.hotel_rate_calendar.insert_one({
            "prop_id": 999,
            "room_type_id": "RT-999-deluxe",
            "date": date_str,
            "rate_amount": 150.00,
            "currency": "USD",
            "is_closed": False,
        })
    return 999


@pytest.fixture
def seeded_hotel_no_inventory(db):
    """Hotel with room type but NO inventory records."""
    db.dim_hotels.insert_one({
        "prop_id": 998,
        "hotel_name": "No Inventory Hotel",
        "display_name": "No Inventory Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-998-standard",
        "prop_id": 998,
        "name": "Standard Room",
        "base_capacity": 2,
        "max_adults": 2,
        "max_children": 0,
        "is_active": True,
    })
    return 998


@pytest.fixture
def seeded_hotel_no_rates(db):
    """Hotel with room type + inventory but NO rates (no calendar, no rate plans).

    La disponibilidad pasa (hay inventario) pero ``_calculate_total_price``
    devuelve ``None`` — el caso exacto que la regla anti-sin-precio debe
    bloquear en la creación.
    """
    db.dim_hotels.insert_one({
        "prop_id": 991,
        "hotel_name": "No Rates Hotel",
        "display_name": "No Rates Hotel",
    })
    db.room_types.insert_one({
        "room_type_id": "RT-991-estandar",
        "prop_id": 991,
        "name": "Standard Room",
        "base_capacity": 2,
        "max_adults": 2,
        "max_children": 0,
        "is_active": True,
    })
    for day_offset in range(3):
        date_str = f"2026-08-{10 + day_offset:02d}"
        db.room_inventory_calendar.insert_one({
            "prop_id": 991,
            "room_type_id": "RT-991-estandar",
            "date": date_str,
            "total_rooms": 10,
            "available_rooms": 5,
            "is_available": True,
        })
    return 991


# ---------------------------------------------------------------------------
# booking_orders.user_id is a BSON ObjectId FK to users._id
# ---------------------------------------------------------------------------

class TestBookingUserIdObjectIdFk:
    """booking_orders.user_id must be stored as a BSON ObjectId (FK to
    users._id), matching the rest of the codebase (reviews, user_sessions,
    role_assignments, …). The client "mis reservas" filter queries by
    ObjectId (queries.py), so a string value would silently hide the
    booking from its owner.
    """

    def test_booking_stores_user_id_as_object_id(self, db, seeded_hotel):
        uid = ObjectId()
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="User Alice",
            guest_email="alice@test.com",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
            user_id=uid,
        )
        result = create_booking(payload)
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc is not None
        assert isinstance(doc.get("user_id"), ObjectId)
        assert doc["user_id"] == uid

    def test_client_list_bookings_filters_by_object_id(self, db, seeded_hotel):
        uid = ObjectId()
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Bob Owned",
            guest_email="bob@test.com",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="cliente",
            is_test=True,
            user_id=uid,
        )
        result = create_booking(payload)
        # Another user's booking must NOT appear
        create_booking(
            ReservationInput(
                prop_id=seeded_hotel,
                guest_name="Other User",
                guest_email="other@test.com",
                check_in_date="2026-08-10",
                check_out_date="2026-08-13",
                adults=1,
                children=0,
                rooms=1,
                comment="",
                source="cliente",
                is_test=True,
                user_id=ObjectId(),
            )
        )
        client_doc = {
            "_id": uid,
            "username": "cliente_test",
            "primary_role": "cliente",
        }
        page = list_bookings(user=client_doc)
        ids = [item["booking_id"] for item in page["items"]]
        assert result["booking_id"] in ids
        assert len(ids) == 1, f"Cliente debe ver solo sus reservas, vio: {ids}"

    def test_build_reservation_input_normalizes_user_id_to_object_id(self):
        uid = ObjectId()
        inp = build_reservation_input(
            {
                "user_id": str(uid),
                "prop_id": 999,
                "guest_name": "X",
                "guest_email": "x@test.com",
                "check_in_date": "2026-08-10",
                "check_out_date": "2026-08-13",
                "adults": 1,
                "children": 0,
                "rooms": 1,
            },
            source="cliente",
        )
        assert isinstance(inp.user_id, ObjectId)
        assert inp.user_id == uid

    @pytest.mark.asyncio
    async def test_api_route_stores_user_id_as_object_id(self, client, db, seeded_hotel, admin_user):
        """POST /api/reservations must persist user_id as a BSON ObjectId.

        Pins the route change (reservations.py no longer str()s the owner
        _id): a regression reintroducing the string coercion would pass all
        service-level tests but fail here.
        """
        from tests.conftest import login

        # The staff-only creation route 409-gates on an active cash shift.
        db.reception_shifts.delete_many({"prop_id": seeded_hotel})
        db.reception_shifts.insert_one(
            {
                "prop_id": seeded_hotel,
                "status": "open",
                "shift_type": "morning",
                "start_time": utc_now(),
                "transactions": [],
            }
        )
        lr = await client.post(
            "/api/auth/login",
            json={"identifier": admin_user["username"], "password": admin_user["password"]},
        )
        assert lr.status_code == 200, lr.text
        resp = await client.post(
            "/api/reservations",
            json={
                "prop_id": seeded_hotel,
                "guest_name": "Api Owner",
                "guest_email": "api@test.com",
                "guest_phone": "+1234567890",
                "cedula": "1234567890",
                "room_type_id": "RT-999-deluxe",
                "check_in_date": "2026-08-10",
                "check_out_date": "2026-08-13",
                "check_in_time": "15:00",
                "check_out_time": "12:00",
                "adults": 2,
                "children": 0,
                "rooms": 1,
                "comment": "",
                "is_test": True,
            },
        )
        assert resp.status_code == 201, resp.text
        doc = db.booking_orders.find_one({"booking_id": resp.json()["booking_id"]})
        assert doc is not None
        assert isinstance(doc.get("user_id"), ObjectId)
        # The owner must be the authenticated admin (server-controlled).
        assert doc["user_id"] == ObjectId(admin_user["user_id"])

    def test_guest_booking_without_user_id_stays_null(self, db, seeded_hotel):
        result = create_booking(
            ReservationInput(
                prop_id=seeded_hotel,
                guest_name="Guest",
                guest_email="guest@test.com",
                check_in_date="2026-08-10",
                check_out_date="2026-08-13",
                adults=1,
                children=0,
                rooms=1,
                comment="",
                source="web",
                is_test=True,
            )
        )
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc.get("user_id") is None


# ---------------------------------------------------------------------------
# GAP-035: status is "pending" not "requested"
# ---------------------------------------------------------------------------

class TestStatusIsPending:
    def test_create_booking_returns_pending_status(self, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Alice",
            guest_email="alice@test.com",
            guest_phone="+1234567890",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="Test booking",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        assert result["status"] == "pending", f"Expected 'pending', got '{result['status']}'"

    def test_booking_document_has_pending_status(self, db, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Bob",
            guest_email="bob@test.com",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc is not None
        assert doc["status"] == "pending", f"Expected 'pending', got '{doc['status']}'"

    def test_status_history_has_pending_status(self, db, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Carol",
            guest_email="carol@test.com",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        history = list(db.booking_status_history.find(
            {"booking_id": result["booking_id"]},
            {"_id": 0},
        ))
        assert len(history) >= 1
        assert history[0]["status"] == "pending", (
            f"Expected first history entry 'pending', got '{history[0]['status']}'"
        )


# ---------------------------------------------------------------------------
# GAP-032: room_type_id stored in booking
# ---------------------------------------------------------------------------

class TestRoomTypeId:
    def test_room_type_id_stored_in_booking(self, db, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Dave",
            guest_email="dave@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc is not None
        assert doc.get("room_type_id") == "RT-999-deluxe", (
            f"Expected room_type_id='RT-999-deluxe', got '{doc.get('room_type_id')}'"
        )

    def test_room_type_id_optional(self, db, seeded_hotel):
        """Without room_type_id, booking still creates (uses ANY room type)."""
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Eve",
            guest_email="eve@test.com",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc is not None
        assert doc.get("room_type_id") == "", (
            f"Expected empty room_type_id, got '{doc.get('room_type_id')}'"
        )


# ---------------------------------------------------------------------------
# GAP-033: guest_phone stored in booking and booking_guests
# ---------------------------------------------------------------------------

class TestGuestPhone:
    def test_guest_phone_stored_in_booking(self, db, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Frank",
            guest_email="frank@test.com",
            guest_phone="+1-555-123-4567",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc is not None
        assert doc.get("guest_phone") == "+1-555-123-4567"

    def test_guest_phone_stored_in_booking_guests(self, db, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Grace",
            guest_email="grace@test.com",
            guest_phone="+34 600 123 456",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        guest = db.booking_guests.find_one(
            {"booking_id": result["booking_id"], "is_primary": True},
        )
        assert guest is not None
        assert guest.get("guest_phone") == "+34 600 123 456"

    def test_phone_validation_accepts_valid(self):
        assert _valid_phone("") is True
        assert _valid_phone("+1234567890") is True
        assert _valid_phone("555-123-4567") is True
        assert _valid_phone("+1 (555) 123-4567") is True

    def test_phone_validation_rejects_invalid(self):
        assert _valid_phone("abc") is False
        assert _valid_phone("555-ABC-1234") is False
        assert _valid_phone("<script>") is False

    def test_validation_rejects_invalid_phone(self):
        payload = ReservationInput(
            prop_id=999,
            guest_name="Heidi",
            guest_email="heidi@test.com",
            guest_phone="not-a-phone!",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="test",
        )
        errors = validate_reservation_input(payload)
        phone_errors = [e for e in errors if "phone" in e.lower()]
        assert len(phone_errors) >= 1, f"Expected phone validation error, got {errors}"


# ---------------------------------------------------------------------------
# GAP-034: total_price, currency, total_nights calculated
# ---------------------------------------------------------------------------

class TestTotalPrice:
    def test_total_price_calculated_and_returned(self, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Ivan",
            guest_email="ivan@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        assert result.get("total_price") == 450.00, (
            f"Expected total_price=450.00 (3 nights x $150), got {result.get('total_price')}"
        )
        assert result.get("currency") == "USD"
        assert result.get("total_nights") == 3

    def test_total_price_scales_with_rooms(self, seeded_hotel):
        """2 rooms x 3 nights x $150 = $900."""
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Judy",
            guest_email="judy@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=2,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        assert result.get("total_price") == 900.00, (
            f"Expected total_price=900.00 (2 rooms x 3 nights x $150), got {result.get('total_price')}"
        )

    def test_total_price_stored_in_booking_document(self, db, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Karl",
            guest_email="karl@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        doc = db.booking_orders.find_one({"booking_id": result["booking_id"]})
        assert doc is not None
        assert doc.get("total_price") == 450.00
        assert doc.get("currency") == "USD"
        assert doc.get("total_nights") == 3

    def test_calculate_total_price_no_rates(self):
        """Hotel without rate records returns None."""
        total, currency, nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
            99999, "RT-99999-none", "2026-08-10", "2026-08-13", 1,
        )
        assert total is None
        assert currency == "USD"
        assert nights == 3

    def test_calculate_total_price_falls_back_to_rate_plan_base_rate(self, db):
        """Calendario vacío pero rate plan configurado → base_rate × noches.

        Es el caso que producía reservas SIN precio (emails con Total "—",
        penalizaciones $0, facturas $0): el hotel tiene tarifas en
        ``rate_plans`` pero el ``hotel_rate_calendar`` no cubre las fechas.
        El fallback usa la tarifa del propio hotel (autoritativa).
        """
        db.rate_plans.insert_one({
            "prop_id": 997, "rate_plan_id": "RP-997-flex",
            "name": "Flexible", "base_rate": 120.0,
        })
        total, currency, nights, *_ = _calculate_total_price(
            997, "RT-997-estandar", "2026-08-10", "2026-08-13", 1,
        )
        assert total == 360.0  # 3 noches × $120
        assert currency == "USD"
        assert nights == 3

    def test_calculate_total_price_fallback_scales_with_rooms(self, db):
        """2 habitaciones × 3 noches × $120 = $720."""
        db.rate_plans.insert_one({
            "prop_id": 996, "rate_plan_id": "RP-996-flex", "base_rate": 120.0,
        })
        total, *_ = _calculate_total_price(
            996, "RT-996-estandar", "2026-08-10", "2026-08-13", 2,
        )
        assert total == 720.0

    def test_calculate_total_price_fallback_prefers_explicit_rate_plan(self, db):
        """El rate plan que referencia la reserva manda sobre room-type/general."""
        db.rate_plans.insert_one({"prop_id": 995, "rate_plan_id": "RP-995-flex", "base_rate": 94.0})
        db.rate_plans.insert_one({
            "prop_id": 995, "rate_plan_id": "RP-995-advance",
            "room_type_id": "RT-995-doble", "base_rate": 200.0,
        })
        total, *_ = _calculate_total_price(
            995, "RT-995-doble", "2026-08-10", "2026-08-13", 1,
            rate_plan_id="RP-995-flex",
        )
        assert total == 94.0 * 3  # el plan explícito, no el del room type

    def test_calculate_total_price_fallback_uses_room_type_plan(self, db):
        """Sin rate plan explícito, usa el plan que matchea el room type."""
        db.rate_plans.insert_one({"prop_id": 994, "rate_plan_id": "RP-994-flex", "base_rate": 94.0})
        db.rate_plans.insert_one({
            "prop_id": 994, "rate_plan_id": "RP-994-doble",
            "room_type_id": "RT-994-doble", "base_rate": 150.0,
        })
        total, *_ = _calculate_total_price(
            994, "RT-994-doble", "2026-08-10", "2026-08-13", 1,
        )
        assert total == 150.0 * 3  # plan del room type, no el general

    def test_calculate_total_price_fallback_applies_extra_adult_occupancy(self, db):
        """El fallback respeta la ocupación del plan (extra_adult_price), igual
        que el path del calendario — 3 adultos en base_occupancy 2: 1 extra × $20."""
        db.rate_plans.insert_one({
            "prop_id": 992, "rate_plan_id": "RP-992-flex",
            "base_rate": 100.0, "base_occupancy": 2, "extra_adult_price": 20.0,
        })
        total, *_ = _calculate_total_price(
            992, "RT-992-doble", "2026-08-10", "2026-08-13", 1,
            adults=3,
        )
        assert total == 360.0  # (100 + 1×20) × 3 noches

    def test_calculate_total_price_fallback_still_none_without_any_rate_plan(self, db):
        """Sin calendario Y sin rate plans → None (contrato original intacto)."""
        total, currency, nights, *_ = _calculate_total_price(
            993, "RT-993-x", "2026-08-10", "2026-08-13", 1,
        )
        assert total is None
        assert nights == 3


# ---------------------------------------------------------------------------
# GAP-036: availability check
# ---------------------------------------------------------------------------

class TestAvailabilityCheck:
    def test_check_availability_allows_with_inventory(self, seeded_hotel):
        """seeded_hotel has 5 rooms for 3 dates."""
        result = _check_availability(seeded_hotel, "2026-08-10", "2026-08-13", 1, "RT-999-deluxe")
        assert result is None, f"Expected no error, got '{result}'"

    def test_check_availability_blocks_without_inventory(self, seeded_hotel_no_inventory):
        """Hotel 998 has room types but no inventory records."""
        result = _check_availability(seeded_hotel_no_inventory, "2026-08-10", "2026-08-13", 1, "RT-998-standard")
        assert result is not None, "Expected availability error, got None"
        assert "No" in result or "not" in result.lower(), (
            f"Expected error message, got '{result}'"
        )

    def test_check_availability_blocks_overbooking(self, seeded_hotel):
        """5 rooms available, requesting 10 should fail."""
        result = _check_availability(seeded_hotel, "2026-08-10", "2026-08-13", 10, "RT-999-deluxe")
        assert result is not None

    def test_create_booking_fails_without_availability(self, seeded_hotel):
        """With rooms=10 but only 5 available -> ValueError."""
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Laura",
            guest_email="laura@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=10,  # only 5 available
            comment="",
            source="test",
            is_test=True,
        )
        with pytest.raises(ValueError, match="availability|Cannot create"):
            create_booking(payload)

    def test_create_booking_allows_with_availability(self, seeded_hotel):
        payload = ReservationInput(
            prop_id=seeded_hotel,
            guest_name="Mallory",
            guest_email="mallory@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,  # within 5 available
            comment="",
            source="test",
            is_test=True,
        )
        result = create_booking(payload)
        assert result["status"] == "pending"

    def test_check_availability_invalid_dates(self):
        result = _check_availability(999, "not-a-date", "2026-08-13", 1)
        assert result is not None
        assert "Invalid date" in result

    def test_check_availability_without_room_type_finds_any(self, seeded_hotel):
        """Without room_type_id, finds ANY room type with availability."""
        result = _check_availability(seeded_hotel, "2026-08-10", "2026-08-13", 1)
        assert result is None, f"Expected no error (any room type works), got '{result}'"


# ---------------------------------------------------------------------------
# Build reservation input extracts new fields
# ---------------------------------------------------------------------------

class TestBuildReservationInput:
    def test_extracts_guest_phone_and_room_type_id(self):
        from src.app.modules.reservations.service.validation import (
            build_reservation_input,
        )
        result = build_reservation_input({
            "prop_id": "999",
            "guest_name": "  Niels  ",
            "guest_email": "NIELS@TEST.COM",
            "guest_phone": "  +52 555 123 4567  ",
            "room_type_id": "  RT-999-suite  ",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-13",
            "adults": "2",
            "rooms": "1",
        }, source="test")
        assert result.guest_phone == "+52 555 123 4567", (
            f"Expected stripped phone, got '{result.guest_phone}'"
        )
        assert result.room_type_id == "RT-999-suite", (
            f"Expected stripped room_type_id, got '{result.room_type_id}'"
        )


# ---------------------------------------------------------------------------
# GAP-037/038: confirm and reject booking
# ---------------------------------------------------------------------------

class TestConfirmReject:
    def _create_test_booking(self, prop_id=999):
        payload = ReservationInput(
            prop_id=prop_id,
            guest_name="Test",
            guest_email="test@test.com",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        return create_booking(payload)["booking_id"]

    def test_confirm_booking_success(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import confirm_booking
        bid = self._create_test_booking()
        result = confirm_booking(bid, changed_by="test")
        assert result["status"] == "confirmed"
        doc = db.booking_orders.find_one({"booking_id": bid})
        assert doc["status"] == "confirmed"

    def test_confirm_booking_history_logged(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import confirm_booking
        bid = self._create_test_booking()
        confirm_booking(bid, changed_by="staff")
        history = list(db.booking_status_history.find(
            {"booking_id": bid, "status": "confirmed"}
        ))
        assert len(history) == 1
        assert history[0]["changed_by"] == "staff"

    def test_confirm_already_confirmed_raises_error(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import confirm_booking
        bid = self._create_test_booking()
        confirm_booking(bid)
        with pytest.raises(ValueError, match="Transición inválida|Confirmada"):
            confirm_booking(bid)

    def test_reject_booking_success(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import reject_booking
        bid = self._create_test_booking()
        result = reject_booking(bid, reason="overbooked", changed_by="test")
        assert result["status"] == "rejected"
        doc = db.booking_orders.find_one({"booking_id": bid})
        assert doc["status"] == "rejected"

    def test_reject_booking_history_logged(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import reject_booking
        bid = self._create_test_booking()
        reject_booking(bid, reason="overbooked", changed_by="staff")
        history = list(db.booking_status_history.find(
            {"booking_id": bid, "status": "rejected"}
        ))
        assert len(history) == 1
        assert history[0]["reason"] == "overbooked"

    def test_reject_non_pending_raises_error(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import (
            confirm_booking,
            reject_booking,
        )
        bid = self._create_test_booking()
        confirm_booking(bid)
        with pytest.raises(ValueError, match="Transición inválida|Confirmada"):
            reject_booking(bid)


# ---------------------------------------------------------------------------
# GAP-039: list_bookings with filters
# ---------------------------------------------------------------------------

class TestListBookingsFilters:
    def _create_bookings_in_states(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import (
            confirm_booking,
            reject_booking,
        )
        bids = {}
        for i, name in enumerate(["Alpha", "Beta", "Gamma"]):
            payload = ReservationInput(
                prop_id=seeded_hotel,
                guest_name=name,
                guest_email=f"{name.lower()}@test.com",
                check_in_date="2026-08-10",
                check_out_date="2026-08-13",
                adults=1,
                children=0,
                rooms=1,
                comment="",
                source="test",
                is_test=True,
            )
            bid = create_booking(payload)["booking_id"]
            bids[name] = bid
        confirm_booking(bids["Beta"], changed_by="test")
        reject_booking(bids["Gamma"], reason="no_rooms", changed_by="test")
        return bids

    def test_filter_by_status(self, db, seeded_hotel):
        from src.app.modules.reservations.service.queries import list_bookings
        self._create_bookings_in_states(db, seeded_hotel)
        pending = list_bookings(status="pending", page_size=50)
        assert pending["total"] == 1, f"Expected 1 pending, got {pending['total']}"
        confirmed = list_bookings(status="confirmed", page_size=50)
        assert confirmed["total"] == 1
        rejected = list_bookings(status="rejected", page_size=50)
        assert rejected["total"] == 1

    def test_filter_by_prop_id(self, db, seeded_hotel):
        from src.app.modules.reservations.service.queries import list_bookings
        self._create_bookings_in_states(db, seeded_hotel)
        result = list_bookings(prop_id=seeded_hotel, page_size=50)
        assert result["total"] == 3
        result_none = list_bookings(prop_id=1, page_size=50)
        assert result_none["total"] == 0

    def test_filter_by_guest_name(self, db, seeded_hotel):
        from src.app.modules.reservations.service.queries import list_bookings
        self._create_bookings_in_states(db, seeded_hotel)
        result = list_bookings(guest_name="Alpha", page_size=50)
        assert result["total"] == 1
        # Case-insensitive
        result_ci = list_bookings(guest_name="alpha", page_size=50)
        assert result_ci["total"] == 1


# ---------------------------------------------------------------------------
# GAP-040: get_reservation_stats
# ---------------------------------------------------------------------------

class TestReservationStats:
    def test_stats_returns_all_statuses(self, db, seeded_hotel):
        from src.app.modules.reservations.service.queries import get_reservation_stats
        stats = get_reservation_stats()
        for s in ("pending", "confirmed", "cancelled", "rejected", "checked_in", "checked_out"):
            assert s in stats, f"Missing status '{s}' in stats"
        assert stats["total"] == 0
        assert stats["active"] == 0
        assert stats["completed"] == 0
        assert stats["lost"] == 0

    def test_stats_counts_correctly(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import (
            confirm_booking,
            reject_booking,
        )
        from src.app.modules.reservations.service.queries import get_reservation_stats

        # Create 1 pending, confirm 1, reject 1
        for name in ["A", "B", "C"]:
            payload = ReservationInput(
                prop_id=seeded_hotel,
                guest_name=name,
                guest_email=f"{name}@test.com",
                check_in_date="2026-08-10",
                check_out_date="2026-08-13",
                adults=1,
                children=0,
                rooms=1,
                comment="",
                source="test",
                is_test=True,
            )
            bid = create_booking(payload)["booking_id"]
            if name == "B":
                confirm_booking(bid, changed_by="test")
            elif name == "C":
                reject_booking(bid, reason="test", changed_by="test")

        stats = get_reservation_stats()
        assert stats["pending"] == 1
        assert stats["confirmed"] == 1
        assert stats["rejected"] == 1
        assert stats["cancelled"] == 0
        assert stats["total"] == 3
        assert stats["active"] == 2  # pending(1) + confirmed(1) = 2
        assert stats["lost"] == 1  # rejected(1)


# ---------------------------------------------------------------------------
# GAP-046: Auto-create invoice on check-in
# ---------------------------------------------------------------------------

class TestAutoInvoiceOnCheckIn:
    def _create_booking_for_checkin(self) -> str:
        """Create a real (non-test) booking with the seeded_hotel data."""
        payload = ReservationInput(
            prop_id=999,
            guest_name="Checkin Guest",
            guest_email="checkin@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=False,
        )
        return create_booking(payload)["booking_id"]

    def test_check_in_creates_invoice(self, db, seeded_hotel):
        """Non-test booking should get an invoice auto-created at check-in."""
        from src.app.modules.reservations.service._checkinout import complete_check_in

        bid = self._create_booking_for_checkin()
        result = complete_check_in(bid, changed_by="test")

        assert result["stay_status"] == "checked_in"
        assert result["invoice_id"] is not None, "Expected an invoice_id on check-in"

        # Verify invoice exists in DB
        from bson import ObjectId
        invoice = db.reservation_invoices.find_one({"_id": ObjectId(result["invoice_id"])})
        assert invoice is not None, "Invoice document should exist"
        assert invoice["booking_id"] == bid
        assert invoice["status"] == "issued"
        assert invoice["invoice_number"].startswith("INV-")

    def test_check_in_invoice_amounts(self, db, seeded_hotel):
        """Invoice subtotal = total_price ($450), taxes = 10% ($45), total = $495."""
        from src.app.modules.reservations.service._checkinout import complete_check_in

        bid = self._create_booking_for_checkin()
        result = complete_check_in(bid, changed_by="test")

        from bson import ObjectId
        invoice = db.reservation_invoices.find_one({"_id": ObjectId(result["invoice_id"])})
        assert invoice["subtotal"] == 450.00
        assert invoice["taxes"] == 45.00
        assert invoice["total"] == 495.00

    def test_check_in_skips_invoice_for_test_booking(self, db, seeded_hotel):
        """Test bookings should NOT create an invoice."""
        from src.app.modules.reservations.service._checkinout import complete_check_in

        payload = ReservationInput(
            prop_id=999,
            guest_name="Test Guest",
            guest_email="test@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="test",
            is_test=True,
        )
        bid = create_booking(payload)["booking_id"]
        result = complete_check_in(bid, changed_by="test")

        assert result["stay_status"] == "checked_in"
        assert result["invoice_id"] is None, "Test bookings should not create invoices"

    def test_check_in_without_price_skips_invoice(self, db, seeded_hotel):
        """Booking without price data should skip invoice creation.

        This edge case (booking exists but total_price is None/missing)
        can't happen through create_booking() — the normal flow always
        calculates a price. We directly insert the document to test the
        guard clause in complete_check_in().
        """
        from src.app.modules.reservations.service._checkinout import complete_check_in

        bid = generate_prefixed_id("BK")
        db.booking_orders.insert_one({
            "booking_id": bid,
            "prop_id": seeded_hotel,
            "status": "pending",
            "guest_name": "No Price",
            "guest_email": "noprice@test.com",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-13",
            "adults": 1,
            "children": 0,
            "rooms": 1,
            "total_price": None,
            "created_at": utc_now(),
        })
        result = complete_check_in(bid, changed_by="test")

        assert result["stay_status"] == "checked_in"
        assert result["invoice_id"] is None, "No invoice when booking has no price"

    def test_check_in_never_links_non_positive_invoice(self, db, seeded_hotel):
        """Check-in nunca debe vincular una factura en $0 o negativa (guarda
        extendida al path de check-in).

        Escenario (contrive pero pin el invariante): una reserva con precio
        real ($450) pero line_items que la anulan (descuento/crédito de -$500)
        hacía que ``create_invoice`` computara un total no-positivo. La guarda
        anterior solo rechazaba ``line_items`` vacíos, así que el check-in
        persistía la factura a -$5. El check-in debe completarse (folio,
        habitaciones, etc.) pero SIN factura.
        """
        from src.app.modules.reservations.service._checkinout import complete_check_in

        bid = self._create_booking_for_checkin()  # total_price = 450 (3 noches × $150)
        # Crédito que cancela el subtotal + taxes (450 + 45 - 500 = -5).
        db.booking_orders.update_one(
            {"booking_id": bid},
            {"$set": {"line_items": [{"item_id": "neg1", "name": "Ajuste", "total": -500.0}]}},
        )
        result = complete_check_in(bid, changed_by="test")

        assert result["stay_status"] == "checked_in"
        assert result["invoice_id"] is None, "No se debe vincular una factura no-positiva"
        assert db.reservation_invoices.count_documents({"booking_id": bid}) == 0
        assert db.fact_reservation_invoices.count_documents({"booking_id": bid}) == 0

    def test_check_in_reuses_existing_invoice_without_duplicating(self, db, seeded_hotel):
        """La rama de recuperación vincula la factura existente (incluso una
        legacy en $0) sin crear una segunda — el invariante anti-$0 rige la
        CREACIÓN, no la recuperación (decisión documentada en ``_checkin.py``;
        las legacy en $0 las corrige el backfill de facturas).
        """
        from bson import ObjectId
        from src.app.modules.reservations.service._checkinout import complete_check_in

        bid = self._create_booking_for_checkin()  # total_price = 450
        legacy_id = db.reservation_invoices.insert_one({
            "booking_id": bid,
            "invoice_number": "INV-LEGACY-0",
            "status": "issued",
            "subtotal": 0.0, "taxes": 0.0, "total": 0.0,
        }).inserted_id
        result = complete_check_in(bid, changed_by="test")

        assert result["stay_status"] == "checked_in"
        assert result["invoice_id"] == str(legacy_id), (
            "Debe reusarse la factura existente, no crearse una duplicada"
        )
        assert db.reservation_invoices.count_documents({"booking_id": bid}) == 1
        # El mirror de la factura legacy también debe existir en la colección
        # fact (la semilla del test no lo crea, pero el check-in no debe
        # fabricar un segundo documento).
        assert db.fact_reservation_invoices.count_documents({"booking_id": bid}) == 0


# ---------------------------------------------------------------------------
# Regla anti-sin-precio: una reserva NUNCA se guarda sin total_price
# ---------------------------------------------------------------------------

class TestNoPriceGuard:
    """Ningún canal de creación (motor web, reserva física/recepción) puede
    persistir una reserva sin ``total_price``.

    Antes, un hotel sin tarifas (ni calendario ni rate plans) creaba la
    reserva con ``total_price=None`` — lo que rompía los emails con Total
    "—", las penalizaciones $0 y las facturas en $0 (ver el backfill de
    precios). La regla: ``_calculate_total_price`` devuelve ``None`` solo en
    ese caso, y ahora la creación falla con un error claro y NO persiste nada.
    """

    def _payload(self, **overrides) -> ReservationInput:
        base = dict(
            prop_id=991,
            guest_name="Sin Tarifa",
            guest_email="norate@test.com",
            room_type_id="RT-991-estandar",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=1,
            children=0,
            rooms=1,
            comment="",
            source="web",
            is_test=True,
        )
        base.update(overrides)
        return ReservationInput(**base)

    def test_create_booking_blocks_without_total_price(self, db, seeded_hotel_no_rates):
        """Service: hotel sin tarifas → ValueError y nada persistido."""
        with pytest.raises(ValueError, match="precio"):
            create_booking(self._payload(prop_id=seeded_hotel_no_rates))
        assert db.booking_orders.count_documents({"prop_id": seeded_hotel_no_rates}) == 0
        assert db.booking_guests.count_documents({"booking_id": {"$regex": "^BK-"}}) == 0
        assert db.booking_status_history.count_documents({"status": "pending"}) == 0

    @pytest.mark.asyncio
    async def test_api_web_booking_blocks_without_total_price(
        self, client, db, seeded_hotel_no_rates, admin_user
    ):
        """Motor web (POST /api/reservations): 400 con mensaje claro, nada guardado."""
        from tests.conftest import login

        pid = seeded_hotel_no_rates
        db.reception_shifts.delete_many({"prop_id": pid})
        db.reception_shifts.insert_one({
            "prop_id": pid, "status": "open", "shift_type": "morning",
            "start_time": utc_now(), "transactions": [],
        })
        lr = await client.post(
            "/api/auth/login",
            json={"identifier": admin_user["username"], "password": admin_user["password"]},
        )
        assert lr.status_code == 200, lr.text

        resp = await client.post("/api/reservations", json={
            "prop_id": pid,
            "guest_name": "Web Sin Precio",
            "guest_email": "webnoprice@test.com",
            "guest_phone": "+1234567890",
            "cedula": "1234567890",
            "room_type_id": "RT-991-estandar",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-13",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "adults": 2, "children": 0, "rooms": 1,
            "comment": "", "is_test": True,
        })
        assert resp.status_code == 400, resp.text
        assert "precio" in resp.json()["detail"].lower()
        assert db.booking_orders.count_documents({"prop_id": pid}) == 0
        assert db.booking_status_history.count_documents({"status": "pending"}) == 0

    @pytest.mark.asyncio
    async def test_api_manual_reservation_blocks_without_total_price(
        self, client, db, seeded_hotel_no_rates, admin_user
    ):
        """Reserva física (POST /api/management/manual-reservations): 400, nada guardado."""
        from tests.conftest import login

        pid = seeded_hotel_no_rates
        db.reception_shifts.delete_many({"prop_id": pid})
        db.reception_shifts.insert_one({
            "prop_id": pid, "status": "open", "shift_type": "morning",
            "start_time": utc_now(), "transactions": [],
        })
        lr = await client.post(
            "/api/auth/login",
            json={"identifier": admin_user["username"], "password": admin_user["password"]},
        )
        assert lr.status_code == 200, lr.text

        resp = await client.post("/api/management/manual-reservations", json={
            "prop_id": pid,
            "room_type_id": "RT-991-estandar",
            "guest_name": "Fisica Sin Precio",
            "guest_email": "fisicanoprice@test.com",
            "guest_phone": "+1234567890",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-13",
            "adults": 1, "children": 0, "rooms": 1,
            "comment": "",
        })
        assert resp.status_code == 400, resp.text
        assert "precio" in resp.json()["detail"].lower()
        assert db.booking_orders.count_documents({"prop_id": pid}) == 0
        assert db.manual_reservations.count_documents({}) == 0
        assert db.booking_status_history.count_documents({"status": "confirmed"}) == 0

    def test_modify_booking_blocks_without_total_price(self, db, seeded_hotel):
        """Modificar a fechas sin tarifas no puede dejar la reserva sin precio:
        falla y conserva el total_price original."""
        from src.app.modules.reservations.service.lifecycle import modify_booking

        bid = create_booking(ReservationInput(
            prop_id=999,
            guest_name="Modify",
            guest_email="modify@test.com",
            room_type_id="RT-999-deluxe",
            check_in_date="2026-08-10",
            check_out_date="2026-08-13",
            adults=2, children=0, rooms=1,
            comment="", source="test", is_test=True,
        ))["booking_id"]
        # Quitar las tarifas y dar inventario en las fechas nuevas (09-20..22)
        # para que la única razón de fallo sea el precio.
        db.hotel_rate_calendar.delete_many({"prop_id": 999})
        for day_offset in range(3):
            date_str = f"2026-09-{20 + day_offset:02d}"
            db.room_inventory_calendar.insert_one({
                "prop_id": 999,
                "room_type_id": "RT-999-deluxe",
                "date": date_str,
                "total_rooms": 10,
                "available_rooms": 5,
                "is_available": True,
            })

        with pytest.raises(ValueError, match="precio"):
            modify_booking(bid, check_in_date="2026-09-20", check_out_date="2026-09-23")

        doc = db.booking_orders.find_one({"booking_id": bid})
        assert doc["total_price"] == 450.00, "El precio original debe conservarse"
