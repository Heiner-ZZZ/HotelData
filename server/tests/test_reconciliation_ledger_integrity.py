from src.app.modules.financial_reconciliation.service import build_reconciliation_report


def test_reconciliation_detects_orphan_and_duplicate_ledger_sources(db):
    db.dim_hotels.insert_one({"prop_id": 731, "display_name": "Ledger Integrity Hotel"})
    db.ledger_transactions.insert_many([
        {
            "prop_id": 731,
            "journal_entry_id": "JE-ORPHAN-001",
            "source": "invoice",
            "source_id": "INV-NOT-IN-MONGO",
            "debit": 50.0,
            "credit": 0.0,
        },
        {
            "prop_id": 731,
            "journal_entry_id": "JE-ORPHAN-001",
            "source": "invoice",
            "source_id": "INV-NOT-IN-MONGO",
            "debit": 0.0,
            "credit": 50.0,
        },
        {
            "prop_id": 731,
            "journal_entry_id": "JE-DUP-A",
            "source": "payment",
            "source_id": "PAY-DUPLICATED",
            "debit": 10.0,
            "credit": 0.0,
        },
        {
            "prop_id": 731,
            "journal_entry_id": "JE-DUP-B",
            "source": "payment",
            "source_id": "PAY-DUPLICATED",
            "debit": 0.0,
            "credit": 10.0,
        },
    ])

    report = build_reconciliation_report(731)

    messages = [finding["message"].lower() for finding in report["findings"] if finding["domain"] == "ledger"]
    assert any("huérfano" in message or "origen" in message for message in messages)
    assert any("journal" in message or "duplic" in message for message in messages)
