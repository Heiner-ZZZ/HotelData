"""Regressions for nightly room inventory consistency."""
from __future__ import annotations

import pytest

from src.app.modules.financial_reconciliation.service import build_reconciliation_report
from src.app.modules.reservations.service.lifecycle.create._availability import _check_availability
from src.app.modules.reservations.service._transitions._inventory import _deduct_inventory


def test_confirm_booking_does_not_transition_when_one_night_lacks_inventory(db):
    """A reservation cannot become confirmed while its nightly inventory is incomplete."""
    from src.app.modules.reservations.service._transitions import confirm_booking

    db.booking_orders.insert_one({
        "prop_id": 952,
        "booking_id": "BK-952-001",
        "room_type_id": "standard",
        "rooms": 1,
        "status": "pending",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-12",
        "total_price": 100.0,
    })
    db.room_inventory_calendar.insert_one({
        "prop_id": 952,
        "room_type_id": "standard",
        "date": "2026-08-10",
        "total_rooms": 1,
        "available_rooms": 1,
        "blocked_rooms": 0,
    })

    with pytest.raises(ValueError, match="inventario|Inventario|inventory|No hay datos"):
        confirm_booking("BK-952-001")

    assert db.booking_orders.find_one({"booking_id": "BK-952-001"})["status"] == "pending"
    assert db.booking_status_history.count_documents({
        "booking_id": "BK-952-001",
        "status": "confirmed",
    }) == 0


def test_reconciliation_reports_reservation_inventory_drift_per_night(db):
    """A hotel report must expose reservation/calendar drift, not just GL drift."""
    db.dim_hotels.insert_one({"prop_id": 951, "display_name": "Inventory Hotel"})
    db.room_types.insert_one({
        "prop_id": 951,
        "room_type_id": "standard",
        "name": "Standard",
        "is_active": True,
    })
    db.hotel_rooms.insert_one({
        "prop_id": 951,
        "hotel_room_id": "HR-951-101",
        "room_type_id": "standard",
        "room_label": "101",
        "is_active": True,
    })
    db.booking_orders.insert_one({
        "prop_id": 951,
        "booking_id": "BK-951-001",
        "room_type_id": "standard",
        "rooms": 1,
        "assigned_rooms": ["HR-951-101"],
        "status": "checked_in",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-11",
    })
    # Calendar says the room is still available while the reservation says it
    # is occupied: a deterministic per-night reconciliation finding.
    db.room_inventory_calendar.insert_one({
        "prop_id": 951,
        "room_type_id": "standard",
        "date": "2026-08-10",
        "total_rooms": 1,
        "available_rooms": 1,
        "blocked_rooms": 0,
    })

    report = build_reconciliation_report(951)

    finding = next(item for item in report["findings"] if item["domain"] == "inventory")
    assert finding["actual"]["date"] == "2026-08-10"
    assert finding["expected"]["occupied_rooms"] == 1
    assert finding["actual"]["occupied_rooms"] == 0
    assert finding["repair_policy"] == "manual"


def test_checked_out_reservations_do_not_appear_as_current_inventory_occupancy(db):
    """Reconciliation must release checked-out stays from current occupancy checks."""
    db.dim_hotels.insert_one({"prop_id": 948, "display_name": "Checkout Hotel"})
    db.hotel_rooms.insert_one({
        "prop_id": 948,
        "hotel_room_id": "HR-948-101",
        "room_type_id": "standard",
        "room_label": "101",
        "is_active": True,
    })
    db.booking_orders.insert_one({
        "prop_id": 948,
        "booking_id": "BK-948-001",
        "room_type_id": "standard",
        "rooms": 1,
        "assigned_rooms": ["HR-948-101"],
        "status": "confirmed",
        "stay_status": "checked_out",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-02",
    })
    db.room_inventory_calendar.insert_one({
        "prop_id": 948,
        "room_type_id": "standard",
        "date": "2026-08-01",
        "total_rooms": 1,
        "available_rooms": 1,
        "blocked_rooms": 0,
    })

    report = build_reconciliation_report(948)

    assert not any(item["domain"] == "inventory" for item in report["findings"])


def test_invalid_assigned_room_is_reported_without_inventing_inventory_drift(db):
    """A stale room FK is a room finding, not seven false nightly shortages."""
    db.dim_hotels.insert_one({"prop_id": 947, "display_name": "Room FK Hotel"})
    db.booking_orders.insert_one({
        "prop_id": 947,
        "booking_id": "BK-947-001",
        "room_type_id": "standard",
        "rooms": 1,
        "assigned_rooms": ["HR-947-MISSING"],
        "status": "confirmed",
        "stay_status": "confirmed",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-08",
    })

    report = build_reconciliation_report(947)

    assert any(item["domain"] == "room" for item in report["findings"])
    assert not any(item["domain"] == "inventory" for item in report["findings"])


def test_deleted_inventory_calendar_rows_are_not_sellable(db):
    """Soft-deleted calendar rows must not satisfy availability checks."""
    db.room_inventory_calendar.insert_one({
        "prop_id": 949,
        "room_type_id": "standard",
        "date": "2026-08-10",
        "total_rooms": 2,
        "available_rooms": 2,
        "blocked_rooms": 0,
        "is_deleted": True,
    })

    error = _check_availability(
        prop_id=949,
        check_in_date="2026-08-10",
        check_out_date="2026-08-11",
        rooms=1,
        room_type_id="standard",
    )

    assert error == (
        "No hay disponibilidad registrada para el 2026-08-10. Cargá el inventario "
        "de esa fecha o elegí otras fechas."
    )


def test_inventory_deduction_is_all_or_nothing_when_a_night_is_missing(db):
    """A failed multi-night reservation must not consume only its first nights."""
    db.room_inventory_calendar.insert_one({
        "prop_id": 950,
        "room_type_id": "standard",
        "date": "2026-08-10",
        "total_rooms": 2,
        "available_rooms": 2,
        "blocked_rooms": 0,
    })

    with pytest.raises(ValueError, match="No hay datos de inventario"):
        _deduct_inventory(
            prop_id=950,
            check_in_date="2026-08-10",
            check_out_date="2026-08-12",
            rooms=1,
            room_type_id="standard",
        )

    first_night = db.room_inventory_calendar.find_one({
        "prop_id": 950,
        "room_type_id": "standard",
        "date": "2026-08-10",
    })
    assert first_night["available_rooms"] == 2
