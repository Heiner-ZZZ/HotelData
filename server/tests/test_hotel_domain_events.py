"""Regression tests for the hotel-scoped financial domain event projection."""
from __future__ import annotations

from datetime import datetime, timezone


def test_domain_event_is_idempotent_and_mirrored(db):
    from src.app.modules.financial_reconciliation.domain_events import append_domain_event

    first = append_domain_event(
        prop_id=1,
        event_type="payment.confirmed",
        aggregate_type="guest_ar",
        aggregate_id="PAY-001",
        idempotency_key="payment-confirmed-PAY-001",
        payload={"amount": 100.0, "booking_id": "BK-001"},
        source_collection="reservation_payments",
        source_id="PAY-001",
    )
    second = append_domain_event(
        prop_id=1,
        event_type="payment.confirmed",
        aggregate_type="guest_ar",
        aggregate_id="PAY-001",
        idempotency_key="payment-confirmed-PAY-001",
        payload={"amount": 100.0, "booking_id": "BK-001"},
        source_collection="reservation_payments",
        source_id="PAY-001",
    )

    assert first["event_id"] == second["event_id"]
    assert db.hotel_domain_events.count_documents({"prop_id": 1}) == 1
    stored = db.hotel_domain_events.find_one({"prop_id": 1})
    assert db.fact_hotel_domain_events.find_one({"_id": stored["_id"]}) is not None
    assert stored["aggregate_type"] == "guest_ar"


def test_new_guest_ar_documents_emit_canonical_events(db):
    from src.app.modules.billing.schemas import InvoiceCreate, PaymentCreate
    from src.app.modules.billing.service.lifecycle import create_invoice, create_payment

    booking_id = "BK-EVENT-LIVE-001"
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "total_price": 116.0,
        "total_nights": 1,
        "guest_name": "Event Guest",
    })
    invoice = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=16.0))
    assert invoice is not None
    payment = create_payment(PaymentCreate(booking_id=booking_id, amount=116.0, invoice_id=invoice["id"], method="card"))
    assert payment is not None

    event_types = {
        row["event_type"]
        for row in db.hotel_domain_events.find({"prop_id": 1}, {"event_type": 1})
    }
    assert "guest_ar.invoice.issued" in event_types
    assert "guest_ar.payment.confirmed" in event_types


def test_rebuild_hotel_financial_aggregate_connects_ar_operations_ap_and_gl(db):
    from src.app.modules.financial_reconciliation.domain_events import rebuild_hotel_financial_aggregate

    now = datetime.now(timezone.utc)
    db.reservation_invoices.insert_one({
        "prop_id": 1,
        "invoice_number": "INV-AGG-001",
        "status": "issued",
        "total": 250.0,
        "created_at": now,
    })
    db.reservation_payments.insert_one({
        "prop_id": 1,
        "booking_id": "BK-AGG-001",
        "status": "confirmed",
        "amount": 100.0,
        "method": "card",
        "created_at": now,
    })
    db.guest_folios.insert_one({
        "prop_id": 1,
        "booking_id": "BK-AGG-001",
        "status": "open",
        "total_due": 150.0,
    })
    db.maintenance_tasks.insert_one({
        "prop_id": 1,
        "status": "completed",
        "actual_cost": 30.0,
    })
    db.expense_invoices.insert_one({
        "prop_id": 1,
        "status": "approved",
        "total": 80.0,
    })
    db.ledger_transactions.insert_many([
        {"prop_id": 1, "debit": 250.0, "credit": 0.0, "source": "invoice", "source_id": "INV-AGG-001"},
        {"prop_id": 1, "debit": 0.0, "credit": 250.0, "source": "invoice", "source_id": "INV-AGG-001"},
    ])

    result = rebuild_hotel_financial_aggregate(1)

    assert result["prop_id"] == 1
    assert result["guest_ar"]["invoiced"] == 250.0
    assert result["guest_ar"]["collected"] == 100.0
    assert result["guest_ar"]["outstanding_folios"] == 150.0
    assert result["operations"]["maintenance_cost"] == 30.0
    assert result["vendor_ap"]["approved"] == 80.0
    assert result["general_ledger"]["debit"] == 250.0
    assert result["general_ledger"]["credit"] == 250.0
    stored = db.hotel_financial_aggregates.find_one({"prop_id": 1})
    assert stored["guest_ar"]["outstanding_folios"] == 150.0


def test_backfill_domain_events_is_hotel_scoped_and_idempotent(db):
    from src.app.modules.financial_reconciliation.domain_events import backfill_domain_events

    db.reservation_invoices.insert_many([
        {"_id": __import__("bson").ObjectId(), "prop_id": 1, "status": "issued", "total": 10.0},
        {"_id": __import__("bson").ObjectId(), "prop_id": 2, "status": "issued", "total": 900.0},
    ])

    first = backfill_domain_events(1)
    second = backfill_domain_events(1)

    assert first["created"] >= 1
    assert second["created"] == 0
    assert db.hotel_domain_events.count_documents({"prop_id": 1}) == first["created"]
    assert db.hotel_domain_events.count_documents({"prop_id": 2}) == 0


def test_rebuild_aggregate_never_mix_hotel_data(db):
    from src.app.modules.financial_reconciliation.domain_events import rebuild_hotel_financial_aggregate

    db.reservation_invoices.insert_many([
        {"prop_id": 1, "status": "issued", "total": 10.0},
        {"prop_id": 2, "status": "issued", "total": 900.0},
    ])

    result = rebuild_hotel_financial_aggregate(1)

    assert result["guest_ar"]["invoiced"] == 10.0
    assert result["prop_id"] == 1
