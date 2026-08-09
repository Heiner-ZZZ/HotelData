from src.app.modules.financial_reconciliation.service import build_reconciliation_report


def test_cancelled_positive_invoice_requires_manual_review_not_backfill(db):
    db.dim_hotels.insert_one({"prop_id": 706, "display_name": "Cancelled Invoice Hotel"})
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": 706,
        "invoice_number": "INV-CANCELLED-POSITIVE",
        "total": 150.0,
        "status": "cancelled",
    }).inserted_id

    report = build_reconciliation_report(706)

    invoice_findings = [
        finding for finding in report["findings"]
        if finding["domain"] == "invoice" and str(invoice_id) in finding["source_ids"]
    ]
    assert invoice_findings
    assert all(finding["repair_policy"] == "manual" for finding in invoice_findings)
    assert all("cancel" in finding["message"].lower() or "reembols" in finding["message"].lower() for finding in invoice_findings)


def test_reconciled_cancelled_invoice_is_removed_from_manual_findings(db):
    db.dim_hotels.insert_one({"prop_id": 707, "display_name": "Reconciled Invoice Hotel"})
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": 707,
        "invoice_number": "INV-CANCELLED-RECONCILED",
        "total": 150.0,
        "status": "cancelled",
        "recognized_total": 0.0,
        "accounting_status": "reversed",
    }).inserted_id
    db.ledger_transactions.insert_many([
        {"prop_id": 707, "source": "invoice_reversal", "source_id": "INV-CANCELLED-RECONCILED", "debit": 150.0, "credit": 0.0},
        {"prop_id": 707, "source": "invoice_reversal", "source_id": "INV-CANCELLED-RECONCILED", "debit": 0.0, "credit": 150.0},
    ])

    report = build_reconciliation_report(707)

    assert not [
        finding for finding in report["findings"]
        if finding["domain"] == "invoice" and str(invoice_id) in finding["source_ids"]
    ]
