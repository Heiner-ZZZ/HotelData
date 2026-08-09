"""Punto 2: evidence reconciliation for historical guest invoices."""
from __future__ import annotations

from bson import ObjectId

from src.app.modules.financial_reconciliation.service import build_reconciliation_report


def _invoice_findings(report: dict, invoice_id: ObjectId) -> list[dict]:
    return [
        finding
        for finding in report["findings"]
        if finding["domain"] == "invoice" and str(invoice_id) in finding["source_ids"]
    ]


def test_reconciliation_accepts_posted_historical_invoice_with_historical_ledger(db):
    """HINV uses historical_invoice evidence instead of duplicating invoice revenue."""
    prop_id = 840
    booking_id = "BK-P2-HISTORICAL-INVOICE"
    folio_id = db.guest_folios.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "status": "settled",
        "total_room": 100.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_due": 0.0,
        "total_payments": 100.0,
    }).inserted_id
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "folio_id": folio_id,
        "invoice_number": "HINV-FL-P2-0001",
        "source": "historical_reconstruction",
        "status": "paid",
        "accounting_status": "posted",
        "total": 100.0,
    }).inserted_id
    db.ledger_transactions.insert_many([
        {
            "prop_id": prop_id,
            "booking_id": booking_id,
            "source": "historical_invoice",
            "source_id": "HINV-FL-P2-0001",
            "journal_entry_id": "JE-P2-HIST-001",
            "debit": 100.0,
            "credit": 0.0,
        },
        {
            "prop_id": prop_id,
            "booking_id": booking_id,
            "source": "historical_invoice",
            "source_id": "HINV-FL-P2-0001",
            "journal_entry_id": "JE-P2-HIST-001",
            "debit": 0.0,
            "credit": 100.0,
        },
    ])

    report = build_reconciliation_report(prop_id)

    assert _invoice_findings(report, invoice_id) == []


def test_refund_reconciliation_records_domain_event_and_audit_trace(db):
    """Repairing a legacy refund must leave an idempotent event and audit row."""
    from src.app.modules.billing.service.lifecycle.refunds import ensure_refund_document_for_payment

    prop_id = 845
    payment_id = db.reservation_payments.insert_one({
        "prop_id": prop_id,
        "booking_id": "BK-P2-REFUND-TRACE",
        "status": "refunded",
        "amount": 5.0,
        "method": "card",
        "reference": "PAY-P2-REFUND-TRACE",
    }).inserted_id

    document = ensure_refund_document_for_payment(
        str(payment_id),
        changed_by="historical_reconciliation",
    )
    assert document is not None

    key = f"refund-reconciliation:v1:{payment_id}:PAY-P2-REFUND-TRACE"
    event = db.hotel_domain_events.find_one({"prop_id": prop_id, "idempotency_key": key})
    mirror = db.fact_hotel_domain_events.find_one({"_id": event["_id"]}) if event else None
    audit = db.audit_log.find_one({
        "prop_id": prop_id,
        "entity_type": "refund_reconciliation",
        "entity_id": str(payment_id),
        "metadata.idempotency_key": key,
    })

    assert event is not None
    assert event["event_type"] == "guest_ar.payment_refund.reconciled"
    assert mirror is not None
    assert audit is not None
    assert audit["metadata"]["refund_document_id"] == document["id"]


def test_invoice_backed_zero_value_refund_keeps_invoice_link_and_applied_trace(db):
    """A zero-value source invoice gets a receipt, not an unapplied refund."""
    from src.app.modules.billing.service.lifecycle.refunds import ensure_refund_document_for_payment

    prop_id = 849
    booking_id = "BK-P2-REFUND-ZERO-INVOICE"
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "invoice_number": "INV-P2-ZERO-REFUND",
        "status": "refunded",
        "total": 0.0,
    }).inserted_id
    payment_id = db.reservation_payments.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "invoice_id": invoice_id,
        "status": "refunded",
        "amount": 1.0,
        "method": "cash",
        "reference": "PAY-P2-ZERO-REFUND",
    }).inserted_id

    document = ensure_refund_document_for_payment(str(payment_id), changed_by="historical_reconciliation")

    assert document["document_type"] == "refund_receipt"
    assert document["invoice_id"] == str(invoice_id)
    stored_payment = db.reservation_payments.find_one({"_id": payment_id})
    assert stored_payment["reconciliation_status"] == "applied_refund"
    assert stored_payment["reconciliation_reason"] == "refunded_payment_with_zero_invoice_documented_receipt"
    assert db.fact_reservation_payments.find_one({"_id": payment_id})["reconciliation_status"] == "applied_refund"
    assert db.payment_reconciliation_events.count_documents({
        "payment_id": str(payment_id),
        "event": "classified_applied_refund",
    }) == 1


def test_reconciliation_does_not_accept_partial_historical_ledger_evidence(db):
    """A balanced but incomplete historical journal must remain a finding."""
    prop_id = 844
    booking_id = "BK-P2-HISTORICAL-PARTIAL"
    folio_id = db.guest_folios.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "status": "settled",
        "total_room": 100.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_due": 0.0,
    }).inserted_id
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "folio_id": folio_id,
        "invoice_number": "HINV-FL-P2-PARTIAL",
        "source": "historical_reconstruction",
        "status": "paid",
        "accounting_status": "posted",
        "total": 100.0,
    }).inserted_id
    db.ledger_transactions.insert_many([
        {"prop_id": prop_id, "booking_id": booking_id, "source": "historical_invoice", "source_id": "HINV-FL-P2-PARTIAL", "journal_entry_id": "JE-P2-PARTIAL", "debit": 1.0, "credit": 0.0},
        {"prop_id": prop_id, "booking_id": booking_id, "source": "historical_invoice", "source_id": "HINV-FL-P2-PARTIAL", "journal_entry_id": "JE-P2-PARTIAL", "debit": 0.0, "credit": 1.0},
    ])

    report = build_reconciliation_report(prop_id)

    assert _invoice_findings(report, invoice_id)


def test_reconciliation_flags_refunded_payment_without_refund_document_or_ledger(db):
    """A refunded payment needs its own compensating trace even with an invoice."""
    prop_id = 842
    booking_id = "BK-P2-REFUND-MISSING-DOCUMENT"
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "invoice_number": "INV-P2-REFUND-001",
        "status": "refunded",
        "total": 25.0,
    }).inserted_id
    payment_id = db.reservation_payments.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "invoice_id": invoice_id,
        "status": "refunded",
        "amount": 25.0,
        "method": "card",
        "reference": "PAY-P2-REFUND-001",
    }).inserted_id

    report = build_reconciliation_report(prop_id)

    findings = [
        finding for finding in report["findings"]
        if finding["domain"] == "payment" and str(payment_id) in finding["source_ids"]
    ]
    assert findings
    assert findings[0]["severity"] == "warning"


def test_reconciliation_accepts_refunded_payment_with_document_and_balanced_ledger(db):
    """A complete refund trace is not reported as a missing invoice/payment."""
    prop_id = 843
    booking_id = "BK-P2-REFUND-COMPLETE"
    payment_id = db.reservation_payments.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "status": "refunded",
        "amount": 25.0,
        "method": "card",
        "reference": "PAY-P2-REFUND-COMPLETE",
    }).inserted_id
    db.refund_documents.insert_one({
        "prop_id": prop_id,
        "payment_id": payment_id,
        "document_type": "refund_receipt",
        "status": "issued",
        "accounting_status": "posted",
    })
    db.reservation_payments.update_one(
        {"_id": payment_id},
        {"$set": {"reconciliation_status": "unapplied_refund"}},
    )
    db.ledger_transactions.insert_many([
        {
            "prop_id": prop_id,
            "source": "payment_refund",
            "source_id": "PAY-P2-REFUND-COMPLETE",
            "journal_entry_id": "JE-P2-REFUND-001",
            "debit": 25.0,
            "credit": 0.0,
        },
        {
            "prop_id": prop_id,
            "source": "payment_refund",
            "source_id": "PAY-P2-REFUND-COMPLETE",
            "journal_entry_id": "JE-P2-REFUND-001",
            "debit": 0.0,
            "credit": 25.0,
        },
    ])

    report = build_reconciliation_report(prop_id)

    assert not [
        finding for finding in report["findings"]
        if finding["domain"] == "payment" and str(payment_id) in finding["source_ids"]
    ]


def test_reconciliation_requires_explicit_unapplied_refund_classification(db):
    """A receipt and reversal are not enough without the explicit no-invoice state."""
    prop_id = 846
    payment_id = db.reservation_payments.insert_one({
        "prop_id": prop_id,
        "booking_id": "BK-P2-REFUND-UNAPPLIED-UNCLASSIFIED",
        "status": "refunded",
        "amount": 25.0,
        "method": "card",
        "reference": "PAY-P2-REFUND-UNCLASSIFIED",
    }).inserted_id
    db.refund_documents.insert_one({
        "prop_id": prop_id,
        "payment_id": payment_id,
        "document_type": "refund_receipt",
        "status": "issued",
        "accounting_status": "posted",
    })
    db.ledger_transactions.insert_many([
        {"prop_id": prop_id, "source": "payment_refund", "source_id": "PAY-P2-REFUND-UNCLASSIFIED", "journal_entry_id": "JE-P2-REFUND-UNCLASSIFIED", "debit": 25.0, "credit": 0.0},
        {"prop_id": prop_id, "source": "payment_refund", "source_id": "PAY-P2-REFUND-UNCLASSIFIED", "journal_entry_id": "JE-P2-REFUND-UNCLASSIFIED", "debit": 0.0, "credit": 25.0},
    ])

    report = build_reconciliation_report(prop_id)

    findings = [
        finding for finding in report["findings"]
        if finding["domain"] == "payment" and str(payment_id) in finding["source_ids"]
    ]
    assert findings
    assert findings[0]["actual"]["reconciliation_status"] is None


def test_reconciliation_does_not_trust_posted_historical_invoice_without_evidence(db):
    """A HINV marked posted without a folio/ledger trail remains a finding."""
    prop_id = 841
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": prop_id,
        "booking_id": "BK-P2-HISTORICAL-MISSING-EVIDENCE",
        "invoice_number": "HINV-FL-P2-MISSING",
        "source": "historical_reconstruction",
        "status": "paid",
        "accounting_status": "posted",
        "total": 100.0,
    }).inserted_id

    report = build_reconciliation_report(prop_id)

    findings = _invoice_findings(report, invoice_id)
    assert findings
    assert findings[0]["repair_policy"] == "idempotent_migration"


def test_new_positive_invoice_is_created_with_accounting_trace(db):
    """Live invoice creation records the same GL state used by backfills."""
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    prop_id = 848
    booking_id = "BK-P2-LIVE-INVOICE-TRACE"
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "Accounting Trace Guest",
        "line_items": [],
    })

    invoice = create_invoice(InvoiceCreate(
        booking_id=booking_id,
        subtotal=80.0,
        taxes=12.8,
    ))

    assert invoice["accounting_status"] == "posted"
    assert invoice["ledger_posting_status"] == "posted"
    assert len(invoice["ledger_references"]) == 1
    assert db.fact_reservation_invoices.find_one({"_id": ObjectId(invoice["id"])})["ledger_posting_status"] == "posted"
    assert db.ledger_transactions.count_documents({
        "prop_id": prop_id,
        "source": "invoice",
        "source_id": invoice["invoice_number"],
    }) == 3


def test_positive_invoice_accounting_repair_syncs_mirror_event_and_audit_without_duplicate_ledger(db):
    """A paid invoice with an existing complete journal gets the missing trace only."""
    from src.app.modules.billing.service.lifecycle.invoices import reconcile_positive_invoice_accounting

    prop_id = 847
    booking_id = "BK-P2-POSITIVE-INVOICE-TRACE"
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": prop_id,
        "booking_id": booking_id,
        "invoice_number": "INV-P2-POSITIVE-TRACE",
        "status": "paid",
        "total": 92.8,
        "accounting_status": None,
    }).inserted_id
    db.ledger_transactions.insert_many([
        {"prop_id": prop_id, "booking_id": booking_id, "source": "invoice", "source_id": "INV-P2-POSITIVE-TRACE", "journal_entry_id": "JE-P2-INVOICE-TRACE", "debit": 92.8, "credit": 0.0},
        {"prop_id": prop_id, "booking_id": booking_id, "source": "invoice", "source_id": "INV-P2-POSITIVE-TRACE", "journal_entry_id": "JE-P2-INVOICE-TRACE", "debit": 0.0, "credit": 92.8},
    ])

    result = reconcile_positive_invoice_accounting(str(invoice_id), changed_by="historical_reconciliation")
    again = reconcile_positive_invoice_accounting(str(invoice_id), changed_by="historical_reconciliation")

    assert result["accounting_status"] == "posted"
    assert result["ledger_posting_status"] == "posted"
    assert result["ledger_references"] == ["JE-P2-INVOICE-TRACE"]
    assert again["id"] == result["id"]
    assert db.ledger_transactions.count_documents({"source": "invoice", "source_id": "INV-P2-POSITIVE-TRACE"}) == 2
    mirror = db.fact_reservation_invoices.find_one({"_id": invoice_id})
    assert mirror["accounting_status"] == "posted"
    assert mirror["ledger_references"] == ["JE-P2-INVOICE-TRACE"]
    assert db.hotel_domain_events.count_documents({
        "prop_id": prop_id,
        "idempotency_key": f"invoice-accounting-reconciliation:v1:{invoice_id}",
    }) == 1
    assert db.audit_log.count_documents({
        "prop_id": prop_id,
        "entity_type": "guest_ar_invoice",
        "entity_id": str(invoice_id),
        "action": "accounting_reconciled",
    }) == 1
