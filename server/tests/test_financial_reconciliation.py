"""Hotel-scoped, read-only financial reconciliation contract tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson.decimal128 import Decimal128
from httpx import AsyncClient

from src.app.modules.financial_reconciliation.service import build_reconciliation_report

pytestmark = pytest.mark.asyncio


@pytest.fixture
def reconciliation_fixture(db):
    """Create isolated evidence for findings without granting write access."""
    now = datetime.now(timezone.utc)
    booking_id = "BK-REC-001"
    db.dim_hotels.insert_one({"prop_id": 701, "display_name": "Reconciliation Hotel", "published": True})
    db.booking_orders.insert_one({"booking_id": booking_id, "prop_id": 701, "created_at": now})
    folio_id = db.guest_folios.insert_one({
        "prop_id": 701,
        "booking_id": booking_id,
        "status": "closed",
        "total_due": 25.50,
        "created_at": now,
    }).inserted_id
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": 701,
        "booking_id": booking_id,
        "invoice_number": "INV-REC-001",
        "total": 100.00,
        "status": "paid",
    }).inserted_id
    payment_id = db.reservation_payments.insert_one({
        "prop_id": 701,
        "booking_id": booking_id,
        "invoice_id": None,
        "amount": 100.00,
        "status": "confirmed",
    }).inserted_id
    db.ledger_transactions.insert_one({
        "prop_id": 701,
        "journal_entry_id": "JE-REC-001",
        "source": "invoice",
        "source_id": "OTHER-INVOICE",
        "debit": 10.00,
        "credit": 0.00,
    })
    db.ledger_transactions.insert_one({
        "prop_id": 701,
        "journal_entry_id": "JE-REC-001",
        "source": "invoice",
        "source_id": "OTHER-INVOICE",
        "debit": 0.00,
        "credit": 9.00,
    })
    return {
        "folio_id": str(folio_id),
        "invoice_id": str(invoice_id),
        "payment_id": str(payment_id),
    }


async def test_report_detects_decimal128_ledger_imbalance_and_stale_payment(db, reconciliation_fixture):
    db.ledger_transactions.delete_many({"prop_id": 701})
    db.ledger_transactions.insert_many([
        {
            "prop_id": 701,
            "journal_entry_id": "JE-DECIMAL-001",
            "source": "invoice",
            "source_id": "INV-REC-001",
            "debit": Decimal128("100.00"),
            "credit": Decimal128("0.00"),
        },
        {
            "prop_id": 701,
            "journal_entry_id": "JE-DECIMAL-001",
            "source": "invoice",
            "source_id": "INV-REC-001",
            "debit": Decimal128("0.00"),
            "credit": Decimal128("99.00"),
        },
    ])
    db.reservation_payments.insert_one({
        "prop_id": 701,
        "booking_id": "BK-REC-001",
        "invoice_id": "000000000000000000000099",
        "amount": Decimal128("10.00"),
        "status": "confirmed",
    })

    report = build_reconciliation_report(701)
    assert report["summary"]["ledger"]["debit"] == 100.0
    assert report["summary"]["ledger"]["credit"] == 99.0
    assert any(f["domain"] == "ledger" for f in report["findings"])
    assert any(f["domain"] == "payment" and "inexistente" in f["message"] for f in report["findings"])
    assert any(f["domain"] == "invoice" and "importe" in f["message"] for f in report["findings"])


async def test_report_is_hotel_scoped_and_exposes_stable_findings(db, reconciliation_fixture):
    report = build_reconciliation_report(701)

    assert report["prop_id"] == 701
    assert report["summary"]["total_findings"] >= 3
    assert {finding["domain"] for finding in report["findings"]} >= {"folio", "payment", "invoice", "ledger"}
    assert all(finding["resolution"] == "pending" for finding in report["findings"])
    assert all(finding["repair_policy"] in {"manual", "idempotent_migration", "not_repairable"} for finding in report["findings"])
    assert all("finding_id" in finding and finding["finding_id"].startswith("REC-") for finding in report["findings"])

    # A document from another hotel must never influence the report.
    db.guest_folios.insert_one({"prop_id": 702, "status": "closed", "total_due": 9999})
    db.reservation_invoices.insert_one({"prop_id": 702, "invoice_number": "INV-OTHER", "total": 9999})
    db.reservation_payments.insert_one({"prop_id": 702, "invoice_id": "INV-OTHER", "status": "confirmed", "amount": 9999})
    db.ledger_transactions.insert_one({"prop_id": 702, "debit": 9999, "credit": 0, "source": "invoice", "source_id": "INV-OTHER"})
    db.additional_charges.insert_one({"prop_id": 702, "booking_id": "BK-OTHER", "amount": 9999})
    db.maintenance_tasks.insert_one({"prop_id": 702, "status": "scheduled"})
    scoped_again = build_reconciliation_report(701)
    assert scoped_again["summary"] == report["summary"]


async def test_reconciliation_endpoint_requires_hotel_access_and_is_read_only(
    client: AsyncClient, admin_user, db, reconciliation_fixture
):
    login = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    assert login.status_code == 200, login.text

    before = {
        name: db[name].count_documents({})
        for name in ("guest_folios", "reservation_invoices", "reservation_payments", "ledger_transactions")
    }
    response = await client.get("/api/hotels/701/reconciliation/summary")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prop_id"] == 701
    assert body["summary"]["total_findings"] >= 3
    assert body["as_of"]
    after = {
        name: db[name].count_documents({})
        for name in before
    }
    assert after == before


async def test_reconciliation_endpoint_returns_404_for_unknown_hotel(client, admin_user):
    login = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    assert login.status_code == 200, login.text

    response = await client.get("/api/hotels/7999/reconciliation/summary")
    assert response.status_code == 404


async def test_reconciliation_endpoint_denies_unassigned_hotel(client, db, reconciliation_fixture):
    # This user has no hotel assignment and is not a global administrator.
    from tests.conftest import _seed_user

    user = _seed_user(
        db,
        username="reconciliation_staff",
        email="reconciliation_staff@example.com",
        password="StaffPass123!",
        role="recepcionista",
    )
    db.roles.insert_one({"role_name": "recepcionista", "permissions": ["audit.read"]})

    login = await client.post(
        "/api/auth/login",
        json={"identifier": user["username"], "password": user["password"]},
    )
    assert login.status_code == 200, login.text

    response = await client.get("/api/hotels/701/reconciliation/summary")
    assert response.status_code == 403
