"""Unit tests for the reception calendar helpers."""
from __future__ import annotations

import pytest

from src.app.modules.reservations.routes.reception_calendar import (
    _hotel_default_times,
    _normalise_assigned_room_id,
)


class _FakeHotelPolicies:
    def __init__(self, result):
        self._result = result
        self.last_query: dict | None = None

    def find_one(self, query, projection):
        self.last_query = query
        return self._result


class _FakeDb:
    def __init__(self, policy):
        self.hotel_policies = _FakeHotelPolicies(policy)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("HR-1-110", "HR-1-110"),
        ({"hotel_room_id": "HR-1-110", "room_label": "110"}, "HR-1-110"),
        ({"room_id": "HR-1-111"}, "HR-1-111"),
        ({"id": "HR-1-112"}, "HR-1-112"),
        (None, ""),
        ({}, ""),
        ("  HR-1-113  ", "HR-1-113"),
    ],
)
def test_normalise_assigned_room_id_accepts_legacy_shapes(value, expected):
    assert _normalise_assigned_room_id(value) == expected


def test_normalise_assigned_room_id_does_not_use_display_label_as_id():
    assert _normalise_assigned_room_id({"room_label": "110"}) == ""


def test_hotel_default_times_returns_configured_policy():
    db = _FakeDb({"check_in_time": "14:00", "check_out_time": "11:00"})
    assert _hotel_default_times(db, 1) == {
        "check_in_time": "14:00",
        "check_out_time": "11:00",
    }


def test_hotel_default_times_falls_back_to_empty_when_no_policy():
    db = _FakeDb(None)
    assert _hotel_default_times(db, 1) == {"check_in_time": "", "check_out_time": ""}


def test_hotel_default_times_treats_missing_hours_as_empty():
    db = _FakeDb({"check_in_time": None})
    assert _hotel_default_times(db, 1) == {"check_in_time": "", "check_out_time": ""}


def test_hotel_default_times_queries_hotel_wide_policy_only():
    """The lookup must target the hotel-wide default, not per-room policies."""
    db = _FakeDb({"check_in_time": "14:00", "check_out_time": "11:00"})
    _hotel_default_times(db, 7)
    query = db.hotel_policies.last_query
    assert query is not None
    assert query["prop_id"] == 7
    assert query["room_type_id"] == {"$in": ["", None]}
    assert query["season_id"] == {"$in": ["", None]}
    assert "rate_plan_id" not in query
