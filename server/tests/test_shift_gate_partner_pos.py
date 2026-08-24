"""Route-level gates: partner manual reservations + POS charges.

Closes the two holes found in the expired-shift audit (2026-08):

1. ``POST /api/management/manual-reservations`` (partner portal/API) only
   required an EXISTING shift — an EXPIRED shift still allowed the booking
   and stamped it with the expired shift id. Now it mirrors the front-desk
   gate (billing / check-in-out / reception reservations): 409 on missing
   OR expired shift.
2. ``POST /api/management/bookings/{id}/pos-charge`` required no shift at
   all. Now requires an open (non-expired) shift, like invoice item adds.

The default max-open window is 12h (``DEFAULT_MAX_OPEN_HOURS``), so the
expired fixtures start the shift 13h in the past.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.billing.service import create_folio
from src.app.modules.reservations.service._helpers import utc_now


async def _login(client, username: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


def _open_shift(db, prop_id: int, *, expired: bool = False):
    start = utc_now()
    if expired:
        start = start - timedelta(hours=13)  # > DEFAULT_MAX_OPEN_HOURS (12)
    return db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": start,
            "transactions": [],
        }
    ).inserted_id


def _future_dates(days: int = 2) -> tuple[str, str]:
    base = datetime.now(timezone.utc).date()
    return (
        (base + timedelta(days=days)).isoformat(),
        (base + timedelta(days=days + 1)).isoformat(),
    )


def _seed_booking_hotel(db, prop_id: int, *, check_in: str, check_out: str) -> None:
    """Minimal hotel with inventory + rates so ``create_booking`` can price."""
    db.dim_hotels.insert_one(
        {"prop_id": prop_id, "hotel_name": "Gate Hotel", "display_name": "Gate Hotel"}
    )
    db.room_types.insert_one(
        {
            "room_type_id": "RT-gate-test",
            "prop_id": prop_id,
            "name": "Standard",
            "base_capacity": 2,
            "max_adults": 2,
            "max_children": 1,
            "is_active": True,
        }
    )
    db.hotel_rooms.insert_one(
        {
            "prop_id": prop_id,
            "hotel_room_id": "HR-gate-101",
            "room_label": "101",
            "room_type_id": "RT-gate-test",
            "floor": 2,
            "is_active": True,
        }
    )
    start = datetime.fromisoformat(check_in).date()
    end = datetime.fromisoformat(check_out).date()
    day = start
    while day < end:
        d = day.isoformat()
        db.room_inventory_calendar.insert_one(
            {
                "prop_id": prop_id,
                "room_type_id": "RT-gate-test",
                "date": d,
                "total_rooms": 10,
                "available_rooms": 5,
                "is_available": True,
            }
        )
        db.hotel_rate_calendar.insert_one(
            {
                "prop_id": prop_id,
                "room_type_id": "RT-gate-test",
                "date": d,
                "rate_amount": 150.0,
                "currency": "USD",
                "is_closed": False,
            }
        )
        day += timedelta(days=1)


def _seed_checked_in_booking(db, booking_id: str, prop_id: int) -> None:
    # El gate prop-scoped resuelve el hotel por prop_id — la fila debe existir.
    db.dim_hotels.insert_one(
        {"prop_id": prop_id, "hotel_name": "Gate Hotel", "display_name": "Gate Hotel"}
    )
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            "guest_name": "Gate Test Guest",
            "guest_email": "gate@test.local",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-11",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "assigned_rooms": [],
            "total_price": 150.0,
            "total_nights": 1,
            "room_type_id": "RT-gate-test",
            "room_type_name": "Gate Test",
            "stay_status": "checked_in",
            "status": "confirmed",
            "is_test": True,
            "created_at": utc_now(),
        }
    )


async def _post_partner_manual_reservation(client, prop_id: int):
    check_in, check_out = _future_dates()
    return await client.post(
        "/api/management/manual-reservations",
        json={
            "prop_id": prop_id,
            "room_type_id": "RT-gate-test",
            "guest_name": "Gate Test",
            "guest_email": "gate@test.local",
            "check_in_date": check_in,
            "check_out_date": check_out,
        },
    )


async def _post_pos_charge(client, booking_id: str, prop_id: int):
    return await client.post(
        f"/api/management/bookings/{booking_id}/pos-charge?prop_id={prop_id}",
        json={"concept": "Minibar", "amount": 12.5},
    )


# ── Gap 1: partner manual reservations ─────────────────────────────────────


@pytest.mark.asyncio
async def test_partner_manual_reservation_requires_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])

    resp = await _post_partner_manual_reservation(client, prop_id=980)

    assert resp.status_code == 409, resp.text
    assert "turno de caja activo" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_partner_manual_reservation_blocked_with_expired_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    _open_shift(db, prop_id=981, expired=True)

    resp = await _post_partner_manual_reservation(client, prop_id=981)

    assert resp.status_code == 409, resp.text
    assert "más de 12 horas" in resp.json()["detail"]
    # The booking must NOT have been created nor stamped with the expired shift.
    assert db.booking_orders.count_documents({"prop_id": 981}) == 0


@pytest.mark.asyncio
async def test_partner_manual_reservation_allowed_with_open_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    check_in, check_out = _future_dates()
    _seed_booking_hotel(db, 982, check_in=check_in, check_out=check_out)
    _open_shift(db, prop_id=982)

    resp = await client.post(
        "/api/management/manual-reservations",
        json={
            "prop_id": 982,
            "room_type_id": "RT-gate-test",
            "guest_name": "Gate Test",
            "guest_email": "gate@test.local",
            "check_in_date": check_in,
            "check_out_date": check_out,
        },
    )

    # The gate must not over-block: with an open shift the booking proceeds.
    assert resp.status_code == 201, resp.text
    assert db.booking_orders.count_documents({"prop_id": 982}) == 1


# ── Gap 2: POS charge ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pos_charge_requires_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    booking_id = "BK-GATE-POS-1"
    _seed_checked_in_booking(db, booking_id, prop_id=983)

    resp = await _post_pos_charge(client, booking_id, prop_id=983)

    assert resp.status_code == 409, resp.text
    assert "turno de caja activo" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_pos_charge_blocked_with_expired_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    booking_id = "BK-GATE-POS-2"
    _seed_checked_in_booking(db, booking_id, prop_id=984)
    _open_shift(db, prop_id=984, expired=True)

    resp = await _post_pos_charge(client, booking_id, prop_id=984)

    assert resp.status_code == 409, resp.text
    assert "más de 12 horas" in resp.json()["detail"]
    assert db.additional_charges.count_documents({"booking_id": booking_id}) == 0


@pytest.mark.asyncio
async def test_pos_charge_allowed_with_open_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    booking_id = "BK-GATE-POS-3"
    _seed_checked_in_booking(db, booking_id, prop_id=985)
    shift_id = _open_shift(db, prop_id=985)
    create_folio(booking_id, shift_id=str(shift_id))

    resp = await _post_pos_charge(client, booking_id, prop_id=985)

    assert resp.status_code == 201, resp.text
    assert db.additional_charges.count_documents({"booking_id": booking_id}) == 1
