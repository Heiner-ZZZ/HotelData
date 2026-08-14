"""Legacy payments without shift attribution can be filtered and linked.

Payments created before the shift gate (or via channels that never open a
shift) carry no ``shift_id``. Management needs to spot them in the payments
list ("Sin turno" filter) and link each one to the correct shift so the
cashier attribution appears in reports and the cash-control reconciliation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from tests.conftest import login

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, employee: str = "Teller Demo") -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    result = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": employee,
            "opened_by": "admin_test",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    return str(result.inserted_id)


def _seed_payment(db, prop_id: int, *, shift_id: str | None = None, ref: str = "PAY-LEGACY") -> str:
    doc = {
        "booking_id": f"BK-LINK-{ref}",
        "prop_id": prop_id,
        "amount": 50.0,
        "method": "cash",
        "status": "confirmed",
        "reference": ref,
        "paid_at": datetime.now(_UTC) - timedelta(days=3),
        "created_at": datetime.now(_UTC) - timedelta(days=3),
    }
    if shift_id:
        doc["shift_id"] = ObjectId(shift_id)
    result = db.reservation_payments.insert_one(doc)
    db.fact_reservation_payments.insert_one(dict(doc, **{"_id": result.inserted_id}))
    return str(result.inserted_id)


async def _login(client, admin_user) -> None:
    assert await login(client, admin_user["username"], admin_user["password"]) == 200


@pytest.mark.asyncio
async def test_list_payments_sin_turno_filters_out_linked_payments(client, admin_user, db):
    await _login(client, admin_user)
    shift_id = _open_shift(db, 930)
    linked = _seed_payment(db, 930, shift_id=shift_id, ref="PAY-LINKED")
    _seed_payment(db, 930, shift_id=None, ref="PAY-LEGACY-1")

    response = await client.get("/api/billing/payments?prop_id=930&sin_turno=true")

    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item.get("shift_id") is None for item in items)
    assert all(item["id"] != linked for item in items)
    assert any(item["reference"] == "PAY-LEGACY-1" for item in items)


@pytest.mark.asyncio
async def test_link_payment_to_shift_stamps_attribution_and_mirrors_fact(client, admin_user, db):
    await _login(client, admin_user)
    shift_id = _open_shift(db, 930, employee="Carlos Teller")
    payment_id = _seed_payment(db, 930, shift_id=None, ref="PAY-LEGACY-2")

    response = await client.post(
        f"/api/billing/payments/{payment_id}/link-shift?prop_id=930",
        json={"shift_id": shift_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert str(body["shift_id"]) == shift_id
    assert body["shift_employee"] == "Carlos Teller"
    assert body["shift_opened_by"] == "admin_test"

    raw = db.reservation_payments.find_one({"_id": ObjectId(payment_id)})
    assert str(raw["shift_id"]) == shift_id
    assert raw["shift_employee"] == "Carlos Teller"
    fact = db.fact_reservation_payments.find_one({"_id": ObjectId(payment_id)})
    assert fact is not None
    assert str(fact["shift_id"]) == shift_id


@pytest.mark.asyncio
async def test_link_payment_already_linked_returns_409(client, admin_user, db):
    await _login(client, admin_user)
    shift_id = _open_shift(db, 930)
    other_shift_id = _open_shift(db, 930)
    payment_id = _seed_payment(db, 930, shift_id=other_shift_id, ref="PAY-ALREADY")

    response = await client.post(
        f"/api/billing/payments/{payment_id}/link-shift?prop_id=930",
        json={"shift_id": shift_id},
    )

    assert response.status_code == 409
    assert "ya" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_link_payment_to_shift_of_another_property_returns_400(client, admin_user, db):
    await _login(client, admin_user)
    _open_shift(db, 930)
    foreign_shift_id = _open_shift(db, 931)
    payment_id = _seed_payment(db, 930, shift_id=None, ref="PAY-FOREIGN")

    response = await client.post(
        f"/api/billing/payments/{payment_id}/link-shift?prop_id=930",
        json={"shift_id": foreign_shift_id},
    )

    assert response.status_code == 400
    assert "otro hotel" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_link_candidates_return_shifts_of_payment_property(client, admin_user, db):
    await _login(client, admin_user)
    shift_id = _open_shift(db, 930, employee="Carlos Teller")
    payment_id = _seed_payment(db, 930, shift_id=None, ref="PAY-CAND")

    response = await client.get(f"/api/billing/payments/{payment_id}/link-candidates?prop_id=930")

    assert response.status_code == 200
    body = response.json()
    assert body["payment"]["id"] == payment_id
    ids = [str(s["id"]) for s in body["shifts"]]
    assert shift_id in ids
