"""Shift numbering (T01/T02 per hotel per day) + auto HR attendance check-in.

Covers two 2026-08 additions to ``open_shift``:

1. ``shift_number`` — per-hotel per-day sequential number persisted at
   open time so the top-nav chip can render a stable ``T01 · 08:00-16:00``.
2. Auto check-in — opening the cash drawer flips today's pending
   ``employee_shifts`` row to ``active`` (best-effort; never blocks).

``reception_shifts`` and ``employee_shifts`` are both cleaned by conftest;
each test uses its own prop_id/username to stay hermetic.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from src.app.modules.reception.shifts import open_shift


def _unique(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_cashier(db, username: str, full_name: str) -> ObjectId:
    """Seed users + employees rows so open_shift's FK resolvers and the
    auto check-in (user → employee) can find the opener."""
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@test.local",
            "display_name": full_name,
            "password_hash": "x",
            "primary_role": "recepcionista",
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    emp_id = db.employees.insert_one(
        {
            "full_name": full_name,
            "user_id": user_id,
            "prop_id": 1,
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return emp_id


def _seed_today_pending_shift(db, emp_id: ObjectId) -> ObjectId:
    today_str = _now().strftime("%Y-%m-%d")
    return db.employee_shifts.insert_one(
        {
            "employee_id": emp_id,
            "date": today_str,
            "scheduled_start": "08:00",
            "scheduled_end": "16:00",
            "area": "Recepción",
            "status": "pending",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id


def test_open_shift_assigns_sequential_number_per_day(db):
    prop_id = 401
    username = _unique("opener")
    _seed_cashier(db, username, _unique("Cajero"))
    db.reception_shifts.delete_many({"prop_id": prop_id})

    first = open_shift(
        prop_id=prop_id, shift_type="morning", employee=_unique("Cajero"),
        opened_by=username, bypass_schedule_check=True,
    )
    assert first["shift_number"] == 1

    second = open_shift(
        prop_id=prop_id, shift_type="morning", employee=_unique("Cajero2"),
        opened_by=username, bypass_schedule_check=True, force=True,
    )
    assert second["shift_number"] == 2


def test_shift_number_resets_per_day(db):
    prop_id = 402
    username = _unique("opener")
    _seed_cashier(db, username, _unique("Cajero"))
    db.reception_shifts.delete_many({"prop_id": prop_id})

    yesterday = (_now() - timedelta(days=1)).isoformat()
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "closed",
            "shift_type": "morning",
            "start_time": yesterday,
        }
    )

    opened = open_shift(
        prop_id=prop_id, shift_type="morning", employee=_unique("Cajero"),
        opened_by=username, bypass_schedule_check=True,
    )
    assert opened["shift_number"] == 1


def test_open_shift_auto_checkin_pending_attendance(db):
    prop_id = 403
    username = _unique("opener")
    full_name = _unique("Cajero")
    emp_id = _seed_cashier(db, username, full_name)
    db.reception_shifts.delete_many({"prop_id": prop_id})
    shift_id = _seed_today_pending_shift(db, emp_id)

    opened = open_shift(
        prop_id=prop_id, shift_type="morning", employee=full_name,
        opened_by=username, bypass_schedule_check=True,
    )
    assert opened["shift_number"] == 1

    doc = db.employee_shifts.find_one({"_id": shift_id})
    assert doc is not None
    assert doc["status"] == "active"
    assert doc["actual_check_in"] is not None


def test_open_shift_skips_auto_checkin_without_hr_row(db):
    prop_id = 404
    username = _unique("opener")
    _seed_cashier(db, username, _unique("Cajero"))
    db.reception_shifts.delete_many({"prop_id": prop_id})

    opened = open_shift(
        prop_id=prop_id, shift_type="morning", employee=_unique("Cajero"),
        opened_by=username, bypass_schedule_check=True,
    )
    assert opened["shift_number"] == 1
