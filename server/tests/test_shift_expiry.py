"""Max-open-hours control for cash shifts.

A shift that stays open beyond the hotel's configured ``max_open_hours``
locks front-desk cash operations (cash payments, walk-ins, check-in/out)
until it is closed. The limit lives in the same per-hotel config doc as
the windows (``reception_shift_config.max_open_hours``), defaulting to
``DEFAULT_MAX_OPEN_HOURS`` (12h).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.reception.shifts import (
    DEFAULT_MAX_OPEN_HOURS,
    ShiftExpiredError,
    ensure_shift_not_expired,
    get_active_shift,
    get_shift_config,
    upsert_shift_config,
)
from tests.conftest import login

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift_at(db, prop_id: int, started_hours_ago: float) -> None:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=started_hours_ago)),
            "transactions": [],
        }
    )


def _defaults_windows() -> dict:
    return {
        "morning": {"start": "08:00", "end": "16:00"},
        "afternoon": {"start": "16:00", "end": "00:00"},
        "evening": {"start": "00:00", "end": "08:00"},
    }


# ── Default limit ────────────────────────────────────────────────────────


def test_active_shift_within_default_limit_is_usable(db):
    _open_shift_at(db, 910, started_hours_ago=2)

    ensure_shift_not_expired(910)  # must not raise

    active = get_active_shift(910)
    assert active is not None
    assert active["is_expired"] is False
    assert active["max_open_hours"] == DEFAULT_MAX_OPEN_HOURS


def test_active_shift_over_default_limit_is_expired(db):
    _open_shift_at(db, 911, started_hours_ago=13)

    with pytest.raises(ShiftExpiredError) as exc:
        ensure_shift_not_expired(911)
    assert "sin cerrarse" in exc.value.message
    assert f"{DEFAULT_MAX_OPEN_HOURS:g}" in exc.value.message

    active = get_active_shift(911)
    assert active is not None
    assert active["is_expired"] is True


def test_ensure_shift_not_expired_noop_without_shift(db):
    db.reception_shifts.delete_many({"prop_id": 912})
    ensure_shift_not_expired(912)  # must not raise


# ── Per-hotel limit ──────────────────────────────────────────────────────


def test_expiry_uses_custom_max_open_hours(db):
    upsert_shift_config(913, _defaults_windows(), max_open_hours=2, updated_by="test")
    _open_shift_at(db, 913, started_hours_ago=3)
    with pytest.raises(ShiftExpiredError):
        ensure_shift_not_expired(913)

    upsert_shift_config(914, _defaults_windows(), max_open_hours=48, updated_by="test")
    _open_shift_at(db, 914, started_hours_ago=3)
    ensure_shift_not_expired(914)  # must not raise


def test_get_shift_config_returns_max_open_hours(db):
    config = get_shift_config(915)
    assert config["max_open_hours"] == DEFAULT_MAX_OPEN_HOURS

    upsert_shift_config(915, _defaults_windows(), max_open_hours=6.5, updated_by="test")
    config = get_shift_config(915)
    assert config["max_open_hours"] == 6.5


def test_upsert_rejects_invalid_max_open_hours(db):
    for bad in (0, -1, 24 * 31):
        with pytest.raises(ValueError):
            upsert_shift_config(916, _defaults_windows(), max_open_hours=bad, updated_by="test")


# ── HTTP ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_put_config_persists_max_open_hours(client, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.put(
        "/api/reception/shifts/config",
        params={"prop_id": 917},
        json={"prop_id": 917, "windows": _defaults_windows(), "max_open_hours": 4},
    )

    assert response.status_code == 200
    assert response.json()["config"]["max_open_hours"] == 4

    check = await client.get("/api/reception/shifts/config", params={"prop_id": 917})
    assert check.json()["config"]["max_open_hours"] == 4


@pytest.mark.asyncio
async def test_http_cash_payment_blocked_when_shift_expired(client, admin_user, db):
    booking_id = f"BK-EXP-{secrets.token_hex(4).upper()}"
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 918,
            "guest_name": "Expiry Test Guest",
            "guest_email": "expiry@test.local",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-11",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "assigned_rooms": [],
            "total_price": 150.0,
            "total_nights": 1,
            "room_type_id": "RT-expiry",
            "room_type_name": "Expiry Test",
            "is_test": True,
            "created_at": datetime.now(_UTC),
        }
    )
    _open_shift_at(db, 918, started_hours_ago=13)  # over the 12h default

    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.post(
        "/api/billing/payments?prop_id=918",
        json={"booking_id": booking_id, "amount": 50.0, "method": "cash"},
    )

    assert response.status_code == 409
    assert "sin cerrarse" in response.json()["detail"]
