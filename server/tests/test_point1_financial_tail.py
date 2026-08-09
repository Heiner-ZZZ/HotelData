"""Regression tests for the remaining Punto 1 financial tail repairs."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId


def _seed_booking(db, booking_id: str, *, total_price: float = 150.0) -> None:
    db.dim_hotels.insert_one({"prop_id": 1, "display_name": "Hotel Uno"})
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Reparación financiera",
        "guest_email": "repair@example.test",
        "total_price": total_price,
        "total_nights": 1,
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-02",
        "status": "confirmed",
        "stay_status": "checked_out",
        "created_at": datetime.now(timezone.utc),
    })


def test_reconcile_no_cost_maintenance_is_explicit_and_idempotent(db):
    from src.app.modules.housekeeping.service.lifecycle.maintenance import (
        reconcile_no_cost_maintenance,
    )

    room_id = db.hotel_rooms.insert_one({
        "prop_id": 1,
        "hotel_room_id": "HR-P1-NOCOST",
        "room_label": "P1",
        "room_type_id": "RT-P1",
    }).inserted_id
    task_id = db.maintenance_tasks.insert_one({
        "prop_id": 1,
        "room_id": room_id,
        "hotel_room_id": "HR-P1-NOCOST",
        "room_label": "P1",
        "title": "Inspección sin reparación",
        "status": "completed",
        "actual_cost": None,
        "expense_invoice_id": None,
        "ledger_journal_id": None,
    }).inserted_id

    first = reconcile_no_cost_maintenance(str(task_id), changed_by="historical_reconciliation")
    second = reconcile_no_cost_maintenance(str(task_id), changed_by="historical_reconciliation")

    assert first["financial_link_status"] == "no_cost_recorded"
    assert first["actual_cost"] == 0.0
    assert second["financial_link_status"] == "no_cost_recorded"
    stored = db.maintenance_tasks.find_one({"_id": task_id})
    assert stored["ledger_status"] == "not_applicable"
    assert stored["metadata"]["reconciliation"]["action"] == "classified_no_cost_recorded"
    assert db.maintenance_financial_reconciliations.count_documents({"task_id": str(task_id)}) == 1


def test_failed_payment_without_invoice_is_explicitly_informational(db):
    from src.app.modules.billing.service.lifecycle.payments import (
        classify_failed_payment_informational,
    )

    booking_id = "BK-P1-FAILED-INFORMATIVE"
    _seed_booking(db, booking_id)
    payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_id": None,
        "amount": 42.5,
        "method": "card",
        "status": "failed",
        "reference": "PAY-P1-FAILED-INFORMATIVE",
    }).inserted_id

    first = classify_failed_payment_informational(str(payment_id), changed_by="historical_reconciliation")
    second = classify_failed_payment_informational(str(payment_id), changed_by="historical_reconciliation")

    assert first["reconciliation_status"] == "informational"
    assert first["reconciliation_reason"] == "failed_payment_without_invoice_no_balance_effect"
    assert second["id"] == first["id"]
    assert db.fact_reservation_payments.find_one({"_id": payment_id})["reconciliation_status"] == "informational"
    assert db.payment_reconciliation_events.count_documents({"payment_id": str(payment_id)}) == 1


def test_refunded_payment_without_invoice_gets_formal_refund_receipt_and_ledger(db):
    from src.app.modules.billing.service.lifecycle.refunds import (
        ensure_refund_document_for_payment,
    )

    booking_id = "BK-P1-REFUND-DOCUMENT"
    _seed_booking(db, booking_id)
    payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_id": None,
        "amount": 150.0,
        "method": "card",
        "status": "refunded",
        "reference": "PAY-P1-REFUND-DOCUMENT",
        "paid_at": datetime.now(timezone.utc),
    }).inserted_id

    first = ensure_refund_document_for_payment(str(payment_id), changed_by="historical_reconciliation")
    second = ensure_refund_document_for_payment(str(payment_id), changed_by="historical_reconciliation")

    assert first["document_type"] == "refund_receipt"
    assert first["invoice_id"] is None
    assert first["amount"] == 150.0
    assert second["id"] == first["id"]
    stored_payment = db.reservation_payments.find_one({"_id": payment_id})
    assert stored_payment["refund_document_id"] == ObjectId(first["id"])
    assert stored_payment["reconciliation_status"] == "unapplied_refund"
    assert stored_payment["reconciliation_reason"] == "refunded_payment_without_invoice_documented_receipt"
    assert db.payment_reconciliation_events.count_documents({"payment_id": str(payment_id), "event": "classified_unapplied_refund"}) == 1
    assert db.refund_documents.count_documents({"payment_id": payment_id}) == 1
    assert db.fact_refund_documents.count_documents({"_id": ObjectId(first["id"])}) == 1
    rows = list(db.ledger_transactions.find({
        "source": "payment_refund",
        "source_id": "PAY-P1-REFUND-DOCUMENT",
    }))
    assert len(rows) == 2
    assert round(sum(float(row.get("debit", 0)) for row in rows), 2) == 150.0
    assert round(sum(float(row.get("credit", 0)) for row in rows), 2) == 150.0


def test_refund_flow_converts_paid_invoice_to_credit_note(db):
    from src.app.modules.billing.schemas import InvoiceCreate, PaymentCreate
    from src.app.modules.billing.service.lifecycle import create_invoice, create_payment, refund_payment

    booking_id = "BK-P1-REFUND-FLOW-CREDIT-NOTE"
    _seed_booking(db, booking_id, total_price=116.0)
    invoice = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=16.0))
    payment = create_payment(PaymentCreate(
        booking_id=booking_id,
        invoice_id=invoice["id"],
        amount=116.0,
        method="card",
    ))

    result = refund_payment(payment["id"], refund_id="RF-P1-FLOW")

    assert result["status"] == "refunded"
    document = db.refund_documents.find_one({"payment_id": ObjectId(payment["id"])})
    assert document["document_type"] == "credit_note"
    assert document["invoice_id"] == ObjectId(invoice["id"])
    assert db.reservation_invoices.find_one({"_id": ObjectId(invoice["id"])})["status"] == "refunded"


def test_cancelled_invoice_gets_credit_note_without_payment(db):
    from src.app.modules.billing.service.lifecycle.refunds import (
        create_credit_note_for_invoice,
    )

    booking_id = "BK-P1-CANCELLED-CREDIT-NOTE"
    _seed_booking(db, booking_id, total_price=116.0)
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_number": "INV-P1-CANCELLED-CREDIT-NOTE",
        "room_subtotal": 100.0,
        "extras_total": 0.0,
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "cancelled",
    }).inserted_id

    document = create_credit_note_for_invoice(str(invoice_id), changed_by="test")

    assert document["document_type"] == "credit_note"
    assert document["payment_id"] is None
    assert document["invoice_id"] == str(invoice_id)
    assert document["accounting_status"] == "posted"
    assert db.reservation_invoices.find_one({"_id": invoice_id})["credit_note_id"] == ObjectId(document["id"])


def test_refunded_payment_with_invoice_gets_credit_note(db):
    from src.app.modules.billing.service.lifecycle.refunds import (
        ensure_refund_document_for_payment,
    )

    booking_id = "BK-P1-CREDIT-NOTE"
    _seed_booking(db, booking_id, total_price=116.0)
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_number": "INV-P1-CREDIT-NOTE",
        "room_subtotal": 100.0,
        "extras_total": 0.0,
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "refunded",
    }).inserted_id
    payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_id": invoice_id,
        "amount": 116.0,
        "method": "card",
        "status": "refunded",
        "reference": "PAY-P1-CREDIT-NOTE",
    }).inserted_id

    document = ensure_refund_document_for_payment(str(payment_id), changed_by="test")

    assert document["document_type"] == "credit_note"
    assert document["invoice_id"] == str(invoice_id)
    assert document["original_invoice_number"] == "INV-P1-CREDIT-NOTE"
    assert document["accounting_status"] == "posted"
