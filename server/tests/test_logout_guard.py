"""Logout guard: warns before session death when the user has open shifts.

Covers ``GET /api/auth/logout-guard`` — the self-scoped pre-logout check
the management top-nav uses. Keyed off the authenticated user's ObjectId
FKs (``reception_shifts.opened_by_id`` / ``employees.user_id``) with the
username fallback for legacy cash rows that predate the FK migration.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId


async def _login(client, username: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


def _open_shift_doc(prop_id: int, shift_type: str, opened_by: str, opened_by_id=None) -> dict:
    return {
        "prop_id": prop_id,
        "status": "open",
        "shift_type": shift_type,
        "opened_by": opened_by,
        "opened_by_id": opened_by_id,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "transactions": [],
    }


@pytest.mark.asyncio
async def test_logout_guard_empty_without_open_shifts(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])

    resp = await client.get("/api/auth/logout-guard")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_open_shifts"] is False
    assert body["open_cash_shifts"] == []
    assert body["open_attendance_shift"] is None


@pytest.mark.asyncio
async def test_logout_guard_detects_open_cash_shift_by_user_id(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    user = db.users.find_one({"username": admin_user["username"]})
    db.reception_shifts.insert_one(
        _open_shift_doc(987, "morning", admin_user["username"], user["_id"])
    )

    resp = await client.get("/api/auth/logout-guard")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_open_shifts"] is True
    assert len(body["open_cash_shifts"]) == 1
    shift = body["open_cash_shifts"][0]
    assert shift["prop_id"] == 987
    assert shift["shift_label"] != ""
    assert shift["opened_by"] == admin_user["username"]


@pytest.mark.asyncio
async def test_logout_guard_matches_legacy_cash_row_by_username(client, db, admin_user):
    """Rows without ``opened_by_id`` (pre-FK) still match via username."""
    await _login(client, admin_user["username"], admin_user["password"])
    db.reception_shifts.insert_one(
        _open_shift_doc(988, "afternoon", admin_user["username"])  # no opened_by_id
    )

    resp = await client.get("/api/auth/logout-guard")

    assert resp.status_code == 200, resp.text
    assert resp.json()["has_open_shifts"] is True


@pytest.mark.asyncio
async def test_logout_guard_detects_active_attendance_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    user = db.users.find_one({"username": admin_user["username"]})
    emp_id = db.employees.insert_one(
        {
            "full_name": "Guard Employee",
            "user_id": user["_id"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id
    db.employee_shifts.insert_one(
        {
            "employee_id": emp_id,
            "date": "2026-08-16",
            "scheduled_start": "08:00",
            "scheduled_end": "16:00",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )

    resp = await client.get("/api/auth/logout-guard")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_open_shifts"] is True
    assert body["open_attendance_shift"] is not None
    assert body["open_attendance_shift"]["employee_name"] == "Guard Employee"


@pytest.mark.asyncio
async def test_logout_guard_ignores_other_users_shifts(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    other_id = db.users.insert_one(
        {
            "username": "other-guard-user",
            "email": "other-guard@test.local",
            "password_hash": "x",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id
    db.reception_shifts.insert_one(
        _open_shift_doc(989, "evening", "other-guard-user", other_id)
    )

    resp = await client.get("/api/auth/logout-guard")

    assert resp.status_code == 200, resp.text
    assert resp.json()["has_open_shifts"] is False
