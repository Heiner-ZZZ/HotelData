"""get_active_shift returns the UNIFIED drawer (2026-08).

The live-shift view (dashboard "Arqueo de Caja") used to receive only the raw
shift document, so ``payment_breakdown``/``total_collected`` reflected just
the ``transactions`` array — deposits and billing payments stamped with
``shift_id`` were invisible until close. ``get_active_shift`` now enriches
the payload with ``_unified_drawer``: the same drawer the close arqueo uses
(transactions check_out/payment + confirmed stamped payments, dedupe
incluido), plus ``stamped_payments_count`` for the UI to show the system
payments that came from billing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId

from src.app.modules.reception.shifts import get_active_shift

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, transactions: list[dict] | None = None) -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    res = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
            "transactions": transactions or [],
            "cash_initial": 100.0,
            "total_collected": 0.0,
        }
    )
    return str(res.inserted_id)


def _stamp_payment(db, shift_id: str, booking_id: str, amount: float, method: str = "cash") -> None:
    db.reservation_payments.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 1,
            "shift_id": ObjectId(shift_id),
            "amount": round(amount, 2),
            "method": method,
            "status": "confirmed",
            "paid_at": datetime.now(_UTC),
        }
    )


def _txn(txn_type: str, booking_id: str, amount: float, method: str = "cash") -> dict:
    return {
        "transaction_id": f"TXN-{booking_id}-{txn_type}",
        "type": txn_type,
        "booking_id": booking_id,
        "amount": round(amount, 2),
        "payment_method": method,
        "timestamp": _iso(datetime.now(_UTC)),
    }


def test_active_shift_includes_stamped_deposit_in_drawer(db):
    """El dashboard en vivo debe ver el depósito estampado: breakdown unificado
    ($45 cash) + total_collected ($45) + conteo de pagos de sistema (1)."""
    prop_id = 961
    shift_id = _open_shift(db, prop_id)
    _stamp_payment(db, shift_id, "BK-ACTIVE-961", 45.0, "cash")
    db.reception_shifts.update_one(
        {"_id": ObjectId(shift_id)},
        {"$push": {"transactions": _txn("check_in", "BK-ACTIVE-961", 205.0, "card")}},
    )

    shift = get_active_shift(prop_id)

    assert shift is not None
    assert shift["total_collected"] == 45.0
    assert shift["payment_breakdown"]["cash"] == 45.0
    assert shift["payment_breakdown"]["total"] == 45.0
    assert shift["stamped_payments_count"] == 1


def test_active_shift_unifies_checkout_and_stamped_midstay(db):
    """Check-out por transacción ($150 card) + pago mid-stay estampado
    ($100 card) → drawer $250, 1 pago de sistema."""
    prop_id = 962
    shift_id = _open_shift(
        db,
        prop_id,
        transactions=[_txn("check_out", "BK-OUT-962", 150.0, "card")],
    )
    _stamp_payment(db, shift_id, "BK-MID-962", 100.0, "card")

    shift = get_active_shift(prop_id)

    assert shift["total_collected"] == 250.0
    assert shift["payment_breakdown"]["card"] == 250.0
    assert shift["stamped_payments_count"] == 1


def test_active_shift_dedupes_payment_already_in_transactions(db):
    """Si el check-out ya registró la liquidación ($250 cash) y el pago
    estampado coincide, no se suma dos veces: stamped_payments_count = 0."""
    prop_id = 963
    shift_id = _open_shift(
        db,
        prop_id,
        transactions=[_txn("check_out", "BK-FULL-963", 250.0, "cash")],
    )
    _stamp_payment(db, shift_id, "BK-FULL-963", 250.0, "cash")

    shift = get_active_shift(prop_id)

    assert shift["total_collected"] == 250.0
    assert shift["payment_breakdown"]["cash"] == 250.0
    assert shift["stamped_payments_count"] == 0


def test_active_shift_without_money_returns_zero_drawer(db):
    prop_id = 964
    _open_shift(db, prop_id)

    shift = get_active_shift(prop_id)

    assert shift is not None
    assert shift["total_collected"] == 0.0
    assert shift["payment_breakdown"]["total"] == 0.0
    assert shift["stamped_payments_count"] == 0
