"""Alineación de la factura de estadía con los eventos de ciclo de vida.

Invariante: la factura de estadía solo permanece vigente mientras el importe
que refleja siga siendo lo que corresponde cobrar. Cuando la estadía NO ocurre
(no-show o cancelación con penalización), la factura emitida al confirmar se
ANULA — nunca queda "pendiente de pago" un monto que ya no corresponde
(regresión: $188 pagables cuando la penalización real era $47.94).

Regla de seguridad: solo se anulan facturas SIN pagos confirmados; si el
huésped ya pagó algo, la anulación no es automática (requiere gestión manual:
reembolso / crédito).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.modules.reservations.service.cleanup import cancel_booking
from src.app.modules.reservations.service.no_show import process_no_show


def _seed_booking(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Lifecycle Guest",
        "guest_email": "lifecycle@test.com",
        "room_type_id": "RT-1-deluxe",
        "rate_plan_id": "RP-1-advance",
        "check_in_date": "2026-08-20",
        "check_out_date": "2026-08-22",
        "rooms": 1,
        "total_nights": 2,
        "total_price": 188.0,
        "currency": "USD",
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc),
        "is_test": True,
    }
    doc.update(overrides)
    db.booking_orders.insert_one(doc)


def _seed_invoice(db, booking_id: str, **overrides) -> str:
    doc = {
        "invoice_number": "INV-LIFE-0001",
        "booking_id": booking_id,
        "prop_id": 1,
        "subtotal": 162.07,
        "room_subtotal": 162.07,
        "extras_total": 0.0,
        "taxes": 25.93,
        "total": 188.0,
        "status": "issued",
        "line_items": [],
        "issued_at": datetime.now(timezone.utc),
    }
    doc.update(overrides)
    return str(db.reservation_invoices.insert_one(doc).inserted_id)


def _seed_payment(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "invoice_id": None,
        "amount": 188.0,
        "method": "bank_transfer",
        "status": "confirmed",
        "reference": "PAY-LIFE-1",
        "paid_at": datetime.now(timezone.utc),
    }
    doc.update(overrides)
    db.reservation_payments.insert_one(doc)


def test_no_show_cancels_stay_invoice(db):
    """No-show: la factura de estadía emitida al confirmar se anula."""
    booking_id = "BK-LIFE-NOSHOW"
    _seed_booking(db, booking_id, stay_status="pending")
    _seed_invoice(db, booking_id)

    result = process_no_show(booking_id, changed_by="no_show_scheduler")

    assert result["ok"] is True
    inv = db.reservation_invoices.find_one({"booking_id": booking_id})
    assert inv is not None
    assert inv["status"] == "cancelled"
    assert "no-show" in (inv.get("cancel_reason") or "").lower()


def test_no_show_keeps_invoice_when_paid(db):
    """No-show con factura YA pagada: NO se anula en silencio (gestión manual)."""
    booking_id = "BK-LIFE-NOSHOW-PAID"
    _seed_booking(db, booking_id, stay_status="pending")
    _seed_invoice(db, booking_id)
    _seed_payment(db, booking_id)

    process_no_show(booking_id, changed_by="no_show_scheduler")

    inv = db.reservation_invoices.find_one({"booking_id": booking_id})
    assert inv["status"] == "issued"


def test_no_show_keeps_already_cancelled_invoice(db):
    """Idempotente: factura ya anulada (o inexistente) → no-op, no revierte."""
    booking_id = "BK-LIFE-NOSHOW-2"
    _seed_booking(db, booking_id, stay_status="pending")
    _seed_invoice(db, booking_id, status="cancelled", cancel_reason="anulada manualmente")

    process_no_show(booking_id, changed_by="no_show_scheduler")

    inv = db.reservation_invoices.find_one({"booking_id": booking_id})
    assert inv["status"] == "cancelled"
    assert inv.get("cancel_reason") == "anulada manualmente"


def test_cancel_booking_cancels_stay_invoice(db):
    """Cancelación (con o sin penalización): la factura de estadía se anula."""
    booking_id = "BK-LIFE-CANCEL"
    _seed_booking(db, booking_id, status="pending", check_in_date="2099-01-10", check_out_date="2099-01-12")
    _seed_invoice(db, booking_id)

    result = cancel_booking(booking_id, reason="cancelled_by_user", changed_by="web")

    assert result["status"] == "cancelled"
    inv = db.reservation_invoices.find_one({"booking_id": booking_id})
    assert inv["status"] == "cancelled"
    assert "cancel" in (inv.get("cancel_reason") or "").lower()


def test_cancel_booking_keeps_invoice_when_paid(db):
    """Cancelación con factura YA pagada: NO se anula en silencio."""
    booking_id = "BK-LIFE-CANCEL-PAID"
    _seed_booking(db, booking_id, status="pending", check_in_date="2099-01-10", check_out_date="2099-01-12")
    _seed_invoice(db, booking_id)
    _seed_payment(db, booking_id)

    cancel_booking(booking_id, reason="cancelled_by_user", changed_by="web")

    inv = db.reservation_invoices.find_one({"booking_id": booking_id})
    assert inv["status"] == "issued"
