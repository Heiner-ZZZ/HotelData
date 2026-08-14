"""Manager cash-control must expose the responsible cashier per payment.

Closed shifts carry ``payment_ids`` (payments collected in the shift window).
The manager cash-control view (``list_shifts_for_cash_control``) must resolve
those payments and expose their shift attribution (``shift_employee`` /
``shift_opened_by`` / ``shift_type``) so the UI can render a "Responsable"
column per payment.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _seed_closed_shift(db, prop_id: int = 940) -> str:
    # ``reception_shifts`` is never cleaned by conftest — clear the prop first
    # so the assertion is hermetic across runs.
    db.reception_shifts.delete_many({"prop_id": prop_id})
    result = db.reception_shifts.insert_one({
        "prop_id": prop_id,
        "status": "closed",
        "shift_type": "morning",
        "employee": "Teller Demo",
        "opened_by": "admin_test",
        "start_time": _iso(datetime.now(_UTC) - timedelta(hours=9)),
        "closed_at": _iso(datetime.now(_UTC) - timedelta(hours=1)),
        "end_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
        "cash_initial": 100.0,
        "cash_counted": 150.0,
        "cash_over_short": 0.0,
        "total_collected": 50.0,
        "transactions": [],
        "payment_ids": [],
    })
    return str(result.inserted_id)


def test_cash_control_exposes_responsible_per_payment(db):
    from src.app.modules.reception.shifts import list_shifts_for_cash_control

    shift_id = _seed_closed_shift(db)
    pay1 = db.reservation_payments.insert_one({
        "prop_id": 940,
        "booking_id": "BK-RESP-1",
        "amount": 30.0,
        "method": "cash",
        "reference": "REF-1",
        "paid_at": datetime.now(_UTC) - timedelta(hours=2),
        "status": "confirmed",
        "shift_id": ObjectId(),
        "shift_employee": "Carlos Pérez",
        "shift_opened_by": "gerente1",
        "shift_type": "morning",
    }).inserted_id
    pay2 = db.reservation_payments.insert_one({
        "prop_id": 940,
        "booking_id": "BK-RESP-2",
        "amount": 20.0,
        "method": "card",
        "reference": "REF-2",
        "paid_at": datetime.now(_UTC) - timedelta(hours=1),
        "status": "confirmed",
    }).inserted_id
    db.reception_shifts.update_one(
        {"_id": ObjectId(shift_id)},
        {"$set": {"payment_ids": [pay1, pay2]}},
    )

    shifts = list_shifts_for_cash_control(prop_id=940)

    assert len(shifts) == 1
    payments = shifts[0]["payments"]
    assert len(payments) == 2
    by_ref = {p["reference"]: p for p in payments}
    stamped = by_ref["REF-1"]
    assert stamped["shift_employee"] == "Carlos Pérez"
    assert stamped["shift_opened_by"] == "gerente1"
    assert stamped["shift_type"] == "morning"
    unstamped = by_ref["REF-2"]
    assert unstamped["shift_employee"] is None
    assert unstamped["shift_opened_by"] is None


def test_cash_control_shift_without_payments_has_empty_list(db):
    from src.app.modules.reception.shifts import list_shifts_for_cash_control

    _seed_closed_shift(db)

    shifts = list_shifts_for_cash_control(prop_id=940)

    assert len(shifts) == 1
    assert shifts[0]["payments"] == []


# ── Employee summary (estampado vs depositado) ────────────────────────────


def _stamp_payment(db, shift_id: str, *, amount: float, method: str, employee=None, opened_by=None, status="confirmed"):
    """Insert a payment stamped on the given shift (FK attribution)."""
    return db.reservation_payments.insert_one({
        "prop_id": 940,
        "booking_id": f"BK-SUM-{amount}-{method}",
        "amount": amount,
        "method": method,
        "reference": f"REF-SUM-{amount}-{method}",
        "paid_at": datetime.now(_UTC) - timedelta(hours=1),
        "status": status,
        "shift_id": ObjectId(shift_id),
        "shift_employee": employee,
        "shift_opened_by": opened_by,
        "shift_type": "morning",
    }).inserted_id


def test_cash_control_employee_summary_groups_stamped_payments_by_cashier(db):
    """Summary groups the shift's confirmed stamped payments by responsible
    cashier (employee label, fallback to opener), with per-method totals."""
    from src.app.modules.reception.shifts import list_shifts_for_cash_control

    shift_id = _seed_closed_shift(db)
    _stamp_payment(db, shift_id, amount=50.0, method="cash", employee="Carlos Pérez", opened_by="gerente1")
    _stamp_payment(db, shift_id, amount=30.0, method="card", employee="Carlos Pérez", opened_by="gerente1")
    _stamp_payment(db, shift_id, amount=20.0, method="cash", employee="María López", opened_by="maria")
    # Sin atribución (legacy sin estampa) — se agrupa aparte para detectar
    # discrepancias entre lo estampado y lo depositado.
    _stamp_payment(db, shift_id, amount=10.0, method="cash", employee=None, opened_by=None)
    # Fallido/fallido NO cuenta en lo estampado.
    _stamp_payment(db, shift_id, amount=999.0, method="cash", employee="Carlos Pérez", status="failed")

    shifts = list_shifts_for_cash_control(prop_id=940)

    assert len(shifts) == 1
    summary = shifts[0]["employee_summary"]
    assert [g["employee"] for g in summary] == ["Carlos Pérez", "María López", "Sin atribución"]
    carlos = summary[0]
    assert carlos["count"] == 2
    assert carlos["total"] == 80.0
    assert carlos["cash"] == 50.0
    assert carlos["card"] == 30.0
    assert carlos["transfer"] == 0.0
    maria = summary[1]
    assert maria["count"] == 1
    assert maria["total"] == 20.0
    assert maria["cash"] == 20.0
    unattr = summary[2]
    assert unattr["count"] == 1
    assert unattr["total"] == 10.0


def test_cash_control_employee_summary_falls_back_to_opener_and_tracks_other_methods(db):
    """Payments without an employee label fall back to the opener, and
    methods outside cash/card/transfer land in ``other``."""
    from src.app.modules.reception.shifts import list_shifts_for_cash_control

    shift_id = _seed_closed_shift(db)
    _stamp_payment(db, shift_id, amount=40.0, method="cash", employee=None, opened_by="gerente1")
    _stamp_payment(db, shift_id, amount=7.5, method="simulated", employee="Carlos Pérez", opened_by="gerente1")

    shifts = list_shifts_for_cash_control(prop_id=940)

    summary = shifts[0]["employee_summary"]
    by_name = {g["employee"]: g for g in summary}
    # Fallback: employee label ausente → opener.
    assert by_name["gerente1"]["total"] == 40.0
    assert by_name["gerente1"]["cash"] == 40.0
    assert by_name["Carlos Pérez"]["total"] == 7.5
    assert by_name["Carlos Pérez"]["other"] == 7.5


def test_cash_control_employee_summary_empty_when_no_stamped_payments(db):
    from src.app.modules.reception.shifts import list_shifts_for_cash_control

    _seed_closed_shift(db)

    shifts = list_shifts_for_cash_control(prop_id=940)

    assert shifts[0]["employee_summary"] == []
