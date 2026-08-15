"""Tests for the reception calendar (helpers + ventana de reapertura)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.routes.reception_calendar import (
    _hotel_default_times,
    _normalise_assigned_room_id,
)
from tests.conftest import login


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


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


# ─────────────── Ventana de reapertura en la respuesta ───────────────


@pytest.mark.asyncio
async def test_calendar_exposes_stay_status_and_reopen_window(client, db, admin_user) -> None:
    """El calendario expone ``stay_status`` + ``reopen_window`` por reserva:
    ``'open'`` para no-shows reabribles (hoy/ayer + estadía vigente) y
    ``'too_late'``/``'stay_ended'`` para los antiguos — la UI marca los
    primeros y oculta la acción en los otros."""
    await login(client, admin_user["username"], admin_user["password"])
    db.hotel_rooms.insert_one(
        {
            "hotel_room_id": "HR-CAL-1",
            "prop_id": 991,
            "room_label": "101",
            "room_type_id": "RT-1",
            "room_type_name": "Standard",
            "floor": "1",
            "is_active": True,
        }
    )
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-CAL-OPEN",
            "prop_id": 991,
            "guest_name": "Reopen Hoy",
            "check_in_date": _days_from_today(0),
            "check_out_date": _days_from_today(2),
            "total_nights": 2,
            "status": "confirmed",
            "stay_status": "no_show",
            "assigned_rooms": ["HR-CAL-1"],
            "total_price": 100.0,
            "currency": "USD",
        }
    )
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-CAL-OLD",
            "prop_id": 991,
            "guest_name": "NoShow Viejo",
            "check_in_date": _days_from_today(-5),
            "check_out_date": _days_from_today(-3),
            "total_nights": 2,
            "status": "confirmed",
            "stay_status": "no_show",
            "assigned_rooms": ["HR-CAL-1"],
            "total_price": 100.0,
            "currency": "USD",
        }
    )
    # Una reserva normal (pending) no es no-show: sin ventana.
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-CAL-PENDING",
            "prop_id": 991,
            "guest_name": "Pendiente",
            "check_in_date": _days_from_today(0),
            "check_out_date": _days_from_today(2),
            "total_nights": 2,
            "status": "confirmed",
            "stay_status": "pending",
            "assigned_rooms": ["HR-CAL-1"],
            "total_price": 100.0,
            "currency": "USD",
        }
    )

    response = await client.get("/api/management/reception/calendar", params={"prop_id": 991})

    assert response.status_code == 200, response.text
    reservations = [r for room in response.json()["rooms"] for r in room["reservations"]]
    by_id = {r["booking_id"]: r for r in reservations}
    assert by_id["BK-CAL-OPEN"]["stay_status"] == "no_show"
    assert by_id["BK-CAL-OPEN"]["reopen_window"] == "open"
    assert by_id["BK-CAL-OLD"]["stay_status"] == "no_show"
    assert by_id["BK-CAL-OLD"]["reopen_window"] == "too_late"
    assert by_id["BK-CAL-PENDING"]["stay_status"] == "pending"
    assert by_id["BK-CAL-PENDING"]["reopen_window"] is None


# ─────────── Diagnóstico read-only: no-shows y ventana de reapertura ───────────


def _seed_no_show_booking(
    db,
    booking_id: str,
    *,
    check_in_offset: int,
    check_out_offset: int,
    stay_status: str = "no_show",
    assigned_rooms: list[str] | None = None,
    penalty: float = 100.0,
) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "guest_name": f"Guest {booking_id}",
            "check_in_date": _days_from_today(check_in_offset),
            "check_out_date": _days_from_today(check_out_offset),
            "total_nights": 2,
            "total_price": 100.0,
            "currency": "USD",
            "status": "confirmed",
            "stay_status": stay_status,
            "assigned_rooms": assigned_rooms or [],
            "no_show_penalty_amount": penalty,
            # Misma forma que el servicio: ``datetime`` (Mongo no serializa ``date``).
            "no_show_processed_at": datetime.fromisoformat(f"{local_today()}T12:00:00"),
        }
    )


@pytest.mark.asyncio
async def test_no_show_window_diagnostic_splits_reopenable_vs_closed(
    client, db, admin_user
) -> None:
    """El diagnóstico lista solo no-shows y separa reabribles (ventana abierta)
    de antiguos (too_late / stay_ended), con el número de habitación resuelto."""
    await login(client, admin_user["username"], admin_user["password"])
    db.hotel_rooms.insert_one(
        {
            "hotel_room_id": "HR-CAL-2",
            "prop_id": 991,
            "room_label": "202",
            "room_type_id": "RT-1",
            "room_type_name": "Standard",
            "floor": "2",
            "is_active": True,
        }
    )
    _seed_no_show_booking(db, "BK-DIAG-OPEN", check_in_offset=0, check_out_offset=2, assigned_rooms=["HR-CAL-2"])
    _seed_no_show_booking(db, "BK-DIAG-OLD", check_in_offset=-5, check_out_offset=-3, penalty=120.0)
    _seed_no_show_booking(db, "BK-DIAG-ENDED", check_in_offset=-1, check_out_offset=-1)
    # No-shows NO listados: pending y checked_in no son no-show.
    _seed_no_show_booking(db, "BK-DIAG-PENDING", check_in_offset=0, check_out_offset=2, stay_status="pending")
    _seed_no_show_booking(db, "BK-DIAG-CHECKED", check_in_offset=0, check_out_offset=2, stay_status="checked_in")

    response = await client.get(
        "/api/management/reception/no-shows/reopen-window", params={"prop_id": 991}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert body["reopenable"] == 1
    assert body["closed"] == 2
    by_id = {item["booking_id"]: item for item in body["items"]}

    open_item = by_id["BK-DIAG-OPEN"]
    assert open_item["reopen_window"] == "open"
    assert open_item["reopenable"] is True
    assert open_item["days_late"] == 0
    assert open_item["room_number"] == "202"

    old_item = by_id["BK-DIAG-OLD"]
    assert old_item["reopen_window"] == "too_late"
    assert old_item["reopenable"] is False
    assert old_item["days_late"] == 5
    assert old_item["room_number"] == "Sin asignar"
    assert old_item["no_show_penalty_amount"] == 120.0

    ended_item = by_id["BK-DIAG-ENDED"]
    assert ended_item["reopen_window"] == "stay_ended"
    assert ended_item["reopenable"] is False

    assert "BK-DIAG-PENDING" not in by_id
    assert "BK-DIAG-CHECKED" not in by_id


@pytest.mark.asyncio
async def test_receptionist_can_read_no_show_window_diagnostic(
    client, db
) -> None:
    """La recepción (reservations.manage → read) consulta el diagnóstico para
    saber qué derivar al gerente; la ACCIÓN sigue siendo gerencial."""
    from passlib.context import CryptContext

    role_id = db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["reservations.manage"],
            "is_system": True,
            "created_at": datetime.fromisoformat(f"{local_today()}T12:00:00"),
        }
    ).inserted_id
    db.users.insert_one(
        {
            "username": "recepcionista_diag",
            "email": "recepcionista_diag@hotel.local",
            "display_name": "Recepcionista Diag",
            "password_hash": CryptContext(schemes=["bcrypt"], deprecated="auto").hash("Diag12345!"),
            "primary_role": "recepcionista",
            "role_ids": [role_id],
            "is_active": True,
            "created_at": datetime.fromisoformat(f"{local_today()}T12:00:00"),
        }
    )
    _seed_no_show_booking(db, "BK-DIAG-REC", check_in_offset=0, check_out_offset=2)

    assert await login(client, "recepcionista_diag", "Diag12345!") == 200
    response = await client.get(
        "/api/management/reception/no-shows/reopen-window", params={"prop_id": 991}
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["booking_id"] == "BK-DIAG-REC"
