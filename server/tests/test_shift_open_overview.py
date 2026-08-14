"""Management overview of ALL open cash shifts across hotels.

A gerente/super_admin view that lists every open shift in the chain with
its age (hours open), effective max-open-hours limit and expiry status so
forgotten shifts are easy to spot.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from src.app.modules.reception.shifts import list_open_shifts_overview
from tests.conftest import login

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _seed_open_shift(db, prop_id: int, *, started_hours_ago: float, employee: str = "Demo") -> None:
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": employee,
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=started_hours_ago)),
            "cash_initial": 100.0,
            "total_collected": 25.0,
            "transactions": [
                {"transaction_id": f"TXN-{prop_id}-1", "type": "payment", "amount": 25.0},
            ],
        }
    )


def _seed_closed_shift(db, prop_id: int) -> None:
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "closed",
            "shift_type": "morning",
            "employee": "Closed Demo",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=30)),
            "closed_at": _iso(datetime.now(_UTC) - timedelta(hours=22)),
        }
    )


def _seed_hotel(db, prop_id: int, name: str) -> None:
    db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {"$set": {"prop_id": prop_id, "display_name": name, "hotel_name": name}},
        upsert=True,
    )


def _seed_open_shift_with_id(
    db,
    prop_id: int,
    *,
    total_collected: float,
    transactions: list[dict],
) -> str:
    """Insert an open shift and return its ``_id`` for FK stamping."""
    result = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": "Drawer Demo",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=2)),
            "cash_initial": 100.0,
            "total_collected": total_collected,
            "transactions": transactions,
        }
    )
    return str(result.inserted_id)


def _seed_stamped_payment(
    db,
    shift_id: str,
    *,
    booking_id: str,
    amount: float,
    status: str = "confirmed",
) -> None:
    """Insert a reservation_payment stamped with the shift FK."""
    db.reservation_payments.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 1,
            "amount": amount,
            "method": "cash",
            "status": status,
            "shift_id": ObjectId(shift_id),
            "paid_at": datetime.now(_UTC),
            "reference": f"PAY-{booking_id}-{amount}",
        }
    )


def test_overview_lists_open_shifts_from_all_hotels(db):
    _seed_hotel(db, 921, "Hotel A Test")
    _seed_hotel(db, 922, "Hotel B Test")
    _seed_open_shift(db, 921, started_hours_ago=5)
    _seed_open_shift(db, 922, started_hours_ago=2)
    # Closed shifts must NOT appear.
    _seed_closed_shift(db, 922)

    items = list_open_shifts_overview()

    props = [i["prop_id"] for i in items]
    assert 921 in props
    assert 922 in props

    by_prop = {i["prop_id"]: i for i in items}
    assert by_prop[921]["hotel_name"] == "Hotel A Test"
    assert by_prop[922]["hotel_name"] == "Hotel B Test"


def test_overview_carries_age_and_expiry_fields(db):
    _seed_hotel(db, 923, "Hotel C Test")
    _seed_open_shift(db, 923, started_hours_ago=14)

    items = list_open_shifts_overview()
    assert len(items) == 1
    row = items[0]

    assert row["hours_open"] >= 13.5
    assert row["max_open_hours"] == 12.0
    assert row["is_expired"] is True
    assert row["expires_at"] is not None
    assert row["transaction_count"] == 1
    assert row["total_collected"] == 25.0
    assert row["employee"] == "Demo"
    assert row["shift_label"].startswith("Matutino")


def test_overview_sorts_by_age_descending(db):
    _seed_hotel(db, 924, "Hotel D Test")
    _seed_hotel(db, 925, "Hotel E Test")
    _seed_open_shift(db, 924, started_hours_ago=20)
    _seed_open_shift(db, 925, started_hours_ago=3)

    items = list_open_shifts_overview()

    assert items[0]["prop_id"] == 924
    assert items[1]["prop_id"] == 925
    assert items[0]["hours_open"] > items[1]["hours_open"]


def test_overview_empty_when_no_open_shifts(db):
    _seed_closed_shift(db, 926)
    assert list_open_shifts_overview() == []


def test_overview_adds_stamped_payments_to_drawer_without_double_counting(db):
    """"En caja" incluye los pagos estampados con shift_id, sin doble-contar
    la liquidación de check-out ya registrada como transacción del turno."""
    _seed_hotel(db, 928, "Hotel G Test")
    shift_id = _seed_open_shift_with_id(
        db,
        928,
        total_collected=100.0,
        transactions=[
            {
                "transaction_id": "TXN-G-1",
                "type": "check_out",
                "booking_id": "BK-CO-1",
                "amount": 100.0,
            },
        ],
    )
    # Pago estampado de OTRA reserva → suma al cajón.
    _seed_stamped_payment(db, shift_id, booking_id="BK-EXTRA-1", amount=50.0)
    # Pago estampado de la MISMA liquidación de check-out → ya contado, NO suma.
    _seed_stamped_payment(db, shift_id, booking_id="BK-CO-1", amount=100.0)
    # Pago fallido → nunca entra al cajón.
    _seed_stamped_payment(db, shift_id, booking_id="BK-FAIL-1", amount=20.0, status="failed")

    items = list_open_shifts_overview()

    assert len(items) == 1
    row = items[0]
    # 100 (check-out ya contado) + 50 (pago estampado extra) = 150 — no 200.
    assert row["total_collected"] == 150.0
    assert row["stamped_payments_count"] == 1


def test_overview_stamped_payment_for_check_in_booking_is_counted(db):
    """El check-in registra transacción en $0 (no infla el cajón); un pago
    real estampado para esa reserva sí debe sumar."""
    _seed_hotel(db, 929, "Hotel H Test")
    shift_id = _seed_open_shift_with_id(
        db,
        929,
        total_collected=0.0,
        transactions=[
            {
                "transaction_id": "TXN-H-1",
                "type": "check_in",
                "booking_id": "BK-CI-1",
                "amount": 0.0,
            },
        ],
    )
    _seed_stamped_payment(db, shift_id, booking_id="BK-CI-1", amount=30.0)

    items = list_open_shifts_overview()

    assert len(items) == 1
    assert items[0]["total_collected"] == 30.0
    assert items[0]["stamped_payments_count"] == 1


def test_overview_includes_payment_breakdown_by_method(db):
    """El overview expone el desglose por método del arqueo esperado
    (fondo + cobrado por método) para el resumen del cierre forzado:
    transacciones del turno + pagos estampados, sin doble-contar la
    liquidación ya registrada."""
    _seed_hotel(db, 930, "Hotel I Test")
    shift_id = _seed_open_shift_with_id(
        db,
        930,
        total_collected=40.0,
        transactions=[
            {
                "transaction_id": "TXN-I-1",
                "type": "payment",
                "booking_id": "BK-CASH-1",
                "amount": 40.0,
                "payment_method": "cash",
            },
        ],
    )
    # Pago estampado de OTRA reserva, método card → suma al desglose.
    db.reservation_payments.insert_one(
        {
            "booking_id": "BK-CARD-1",
            "prop_id": 930,
            "amount": 60.0,
            "method": "card",
            "status": "confirmed",
            "shift_id": ObjectId(shift_id),
            "paid_at": datetime.now(_UTC),
            "reference": "PAY-BK-CARD-1",
        }
    )
    # Pago estampado de la MISMA transacción cash → dedupe, no suma.
    _seed_stamped_payment(db, shift_id, booking_id="BK-CASH-1", amount=40.0)
    # Pago fallido → nunca entra al desglose.
    _seed_stamped_payment(db, shift_id, booking_id="BK-FAIL-1", amount=20.0, status="failed")

    row = list_open_shifts_overview()[0]
    bd = row["payment_breakdown"]
    assert bd["cash"] == 40.0
    assert bd["card"] == 60.0
    assert bd["transfer"] == 0.0
    assert bd["other"] == 0.0
    assert bd["total"] == 100.0
    assert row["total_collected"] == 100.0


@pytest.mark.asyncio
async def test_http_open_overview_requires_shifts_manage(client, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    response = await client.get("/api/reception/shifts/open-overview")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_http_open_overview_returns_hotel_names(client, admin_user, db):
    _seed_hotel(db, 927, "Hotel F Test")
    _seed_open_shift(db, 927, started_hours_ago=6)

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    response = await client.get("/api/reception/shifts/open-overview")

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(i["prop_id"] == 927 and i["hotel_name"] == "Hotel F Test" for i in items)
