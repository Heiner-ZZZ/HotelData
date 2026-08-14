"""Per-hotel configurable cash-shift windows.

The reception cash shift model hardcodes three 8h windows (morning
08:00-16:00, afternoon 16:00-00:00, evening 00:00-08:00) in
``reception/shifts.py``. These tests pin the new per-property override:

1. ``get_shift_config`` falls back to defaults when no config doc exists.
2. ``upsert_shift_config`` persists custom windows per property.
3. Validation rejects overlapping / malformed / zero-length windows.
4. The clock heuristic and ``resolve_expected_shift_type`` classify hours
   using the configured windows (with wrap-past-midnight support).
5. ``open_shift`` surfaces the configured window in the 422 message.
6. HTTP GET/PUT endpoints with permission gates.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.reception.shifts import (
    DEFAULT_SHIFT_HOURS,
    SHIFT_TYPES,
    ScheduleMismatchError,
    _shift_type_for_hour,
    get_shift_config,
    get_shift_windows,
    open_shift,
    resolve_expected_shift_type,
    upsert_shift_config,
)
from tests.conftest import login

CUSTOM_WINDOWS = {
    "morning": {"start": "10:00", "end": "18:00"},
    "afternoon": {"start": "18:00", "end": "02:00"},
    "evening": {"start": "02:00", "end": "10:00"},
}


def _defaults() -> dict:
    return {t: {"start": DEFAULT_SHIFT_HOURS[t]["start"], "end": DEFAULT_SHIFT_HOURS[t]["end"]} for t in SHIFT_TYPES}


# ── Service: defaults ────────────────────────────────────────────────────


def test_get_shift_config_returns_defaults_when_no_doc(db):
    config = get_shift_config(901)

    assert config["prop_id"] == 901
    assert config["is_custom"] is False
    assert config["windows"] == _defaults()
    assert config["labels"]["morning"] == "Matutino (08:00-16:00)"
    assert config["labels"]["afternoon"] == "Vespertino (16:00-00:00)"
    assert config["labels"]["evening"] == "Nocturno (00:00-08:00)"


def test_get_shift_windows_falls_back_to_defaults(db):
    assert get_shift_windows(901) == _defaults()


# ── Service: upsert + persistence ────────────────────────────────────────


def test_upsert_shift_config_persists_custom_windows(db):
    config = upsert_shift_config(901, CUSTOM_WINDOWS, updated_by="gerente_test")

    assert config["is_custom"] is True
    assert config["updated_by"] == "gerente_test"
    assert config["windows"]["morning"] == {"start": "10:00", "end": "18:00"}
    assert config["labels"]["morning"] == "Matutino (10:00-18:00)"

    # Persisted in Mongo — a fresh read sees it.
    again = get_shift_config(901)
    assert again["is_custom"] is True
    assert again["windows"]["afternoon"] == {"start": "18:00", "end": "02:00"}


def test_upsert_shift_config_is_per_property(db):
    upsert_shift_config(901, CUSTOM_WINDOWS, updated_by="gerente_test")

    # A different property keeps the defaults.
    other = get_shift_config(902)
    assert other["is_custom"] is False
    assert other["windows"] == _defaults()


# ── Service: validation ──────────────────────────────────────────────────


def test_upsert_rejects_overlapping_windows(db):
    with pytest.raises(ValueError, match="se superponen"):
        upsert_shift_config(
            901,
            {
                "morning": {"start": "08:00", "end": "16:00"},
                "afternoon": {"start": "12:00", "end": "20:00"},
                "evening": {"start": "00:00", "end": "08:00"},
            },
            updated_by="test",
        )


def test_upsert_rejects_invalid_hhmm(db):
    with pytest.raises(ValueError, match="HH:MM"):
        upsert_shift_config(
            901,
            {
                "morning": {"start": "25:00", "end": "16:00"},
                "afternoon": {"start": "16:00", "end": "00:00"},
                "evening": {"start": "00:00", "end": "08:00"},
            },
            updated_by="test",
        )


def test_upsert_rejects_zero_duration(db):
    with pytest.raises(ValueError, match="Duración"):
        upsert_shift_config(
            901,
            {
                "morning": {"start": "08:00", "end": "08:00"},
                "afternoon": {"start": "16:00", "end": "00:00"},
                "evening": {"start": "00:00", "end": "08:00"},
            },
            updated_by="test",
        )


def test_upsert_rejects_missing_window(db):
    with pytest.raises(ValueError, match="evening"):
        upsert_shift_config(
            901,
            {
                "morning": {"start": "08:00", "end": "16:00"},
                "afternoon": {"start": "16:00", "end": "00:00"},
            },
            updated_by="test",
        )


# ── Clock heuristic with configured windows ──────────────────────────────


def test_shift_type_for_hour_uses_custom_windows(db):
    upsert_shift_config(901, CUSTOM_WINDOWS, updated_by="test")
    windows = get_shift_windows(901)

    # 17:00 is afternoon under defaults, but morning under 10:00-18:00.
    assert _shift_type_for_hour(17, windows) == "morning"
    # 18:00 boundary belongs to the afternoon window (18:00-02:00).
    assert _shift_type_for_hour(18, windows) == "afternoon"
    # 01:00 belongs to the wrapping afternoon window.
    assert _shift_type_for_hour(1, windows) == "afternoon"


def test_shift_type_for_hour_wraps_midnight(db):
    upsert_shift_config(
        901,
        {
            "morning": {"start": "10:00", "end": "18:00"},
            "afternoon": {"start": "18:00", "end": "22:00"},
            "evening": {"start": "22:00", "end": "10:00"},
        },
        updated_by="test",
    )
    windows = get_shift_windows(901)

    assert _shift_type_for_hour(2, windows) == "evening"
    assert _shift_type_for_hour(23, windows) == "evening"
    assert _shift_type_for_hour(21, windows) == "afternoon"
    assert _shift_type_for_hour(12, windows) == "morning"


def test_shift_type_for_hour_falls_back_to_defaults_when_uncovered(db):
    upsert_shift_config(
        901,
        {
            "morning": {"start": "10:00", "end": "18:00"},
            "afternoon": {"start": "18:00", "end": "23:00"},
            "evening": {"start": "23:00", "end": "07:00"},
        },
        updated_by="test",
    )
    windows = get_shift_windows(901)

    # 08:00 is not covered by any configured window → default classification.
    assert _shift_type_for_hour(8, windows) == "morning"


# ── resolve_expected_shift_type with per-property windows ────────────────


def test_resolve_expected_shift_type_uses_prop_windows(db):
    upsert_shift_config(901, CUSTOM_WINDOWS, updated_by="test")
    fixed = datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc)

    expected, source = resolve_expected_shift_type("ghost-user-xyz", fixed, prop_id=901)

    # 17:00 is "morning" under the custom 10:00-18:00 window.
    assert expected == "morning"
    assert source == "time_of_day"


def test_resolve_expected_shift_type_defaults_without_prop(db):
    fixed = datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc)

    expected, source = resolve_expected_shift_type("ghost-user-xyz", fixed)

    assert expected == "afternoon"  # default 16:00-00:00 window
    assert source == "time_of_day"


# ── open_shift surfaces the configured window in the 422 ─────────────────


def test_open_shift_schedule_mismatch_uses_custom_window(db, monkeypatch):
    upsert_shift_config(901, CUSTOM_WINDOWS, updated_by="test")
    fixed = datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc)

    import src.app.modules.reception.shifts as shifts_mod

    monkeypatch.setattr(shifts_mod, "_now_dt", lambda: fixed)

    with pytest.raises(ScheduleMismatchError) as exc:
        open_shift(901, "afternoon", "Recepcionista Test", opened_by="ghost-user-xyz")

    assert exc.value.expected == "morning"
    assert exc.value.expected_window == "10:00-18:00"


# ── HTTP endpoints ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_get_config_returns_defaults(client, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.get("/api/reception/shifts/config", params={"prop_id": 902})

    assert response.status_code == 200
    body = response.json()["config"]
    assert body["is_custom"] is False
    assert body["windows"] == _defaults()


@pytest.mark.asyncio
async def test_http_put_config_persists(client, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.put(
        "/api/reception/shifts/config",
        json={"prop_id": 902, "windows": CUSTOM_WINDOWS},
    )

    assert response.status_code == 200
    body = response.json()["config"]
    assert body["is_custom"] is True
    assert body["windows"]["morning"] == {"start": "10:00", "end": "18:00"}

    # Persisted — GET confirms.
    check = await client.get("/api/reception/shifts/config", params={"prop_id": 902})
    assert check.json()["config"]["windows"]["morning"] == {"start": "10:00", "end": "18:00"}


@pytest.mark.asyncio
async def test_http_put_rejects_overlapping_windows(client, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.put(
        "/api/reception/shifts/config",
        json={
            "prop_id": 902,
            "windows": {
                "morning": {"start": "08:00", "end": "16:00"},
                "afternoon": {"start": "12:00", "end": "20:00"},
                "evening": {"start": "00:00", "end": "08:00"},
            },
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_http_put_requires_shifts_manage(client, cliente_user):
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200

    response = await client.put(
        "/api/reception/shifts/config",
        json={"prop_id": 902, "windows": CUSTOM_WINDOWS},
    )

    assert response.status_code == 403
