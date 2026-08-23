"""Emergency close flow for expired cash shifts.

A shift that stays open beyond the hotel's ``max_open_hours`` blocks cash
operations (payments, front-desk check-in/out, walk-ins). To unblock, a
manager may perform an *emergency close*: a simplified arqueo that stamps
``close_mode="emergency"`` with the reason (default ``vencimiento``) and
records the action + reason in the audit log.

Only holders of ``shifts.manage`` (gerente_hotel / super_admin) may close
in emergency mode; a receptionist (``shifts.update`` only) is rejected
with 403. The normal close flow keeps working for receptionists.

Migración E (2026-08): reception gatea POR HOTEL (``require_prop_permission``)
— cada usuario HTTP necesita hotel_roles + role_assignments en el prop del
test (``_grant_hotel_role``) y las llamadas llevan ``prop_id`` en el query.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from src.app.modules.reception.shifts import (
    ShiftExpiredError,
    close_shift,
    ensure_shift_not_expired,
    get_active_shift_id,
)
from tests.conftest import _seed_user, login

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, started_hours_ago: float = 20.0) -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    res = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=started_hours_ago)),
            "transactions": [],
            "cash_initial": 100.0,
        }
    )
    return str(res.inserted_id)


def _seed_role(db, name: str, permissions: list[str]):
    db.roles.delete_many({"role_name": name})
    db.roles.insert_one({"role_name": name, "permissions": permissions, "is_active": True})


def _grant_hotel_role(db, user_id, prop_id: int, permissions: list[str]) -> None:
    """Migración E: reception gatea por hotel — el usuario necesita un hotel
    role con los códigos y una role_assignment en el prop del test."""
    role_id = db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": f"test_role_{user_id}",
            "display_name": "Rol Test",
            "permissions": permissions,
            "is_active": True,
            "created_at": datetime.now(_UTC),
            "updated_at": datetime.now(_UTC),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {"user_id": user_id, "prop_id": prop_id, "role_id": role_id}
    )
    db.users.update_one({"_id": user_id}, {"$set": {"assigned_hotels": [prop_id]}})


# ── Service level ─────────────────────────────────────────────────────────


def test_emergency_close_stamps_mode_and_default_reason(db):
    shift_id = _open_shift(db, 951)

    result = close_shift(shift_id, cash_counted=100.0, closed_by="gerente_test", emergency=True)

    assert result["status"] == "closed"
    assert result["close_mode"] == "emergency"
    assert result["emergency_reason"] == "vencimiento"


def test_emergency_close_stores_custom_reason(db):
    shift_id = _open_shift(db, 952)
    reason = "Caja desincronizada por corte de luz"

    result = close_shift(
        shift_id,
        cash_counted=100.0,
        closed_by="gerente_test",
        emergency=True,
        emergency_reason=reason,
    )

    assert result["close_mode"] == "emergency"
    assert result["emergency_reason"] == reason


def test_normal_close_has_no_emergency_markers(db):
    shift_id = _open_shift(db, 953)

    result = close_shift(shift_id, cash_counted=100.0, closed_by="recep_test")

    assert result["status"] == "closed"
    assert "close_mode" not in result
    assert "emergency_reason" not in result


def test_emergency_close_unblocks_cash_operations(db):
    prop_id = 954
    shift_id = _open_shift(db, prop_id, started_hours_ago=50.0)

    with pytest.raises(ShiftExpiredError):
        ensure_shift_not_expired(prop_id)  # expired before close

    close_shift(shift_id, cash_counted=100.0, closed_by="gerente_test", emergency=True)

    ensure_shift_not_expired(prop_id)  # must not raise after close
    assert get_active_shift_id(prop_id) is None


# ── HTTP level ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_emergency_close_requires_shifts_manage(client, db):
    _seed_role(db, "recepcionista", ["shifts.read", "shifts.update"])
    user = _seed_user(
        db,
        username="recep_close_test",
        email="recep_close@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    _grant_hotel_role(db, ObjectId(user["user_id"]), 955, ["shifts.read", "shifts.update"])
    shift_id = _open_shift(db, 955)

    assert await login(client, user["username"], user["password"])
    response = await client.post(
        f"/api/reception/shifts/{shift_id}/close",
        params={"prop_id": 955},
        json={"cash_counted": 100.0, "emergency": True},
    )

    assert response.status_code == 403
    assert "shifts.manage" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_emergency_close_as_manager_stamps_and_audits(client, db):
    _seed_role(db, "gerente_hotel", ["shifts.manage", "shifts.read", "shifts.update"])
    user = _seed_user(
        db,
        username="gerente_close_test",
        email="gerente_close@example.com",
        password="Pass123!",
        role="gerente_hotel",
    )
    _grant_hotel_role(db, ObjectId(user["user_id"]), 956, ["shifts.manage", "shifts.read", "shifts.update"])
    shift_id = _open_shift(db, 956)

    assert await login(client, user["username"], user["password"])
    response = await client.post(
        f"/api/reception/shifts/{shift_id}/close",
        params={"prop_id": 956},
        json={"cash_counted": 100.0, "emergency": True},
    )

    assert response.status_code == 200
    doc = db.reception_shifts.find_one({"_id": ObjectId(shift_id)})
    assert doc["close_mode"] == "emergency"
    assert doc["emergency_reason"] == "vencimiento"
    assert doc["closed_by"] == "gerente_close_test"

    audit = db.audit_log.find_one(
        {"entity_type": "reception_shifts", "entity_id": f"close:{shift_id}"}
    )
    assert audit is not None
    assert audit["diff"].get("close_mode") == "emergency"
    assert audit["diff"].get("emergency_reason") == "vencimiento"


@pytest.mark.asyncio
async def test_http_normal_close_still_allowed_for_receptionist(client, db):
    _seed_role(db, "recepcionista", ["shifts.read", "shifts.update"])
    user = _seed_user(
        db,
        username="recep_normal_test",
        email="recep_normal@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    _grant_hotel_role(db, ObjectId(user["user_id"]), 957, ["shifts.read", "shifts.update"])
    shift_id = _open_shift(db, 957)

    assert await login(client, user["username"], user["password"])
    response = await client.post(
        f"/api/reception/shifts/{shift_id}/close",
        params={"prop_id": 957},
        json={"cash_counted": 100.0},
    )

    assert response.status_code == 200
    doc = db.reception_shifts.find_one({"_id": ObjectId(shift_id)})
    assert doc["status"] == "closed"
    assert "close_mode" not in doc
