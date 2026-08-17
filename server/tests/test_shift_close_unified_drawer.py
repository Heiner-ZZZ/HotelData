"""Close-shift arqueo uses the UNIFIED drawer (2026-08).

``close_shift`` used to compute ``total_collected``, the per-method breakdown
and ``cash_expected`` ONLY from the shift's ``transactions`` array (the
movements registered via ``register_transaction``). Payments created by the
billing module — deposits on walk-in reservations, mid-stay folio settlements,
pos-charges — are stamped with ``shift_id`` but never push a shift
transaction, so the close arqueo expected less money than the cashier
physically collected → a false over/short at close.

The fix reuses ``_stamped_drawer_breakdown`` (same logic as
``list_open_shifts_overview``): the drawer = transactions (check_out/payment)
+ confirmed payments stamped with this exact ``shift_id``, deduplicating the
payment already represented as a check_out/payment transaction by
booking_id + amount. Only ``confirmed`` payments count.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId

from src.app.modules.reception.shifts import close_shift

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, transactions: list[dict] | None = None, cash_initial: float = 100.0) -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    res = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
            "transactions": transactions or [],
            "cash_initial": cash_initial,
        }
    )
    return str(res.inserted_id)


def _stamp_payment(db, shift_id: str, booking_id: str, amount: float, method: str = "cash", *, status: str = "confirmed") -> None:
    db.reservation_payments.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 1,
            "shift_id": ObjectId(shift_id),
            "amount": round(amount, 2),
            "method": method,
            "status": status,
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


# ── Depósito de reserva walk-in (solo estampado, sin transacción) ──────────


def test_close_includes_stamped_deposit_from_walkin_creation(db):
    """Depósito cobrado en la creación de la reserva entra al arqueo.

    El flujo real: depósito $45 cash estampado en ``reservation_payments``
    + check-in que registra una transacción informativa (type=check_in, que
    el arqueo NO suma). Al cerrar, el drawer debe ver los $45.
    """
    prop_id = 971
    shift_id = _open_shift(db, prop_id)
    _stamp_payment(db, shift_id, "BK-DEP-971", 45.0, "cash")
    # check_in es informativo: no cuenta en total_collected del cierre
    db.reception_shifts.update_one(
        {"_id": ObjectId(shift_id)},
        {"$push": {"transactions": _txn("check_in", "BK-DEP-971", 205.0, "card")}},
    )

    result = close_shift(shift_id, cash_counted=145.0, closed_by="recep_test")

    assert result["total_collected"] == 45.0
    assert result["payment_breakdown"]["cash"] == 45.0
    assert result["payment_breakdown"]["total"] == 45.0
    # Caja física: 100 inicial + 45 del depósito → over/short cero
    assert result["cash_expected"] == 145.0
    assert result["cash_difference"] == 0.0


# ── Pago de billing mid-stay (estampado) + check-out ───────────────────────


def test_close_includes_midstay_billing_payment_and_does_not_double_count(db):
    """Pago de folio mid-stay ($100 card, estampado) + check-out ($150 card
    vía transacción) → el cierre espera $250, sin duplicar."""
    prop_id = 972
    shift_id = _open_shift(
        db,
        prop_id,
        transactions=[
            _txn("check_out", "BK-OUT-972", 150.0, "card"),
        ],
    )
    _stamp_payment(db, shift_id, "BK-MID-972", 100.0, "card")

    result = close_shift(shift_id, cash_counted=100.0, closed_by="recep_test")

    assert result["total_collected"] == 250.0
    assert result["payment_breakdown"]["card"] == 250.0
    assert result["payment_breakdown"]["cash"] == 0.0
    assert result["payment_breakdown"]["total"] == 250.0


def test_close_dedupes_payment_already_represented_as_checkout_transaction(db):
    """Si el check-out ya registró la liquidación completa como transacción
    ($250 cash) y el pago estampado coincide (booking + monto), NO se suma
    dos veces."""
    prop_id = 973
    shift_id = _open_shift(
        db,
        prop_id,
        transactions=[
            _txn("check_out", "BK-FULL-973", 250.0, "cash"),
        ],
    )
    _stamp_payment(db, shift_id, "BK-FULL-973", 250.0, "cash")

    result = close_shift(shift_id, cash_counted=350.0, closed_by="recep_test")

    assert result["total_collected"] == 250.0
    assert result["payment_breakdown"]["cash"] == 250.0
    assert result["payment_breakdown"]["total"] == 250.0
    assert result["cash_expected"] == 350.0
    assert result["cash_difference"] == 0.0


# ── Solo dinero confirmado cuenta ──────────────────────────────────────────


def test_close_ignores_failed_payments(db):
    """Un pago failed/rechazado nunca entró a la caja: no suma al drawer."""
    prop_id = 974
    shift_id = _open_shift(db, prop_id)
    _stamp_payment(db, shift_id, "BK-FAIL-974", 75.0, "cash", status="failed")
    _stamp_payment(db, shift_id, "BK-OK-974", 30.0, "cash")

    result = close_shift(shift_id, cash_counted=130.0, closed_by="recep_test")

    assert result["total_collected"] == 30.0
    assert result["payment_breakdown"]["cash"] == 30.0
    assert result["cash_expected"] == 130.0
    assert result["cash_difference"] == 0.0


# ── Sin pagos ni transacciones de dinero ───────────────────────────────────


def test_close_without_money_keeps_expected_cash_at_initial(db):
    prop_id = 975
    shift_id = _open_shift(db, prop_id)

    result = close_shift(shift_id, cash_counted=100.0, closed_by="recep_test")

    assert result["total_collected"] == 0.0
    assert result["payment_breakdown"]["total"] == 0.0
    assert result["cash_expected"] == 100.0
    assert result["cash_difference"] == 0.0
