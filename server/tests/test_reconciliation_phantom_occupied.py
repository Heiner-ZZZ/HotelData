"""Reconciliation for room_status_log entries marked occupied without an active stay."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.financial_reconciliation.service import build_reconciliation_report
from src.app.modules.financial_reconciliation.repairs import repair_phantom_occupied_rooms

pytestmark = pytest.mark.asyncio


def _seed_hotel(db, prop_id: int, name: str = "Phantom Hotel") -> None:
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": name})


def _seed_room(db, prop_id: int, label: str, status: str, note: str = "") -> None:
    db.hotel_rooms.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": f"HR-{prop_id}-{label}",
        "room_type_id": "standard",
        "room_label": label,
        "is_active": True,
    })
    db.room_status_log.insert_one({
        "prop_id": prop_id,
        "hotel_room_id": f"HR-{prop_id}-{label}",
        "room_type_id": "standard",
        "room_label": label,
        "status": status,
        "note": note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def _today_range() -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=1)).isoformat(), (today + timedelta(days=1)).isoformat()


async def test_report_flags_occupied_clean_without_active_stay(db):
    """A room marked occupied_clean with no checked-in stay is a reconciliation finding."""
    _seed_hotel(db, 703)
    _seed_room(db, 703, "101", "occupied_clean", note="Auto-asignada desde reserva BK-X")

    report = build_reconciliation_report(703)

    findings = [f for f in report["findings"] if f["domain"] == "room_status"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding["severity"] == "warning"
    assert finding["repair_policy"] == "idempotent_migration"
    assert "101" in finding["source_ids"]
    assert finding["actual"]["status"] == "occupied_clean"
    assert finding["actual"]["active_stay"] is False


async def test_report_does_not_flag_room_with_active_checked_in_stay(db):
    """A room occupied by a currently checked-in stay must not be flagged."""
    _seed_hotel(db, 704)
    _seed_room(db, 704, "101", "occupied_clean", note="Check-in: BK-ACTIVE")
    check_in, check_out = _today_range()
    db.booking_orders.insert_one({
        "prop_id": 704,
        "booking_id": "BK-ACTIVE",
        "room_type_id": "standard",
        "rooms": 1,
        "assigned_rooms": ["HR-704-101"],
        "status": "confirmed",
        "stay_status": "checked_in",
        "check_in_date": check_in,
        "check_out_date": check_out,
    })

    report = build_reconciliation_report(704)

    assert not any(f["domain"] == "room_status" for f in report["findings"])


async def test_report_does_not_flag_non_occupied_statuses(db):
    """vacant_clean / maintenance rooms are never phantom-occupied findings."""
    _seed_hotel(db, 706)
    _seed_room(db, 706, "101", "vacant_clean", note="Disponible")
    _seed_room(db, 706, "102", "maintenance_requested", note="Mantenimiento")

    report = build_reconciliation_report(706)

    assert not any(f["domain"] == "room_status" for f in report["findings"])


async def test_repair_reverts_phantom_occupied_and_keeps_genuine_occupancy(db):
    """Repair flips phantom occupied_clean to vacant_clean, never real stays."""
    _seed_hotel(db, 705)
    _seed_room(db, 705, "101", "occupied_clean", note="Auto-asignada desde reserva BK-X")
    _seed_room(db, 705, "103", "vacant_clean", note="Disponible")
    # Genuinely occupied: checked-in stay with the room assigned, today in range.
    _seed_room(db, 705, "102", "occupied_clean", note="Check-in: BK-REAL")
    check_in, check_out = _today_range()
    db.booking_orders.insert_one({
        "prop_id": 705,
        "booking_id": "BK-REAL",
        "room_type_id": "standard",
        "rooms": 1,
        "assigned_rooms": ["HR-705-102"],
        "status": "confirmed",
        "stay_status": "checked_in",
        "check_in_date": check_in,
        "check_out_date": check_out,
    })

    result = repair_phantom_occupied_rooms(705)

    assert result["prop_id"] == 705
    assert result["reverted"] == ["101"]
    assert db.room_status_log.find_one({"prop_id": 705, "room_label": "101"})["status"] == "vacant_clean"
    assert db.room_status_log.find_one({"prop_id": 705, "room_label": "102"})["status"] == "occupied_clean"
    assert db.room_status_log.find_one({"prop_id": 705, "room_label": "103"})["status"] == "vacant_clean"

    # Idempotent: a second run has nothing left to revert.
    second = repair_phantom_occupied_rooms(705)
    assert second["reverted"] == []
    assert second["count"] == 0


async def test_repair_logs_room_history(db):
    """Every reverted room leaves an audit trail in room_status_history."""
    _seed_hotel(db, 707)
    _seed_room(db, 707, "101", "occupied_clean", note="Auto-asignada desde reserva BK-X")

    repair_phantom_occupied_rooms(707)

    entry = db.room_status_history.find_one({
        "prop_id": 707,
        "room_label": "101",
        "old_status": "occupied_clean",
        "new_status": "vacant_clean",
    })
    assert entry is not None
    assert entry["changed_by"] == "reconciliation:repair"
