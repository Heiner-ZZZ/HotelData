"""Tests for the hotel-scoped Punto 1 operations overview."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.app.modules.financial_reconciliation.overview import build_operations_overview


def test_operations_overview_is_scoped_and_summarizes_connected_domains(db):
    db.dim_hotels.insert_one({"prop_id": 910, "display_name": "Hotel 910"})
    db.dim_hotels.insert_one({"prop_id": 911, "display_name": "Hotel 911"})
    db.room_status_log.insert_many([
        {"prop_id": 910, "status": "vacant_clean"},
        {"prop_id": 910, "status": "occupied_clean"},
        {"prop_id": 911, "status": "out_of_order"},
    ])
    db.guest_folios.insert_many([
        {"prop_id": 910, "status": "closed", "total_due": 12.5},
        {"prop_id": 911, "status": "closed", "total_due": 999},
    ])
    db.reservation_invoices.insert_one({
        "prop_id": 910, "status": "paid", "total": 100.0,
    })
    db.reservation_payments.insert_one({
        "prop_id": 910, "status": "confirmed", "amount": 40.0,
    })
    db.expense_invoices.insert_one({
        "prop_id": 910, "status": "approved", "total": 25.0,
    })
    db.maintenance_tasks.insert_one({
        "prop_id": 910, "status": "completed", "actual_cost": 15.0,
    })
    db.reception_shifts.insert_one({
        "prop_id": 910, "status": "open", "start_time": datetime.now(timezone.utc),
    })

    report = build_operations_overview(910)

    assert report["prop_id"] == 910
    assert report["hotel"]["name"] == "Hotel 910"
    assert report["occupancy"]["occupied_rooms"] == 1
    assert report["occupancy"]["available_rooms"] == 1
    assert report["revenue"]["room_revenue"] == 100.0
    assert report["revenue"]["payments_confirmed"] == 40.0
    assert report["expenses"]["approved"] == 25.0
    assert report["expenses"]["maintenance_cost"] == 15.0
    assert report["cash"]["open_shift_id"]
    assert report["revenue"]["outstanding_folio_balance"] == 12.5


def test_operations_overview_uses_latest_room_status_per_room(db):
    db.dim_hotels.insert_one({"prop_id": 912, "display_name": "Hotel 912"})
    now = datetime.now(timezone.utc)
    db.room_status_log.insert_many([
        {"prop_id": 912, "hotel_room_id": "ROOM-1", "status": "occupied_clean", "updated_at": now},
        {"prop_id": 912, "hotel_room_id": "ROOM-1", "status": "vacant_clean", "updated_at": now + timedelta(seconds=1)},
        {"prop_id": 912, "hotel_room_id": "ROOM-2", "status": "out_of_order", "updated_at": now},
    ])

    report = build_operations_overview(912)

    assert report["occupancy"]["total_tracked_rooms"] == 2
    assert report["occupancy"]["occupied_rooms"] == 0
    assert report["occupancy"]["available_rooms"] == 1
    assert report["occupancy"]["maintenance_rooms"] == 1
