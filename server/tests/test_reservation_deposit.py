"""Advance-payment policy: real deposit via billing at reservation creation.

Closes the fake card-processing hole (2026-08):

- The legacy ``POST /api/payments/process`` stub (deleted) returned an
  invented ``approved`` and the booking was marked ``payment_status="paid"``
  without persisting any payment. The front-desk wizard now registers the
  deposit as a REAL billing payment (``reservation_payments`` + shift_id)
  in the same ``POST /api/reservations`` call.
- ``_validate_deposit`` is satisfied only by actual money recorded in the
  same call; a deposit-policy hotel still blocks creation without it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.reservations.service._helpers import utc_now


async def _login(client, username: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


def _future_dates(days: int = 2) -> tuple[str, str]:
    base = datetime.now(timezone.utc).date()
    return (
        (base + timedelta(days=days)).isoformat(),
        (base + timedelta(days=days + 1)).isoformat(),
    )


def _seed_hotel(db, prop_id: int, *, deposit_percent: int = 0) -> None:
    """Hotel with inventory + rates + optional deposit policy."""
    check_in, check_out = _future_dates()
    db.dim_hotels.insert_one(
        {"prop_id": prop_id, "hotel_name": "Deposit Hotel", "display_name": "Deposit Hotel"}
    )
    db.room_types.insert_one(
        {
            "room_type_id": "RT-dep-test",
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
            "hotel_room_id": "HR-dep-101",
            "room_label": "101",
            "room_type_id": "RT-dep-test",
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
                "room_type_id": "RT-dep-test",
                "date": d,
                "total_rooms": 10,
                "available_rooms": 5,
                "is_available": True,
            }
        )
        db.hotel_rate_calendar.insert_one(
            {
                "prop_id": prop_id,
                "room_type_id": "RT-dep-test",
                "date": d,
                "rate_amount": 150.0,
                "currency": "USD",
                "is_closed": False,
            }
        )
        day += timedelta(days=1)
    if deposit_percent > 0:
        db.hotel_policies.insert_one(
            {
                "prop_id": prop_id,
                "room_type_id": "",
                "rate_plan_id": "",
                "season_id": "",
                "deposit_required": True,
                "deposit_percent": deposit_percent,
            }
        )


def _open_shift(db, prop_id: int):
    return db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": utc_now(),
            "transactions": [],
        }
    ).inserted_id


async def _create_reservation(client, prop_id: int, **extra) -> object:
    check_in, check_out = _future_dates()
    payload = {
        "prop_id": prop_id,
        "room_type_id": "RT-dep-test",
        "guest_name": "Deposit Guest",
        "guest_email": "deposit@test.local",
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": 1,
        "children": 0,
        "rooms": 1,
        "comment": "",
        "guest_phone": "+51999999999",
        "cedula": "70000001",
        "check_in_time": "15:00",
        "check_out_time": "12:00",
    }
    payload.update(extra)
    return await client.post("/api/reservations", json=payload)


@pytest.mark.asyncio
async def test_deposit_policy_requires_real_deposit(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    _seed_hotel(db, prop_id=960, deposit_percent=30)
    _open_shift(db, prop_id=960)

    resp = await _create_reservation(client, prop_id=960)

    assert resp.status_code == 400, resp.text
    assert "depósito mínimo" in resp.json()["detail"]
    assert db.booking_orders.count_documents({"prop_id": 960}) == 0
    assert db.reservation_payments.count_documents({}) == 0


@pytest.mark.asyncio
async def test_deposit_insufficient_rejected(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    _seed_hotel(db, prop_id=961, deposit_percent=30)  # min = $45
    _open_shift(db, prop_id=961)

    resp = await _create_reservation(
        client, prop_id=961,
        deposit={"amount": 20.0, "method": "cash"},
    )

    assert resp.status_code == 400, resp.text
    assert "no alcanza el mínimo" in resp.json()["detail"]
    assert db.booking_orders.count_documents({"prop_id": 961}) == 0


@pytest.mark.asyncio
async def test_deposit_registered_as_real_payment_with_shift(client, db, admin_user):
    await _login(client, admin_user["username"], admin_user["password"])
    _seed_hotel(db, prop_id=962, deposit_percent=30)  # min = $45
    shift_id = _open_shift(db, prop_id=962)

    resp = await _create_reservation(
        client, prop_id=962,
        deposit={"amount": 45.0, "method": "cash", "reference": "DEP-REF-001"},
    )

    assert resp.status_code == 201, resp.text
    booking_id = resp.json()["booking_id"]
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    assert booking is not None
    # Un pago REAL persistido con el shift_id del turno activo.
    payment = db.reservation_payments.find_one({"booking_id": booking_id})
    assert payment is not None
    assert round(float(payment["amount"]), 2) == 45.0
    assert payment["method"] == "cash"
    assert payment["status"] == "confirmed"
    assert payment["shift_id"] == shift_id
    assert payment["reference"] == "DEP-REF-001"
    # La reserva nace pending: el pago del depósito es parcial, no "paid".
    assert booking["payment_status"] == "pending"

    # El detalle expone el depósito REAL (no metadata de tarjeta ficticia).
    detail = await client.get(f"/api/reservations/{booking_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["deposit"] is not None
    assert round(float(body["deposit"]["amount"]), 2) == 45.0
    assert body["deposit"]["method"] == "cash"
    assert body["deposit"]["reference"] == "DEP-REF-001"
    assert body["deposit"]["status"] == "confirmed"
    assert body["deposit"]["paid_at"] is not None


@pytest.mark.asyncio
async def test_booking_never_marked_paid_by_payment_metadata(client, db, admin_user):
    """El hack del stub (payment_method → 'paid') está eliminado."""
    await _login(client, admin_user["username"], admin_user["password"])
    _seed_hotel(db, prop_id=963)  # sin política de depósito
    _open_shift(db, prop_id=963)

    resp = await _create_reservation(client, prop_id=963, payment_method="credit_card", card_last4="4242")

    assert resp.status_code == 201, resp.text
    booking = db.booking_orders.find_one({"booking_id": resp.json()["booking_id"]})
    assert booking is not None
    assert booking["payment_status"] == "pending"
    assert db.reservation_payments.count_documents({"booking_id": booking["booking_id"]}) == 0


@pytest.mark.asyncio
async def test_payments_process_endpoint_removed(client, db, admin_user):
    """El stub legacy /api/payments/process ya no existe (404)."""
    await _login(client, admin_user["username"], admin_user["password"])

    resp = await client.post(
        "/api/payments/process",
        json={
            "card_number": "4242424242424242",
            "card_holder": "Fake Card",
            "expiry": "12/30",
            "cvv": "123",
            "amount": 100.0,
        },
    )

    assert resp.status_code == 404
