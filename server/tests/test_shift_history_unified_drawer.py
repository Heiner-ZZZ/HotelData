"""Historial y cash-control del manager usan el drawer unificado (2026-08).

``list_shifts`` (historial de turnos cerrados), ``get_shift`` (detalle) y
``list_shifts_for_cash_control`` (vista gerencial) ahora exponen el MISMO
drawer que el cierre y la vista en vivo: ``total_collected`` /
``payment_breakdown`` unificados (transacciones + pagos estampados con
``shift_id``, dedupe incluido) y ``stamped_payments_count``.

El cash-control además CORRIGE el arqueo en la respuesta: ``cash_expected`` /
``cash_over_short`` se recomputan con el breakdown unificado, para que los
cierres históricos cerrados antes del fix (que no veían los pagos estampados)
no muestren un sobrante/faltante falso. El doc guardado conserva el registro
original como audit trail.

La atribución por cajero ya existía en el cash-control (``payments`` con
``shift_employee``/``shift_opened_by`` + ``employee_summary`` agrupado por
responsable); estos tests la verifican contra el mismo set de pagos que el
drawer cuenta.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId

from src.app.modules.reception.shifts import (
    close_shift,
    get_shift,
    list_shifts,
    list_shifts_for_cash_control,
)

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, cash_initial: float = 100.0) -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    res = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": "Ana Recepción",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
            "transactions": [],
            "cash_initial": cash_initial,
            "total_collected": 0.0,
        }
    )
    return str(res.inserted_id)


def _stamp_payment(db, shift_id: str, booking_id: str, amount: float, method: str = "cash", prop_id: int = 1) -> None:
    db.reservation_payments.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            "shift_id": ObjectId(shift_id),
            "amount": round(amount, 2),
            "method": method,
            "status": "confirmed",
            "paid_at": datetime.now(_UTC),
            "shift_employee": "Ana Recepción",
            "shift_opened_by": "ana.recepcion",
            "shift_type": "morning",
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


# ── Historial de turnos cerrados (list_shifts) ─────────────────────────────


def test_list_shifts_history_exposes_unified_drawer(db):
    prop_id = 981
    shift_id = _open_shift(db, prop_id)
    _stamp_payment(db, shift_id, "BK-HIST-981", 45.0, "cash")
    db.reception_shifts.update_one(
        {"_id": ObjectId(shift_id)},
        {"$push": {"transactions": _txn("check_in", "BK-HIST-981", 205.0, "card")}},
    )
    close_shift(shift_id, cash_counted=145.0, closed_by="ana.recepcion")

    shifts = list_shifts(prop_id, status_filter="closed")

    assert len(shifts) == 1
    row = shifts[0]
    assert row["total_collected"] == 45.0
    assert row["payment_breakdown"]["cash"] == 45.0
    assert row["payment_breakdown"]["total"] == 45.0
    assert row["stamped_payments_count"] == 1


def test_get_shift_detail_exposes_unified_drawer(db):
    prop_id = 982
    shift_id = _open_shift(db, prop_id)
    _stamp_payment(db, shift_id, "BK-DET-982", 100.0, "card")
    close_shift(shift_id, cash_counted=100.0, closed_by="ana.recepcion")

    detail = get_shift(shift_id)

    assert detail is not None
    assert detail["total_collected"] == 100.0
    assert detail["payment_breakdown"]["card"] == 100.0
    assert detail["stamped_payments_count"] == 1


# ── Cash-control del manager: drawer + arqueo corregido + atribución ───────


def test_cash_control_has_unified_drawer_and_cashier_attribution(db):
    prop_id = 983
    shift_id = _open_shift(db, prop_id)
    _stamp_payment(db, shift_id, "BK-CC-983", 45.0, "cash", prop_id=prop_id)
    close_shift(shift_id, cash_counted=145.0, closed_by="ana.recepcion")

    rows = list_shifts_for_cash_control(prop_id)

    assert len(rows) == 1
    row = rows[0]
    # Drawer unificado
    assert row["total_collected"] == 45.0
    assert row["payment_breakdown"]["cash"] == 45.0
    assert row["stamped_payments_count"] == 1
    # Arqueo: esperado 145 (100 inicial + 45 estampados) → over/short 0
    assert row["cash_expected"] == 145.0
    assert row["cash_over_short"] == 0.0
    # Atribución por cajero: el pago aparece con su responsable
    assert len(row["payments"]) == 1
    assert row["payments"][0]["amount"] == 45.0
    assert row["payments"][0]["shift_employee"] == "Ana Recepción"
    # Resumen por empleado agrupado por el cajero que estampó
    assert row["employee_summary"] == [
        {
            "employee": "Ana Recepción",
            "count": 1,
            "total": 45.0,
            "cash": 45.0,
            "card": 0.0,
            "transfer": 0.0,
            "other": 0.0,
        }
    ]


def test_cash_control_corrects_legacy_close_that_missed_stamped_payments(db):
    """Cierre histórico (pre-fix) con over_short falso: el cash-control debe
    mostrar el esperado CORREGIDO con los pagos estampados, sin tocar el doc."""
    prop_id = 984
    # Simula un cierre viejo: guardó transacciones-only (esperado 100, sobrante
    # +45 falso) pero el pago de $45 estaba estampado con el shift_id.
    shift_oid = ObjectId()
    db.reception_shifts.insert_one(
        {
            "_id": shift_oid,
            "prop_id": prop_id,
            "status": "closed",
            "shift_type": "morning",
            "employee": "Ana Recepción",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=9)),
            "closed_at": _iso(datetime.now(_UTC) - timedelta(hours=8)),
            "transactions": [],
            "cash_initial": 100.0,
            "cash_counted": 145.0,
            "cash_expected": 100.0,
            "cash_over_short": 45.0,  # falso: no veía el depósito estampado
            "total_collected": 0.0,
            "payment_breakdown": {"cash": 0.0, "card": 0.0, "transfer": 0.0, "other": 0.0, "total": 0.0},
            "payment_ids": [],
            "folio_ids": [],
            "booking_ids": [],
        }
    )
    _stamp_payment(db, str(shift_oid), "BK-LEGACY-984", 45.0, "cash", prop_id=prop_id)

    rows = list_shifts_for_cash_control(prop_id)

    assert len(rows) == 1
    row = rows[0]
    assert row["cash_expected"] == 145.0
    assert row["cash_over_short"] == 0.0
    assert row["total_collected"] == 45.0
    assert row["payment_breakdown"]["cash"] == 45.0
    assert row["stamped_payments_count"] == 1
    # El doc guardado conserva su registro original (audit trail)
    stored = db.reception_shifts.find_one({"_id": shift_oid})
    assert stored["cash_over_short"] == 45.0
    assert stored["cash_expected"] == 100.0
