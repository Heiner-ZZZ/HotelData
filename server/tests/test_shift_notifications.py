"""Internal notifications for forgotten open cash shifts.

A periodic sweep (``sweep_shift_notifications``) writes internal
notifications to ``notification_log`` (the bell) for each open shift that:

- has exceeded the hotel's ``max_open_hours`` (``shift_expired`` — the
  cash-drawer block is active), and
- has been open at least ``notify_manager_hours`` (``shift_open_long`` —
  a heads-up to the hotel manager before the block kicks in).

Both target the hotel manager (gerente_hotel) plus super admins, are
best-effort, and are deduplicated per (shift_id, notification_type) so a
5-minute sweep never spams.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.reception.notifications import (
    DEFAULT_NOTIFY_MANAGER_HOURS,
    sweep_shift_notifications,
)
from src.app.modules.reception.shifts import (
    DEFAULT_MAX_OPEN_HOURS,
    get_shift_config,
    upsert_shift_config,
)
from tests.conftest import login

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, started_hours_ago: float) -> None:
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


def _seed_manager(db, prop_id: int, *, username: str = "gerente_notif") -> str:
    """A gerente_hotel user assigned to prop_id with a stable email."""
    email = f"{username}@hoteldata.local"
    db.users.insert_one(
        {
            "username": username,
            "email": email,
            "display_name": "Gerente Notificaciones",
            "primary_role": "gerente_hotel",
            "is_active": True,
            "assigned_hotels": [prop_id],
        }
    )
    return email


def _notif_rows(db, notification_type: str) -> list[dict]:
    return list(db.notification_log.find({"notification_type": notification_type}))


def _default_windows() -> dict:
    return {
        "morning": {"start": "08:00", "end": "16:00"},
        "afternoon": {"start": "16:00", "end": "00:00"},
        "evening": {"start": "00:00", "end": "08:00"},
    }


# ── Sweep: expired shifts ────────────────────────────────────────────────


def test_sweep_notifies_manager_when_shift_expired(db):
    _open_shift(db, 971, started_hours_ago=20)  # > DEFAULT_MAX_OPEN_HOURS (12)
    manager_email = _seed_manager(db, 971)

    sweep_shift_notifications()

    rows = _notif_rows(db, "shift_expired")
    assert len(rows) == 1
    assert rows[0]["recipient_email"] == manager_email
    assert rows[0]["status"] == "sent"  # unread in the bell
    assert "12" in rows[0]["message"] or "12.0" in rows[0]["message"]


def test_sweep_is_idempotent_per_shift_and_type(db):
    _open_shift(db, 972, started_hours_ago=20)
    _seed_manager(db, 972)

    sweep_shift_notifications()
    sweep_shift_notifications()  # second sweep must not duplicate

    assert len(_notif_rows(db, "shift_expired")) == 1


def test_sweep_notifies_open_long_at_custom_threshold(db):
    # Config: notify at 5h; shift open 6h → open_long fires, expired does not
    # (6 < DEFAULT_MAX_OPEN_HOURS).
    upsert_shift_config(972, _default_windows(), notify_manager_hours=5, updated_by="gerente_test")
    _open_shift(db, 972, started_hours_ago=6)
    manager_email = _seed_manager(db, 972)

    sweep_shift_notifications()

    assert len(_notif_rows(db, "shift_open_long")) == 1
    assert _notif_rows(db, "shift_open_long")[0]["recipient_email"] == manager_email
    assert _notif_rows(db, "shift_expired") == []


def test_sweep_stays_silent_within_thresholds(db):
    _open_shift(db, 973, started_hours_ago=3)  # < 8 (default notify) and < 12 (max)
    _seed_manager(db, 973)

    sweep_shift_notifications()

    assert _notif_rows(db, "shift_expired") == []
    assert _notif_rows(db, "shift_open_long") == []


def test_default_notify_manager_hours_is_eight():
    assert DEFAULT_NOTIFY_MANAGER_HOURS == 8.0


# ── Config persistence ────────────────────────────────────────────────────


def test_upsert_config_persists_notify_manager_hours(db):
    cfg = upsert_shift_config(974, _default_windows(), notify_manager_hours=6, updated_by="gerente_test")

    assert cfg["notify_manager_hours"] == 6
    assert get_shift_config(974)["notify_manager_hours"] == 6


def test_upsert_config_keeps_default_when_omitted(db):
    cfg = upsert_shift_config(975, _default_windows(), updated_by="gerente_test")

    assert cfg["notify_manager_hours"] == DEFAULT_NOTIFY_MANAGER_HOURS


@pytest.mark.asyncio
async def test_http_put_config_accepts_notify_manager_hours(client, admin_user, db):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.put(
        "/api/reception/shifts/config",
        json={
            "prop_id": 976,
            "windows": {
                "morning": {"start": "08:00", "end": "16:00"},
                "afternoon": {"start": "16:00", "end": "00:00"},
                "evening": {"start": "00:00", "end": "08:00"},
            },
            "notify_manager_hours": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["config"]["notify_manager_hours"] == 10
