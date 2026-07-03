"""Tests for reservation creation with spec 007 gap fixes.

Covers:
- GAP-032: room_type_id stored in booking document
- GAP-033: guest_phone stored in booking and booking_guests
- GAP-034: total_price, currency, total_nights calculated from hotel_rate_calendar
- GAP-035: status is "pending" (not "requested")
- GAP-036: availability check in room_inventory_calendar
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pymongo import ASCENDING

from src.app.modules.reservations.service._helpers import (
    ReservationInput,
    generate_prefixed_id,
    utc_now,
)
from src.app.modules.reservations.service.lifecycle import (
    _check_availability,
    _calculate_total_price,
    create_booking,
)
from src.app.modules.reservations.service.validation import (
    validate_reservation_input,
    _valid_phone,
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
        total, currency, nights = _calculate_total_price(
            99999, "RT-99999-none", "2026-08-10", "2026-08-13", 1,
        )
        assert total is None
        assert currency == "USD"
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
        from src.app.modules.reservations.service.validation import build_reservation_input
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
        from src.app.modules.reservations.service._transitions import confirm_booking, reject_booking
        bid = self._create_test_booking()
        confirm_booking(bid)
        with pytest.raises(ValueError, match="Transición inválida|Confirmada"):
            reject_booking(bid)


# ---------------------------------------------------------------------------
# GAP-039: list_bookings with filters
# ---------------------------------------------------------------------------

class TestListBookingsFilters:
    def _create_bookings_in_states(self, db, seeded_hotel):
        from src.app.modules.reservations.service._transitions import confirm_booking, reject_booking
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
        from src.app.modules.reservations.service.queries import get_reservation_stats
        from src.app.modules.reservations.service._transitions import confirm_booking, reject_booking

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
        from src.app.modules.reservations.service._helpers import generate_prefixed_id, utc_now

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
