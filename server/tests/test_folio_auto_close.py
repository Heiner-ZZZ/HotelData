"""Cierre automático del folio con saldo cero (TDD).

Contrato:
- ``close_folio`` debe cerrar también folios ``settled`` (pagados en su
  totalidad) con saldo 0 — no solo los ``open`` — para que el check-out con
  saldo cero termine con el folio en ``closed``.
- Un folio ``settled`` con saldo positivo sigue exigiendo excepción aprobada.
"""
from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId

import src.app.modules.reservations.service._checkinout._checkout as checkout_module
from src.app.modules.billing.schemas import PaymentCreate
from src.app.modules.billing.service.folio import close_folio
from src.app.modules.billing.service.lifecycle.payments import create_payment
from src.app.modules.reservations.service import complete_check_out

FIXED_CHECK_IN = "2026-08-14"
FIXED_CHECK_OUT = "2026-08-15"


def _seed_booking(db, booking_id: str, *, prop_id: int = 993) -> None:
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "Auto Close Guest",
        "guest_email": "autoclose@test.com",
        "check_in_date": FIXED_CHECK_IN,
        "check_out_date": FIXED_CHECK_OUT,
        "total_price": 218.0,
        "currency": "USD",
        "total_nights": 2,
        "rooms": 1,
        "assigned_rooms": [],
        "status": "confirmed",
        "stay_status": "checked_in",
        "is_test": False,
    })


def _seed_folio(db, booking_id: str, *, status: str = "open", due: float = 218.0) -> None:
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 993,
        "folio_number": f"FL-AC-{booking_id}",
        "status": status,
        "total_charges": due,
        "total_discounts": 0.0,
        "total_payments": 0.0 if status == "open" else due,
        "total_due": due,
        "postings": [],
        "posting_count": 0,
    })


def _seed_policy(db, *, prop_id: int = 993) -> None:
    db.hotel_policies.insert_one({
        "prop_id": prop_id,
        "room_type_id": "",
        "rate_plan_id": "",
        "season_id": "",
        "check_in_time": "15:00",
        "check_out_time": "12:00",
        "late_checkout_enabled": True,
        "late_checkout_courtesy_minutes": 60,
        "late_checkout_default_fee": 0.0,
    })


def _seed_open_shift(db, *, prop_id: int = 993) -> str:
    result = db.reception_shifts.insert_one({
        "prop_id": prop_id,
        "status": "open",
        "shift_type": "morning",
        "employee": "Carlos Pérez",
        "opened_by": "recep.prueba",
        "start_time": datetime.now(UTC).isoformat(),
        "cash_initial": 100.0,
        "total_collected": 0.0,
        "transactions": [],
    })
    return str(result.inserted_id)


def _freeze_clock(monkeypatch, *, hour: int, minute: int) -> None:
    frozen = datetime(2026, 8, 15, hour, minute, tzinfo=UTC)
    monkeypatch.setattr(checkout_module, "local_today", lambda: FIXED_CHECK_OUT)
    monkeypatch.setattr(checkout_module, "local_now", lambda: frozen, raising=False)


def test_close_folio_closes_settled_folio_with_zero_balance(db):
    """Al emitir factura con folio liquidado (settled, saldo 0) se cierra."""
    _seed_folio(db, "BK-AC-SETTLED", status="settled", due=0.0)
    invoice_id = ObjectId()

    result = close_folio(
        "BK-AC-SETTLED",
        invoice_id=invoice_id,
        closed_by="recep.prueba",
    )

    assert result is not None
    assert result["status"] == "closed"
    folio = db.guest_folios.find_one({"booking_id": "BK-AC-SETTLED"})
    assert folio["status"] == "closed"
    assert folio["closed_by"] == "recep.prueba"
    assert folio["invoice_id"] == invoice_id
    assert folio["closed_at"] is not None


def test_close_folio_keeps_settled_folio_open_with_positive_balance(db):
    """Un folio settled con saldo positivo no se cierra sin excepción aprobada."""
    _seed_folio(db, "BK-AC-SETTLED-DUE", status="settled", due=50.0)

    result = close_folio("BK-AC-SETTLED-DUE", closed_by="recep.prueba")

    assert result is None
    assert db.guest_folios.find_one({"booking_id": "BK-AC-SETTLED-DUE"})["status"] == "settled"


def test_checkout_closes_folio_settled_by_full_payment(db, monkeypatch):
    """Check-out con saldo cero: el folio pagado (auto-settled) termina closed."""
    _seed_policy(db)
    _seed_booking(db, "BK-AC-CHECKOUT")
    _seed_folio(db, "BK-AC-CHECKOUT", status="open", due=218.0)
    _seed_open_shift(db)
    _freeze_clock(monkeypatch, hour=11, minute=0)  # modo normal, sin fee late

    payment = create_payment(PaymentCreate(
        booking_id="BK-AC-CHECKOUT",
        amount=218.0,
        method="card",
    ))
    assert payment is not None
    assert payment["status"] == "confirmed"
    assert db.guest_folios.find_one({"booking_id": "BK-AC-CHECKOUT"})["status"] == "settled"

    result = complete_check_out(
        "BK-AC-CHECKOUT",
        changed_by="recep.prueba",
        keys_returned=True,
    )

    assert result["stay_status"] == "checked_out"
    folio = db.guest_folios.find_one({"booking_id": "BK-AC-CHECKOUT"})
    assert folio["status"] == "closed"
    assert folio["closed_by"] == "recep.prueba"
