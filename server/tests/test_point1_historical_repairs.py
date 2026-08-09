"""Regression tests for the explicit Punto 1 historical financial repairs."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId


def _seed_booking(db, booking_id: str, *, total_price: float = 100.0) -> None:
    db.dim_hotels.insert_one({"prop_id": 1, "display_name": "Hotel Uno"})
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Reparación P1",
        "guest_email": "repair@example.test",
        "total_price": total_price,
        "total_nights": 1,
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-02",
        "status": "confirmed",
        "stay_status": "checked_out",
        "created_at": datetime.now(timezone.utc),
    })


def test_reopen_folio_with_balance_makes_it_collectible_and_is_idempotent(db):
    from src.app.modules.billing.service import folio as folio_service

    booking_id = "BK-P1-REOPEN-HISTORICAL"
    _seed_booking(db, booking_id)
    folio_id = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-P1-REOPEN",
        "status": "closed",
        "total_due": 25.0,
        "total_charges": 25.0,
        "total_payments": 0.0,
        "postings": [],
    }).inserted_id

    repair = getattr(folio_service, "reopen_folio_with_balance", None)
    assert callable(repair)

    first = repair(booking_id, changed_by="historical_reconciliation")
    second = repair(booking_id, changed_by="historical_reconciliation")

    assert first is not None
    assert second is not None
    stored = db.guest_folios.find_one({"_id": folio_id})
    assert stored["status"] == "open"
    assert stored["total_due"] == 25.0
    assert stored["metadata"]["reconciliation"]["action"] == "reopened_collectible_balance"
    assert db.booking_status_history.count_documents({
        "booking_id": booking_id,
        "status": "folio_reopened_for_collection",
    }) == 1


def test_repair_failed_charge_creates_safe_folio_and_links_charge_once(db):
    from src.app.modules.housekeeping.service.lifecycle import charges as charge_service

    booking_id = "BK-P1-REPAIR-CHARGE"
    _seed_booking(db, booking_id, total_price=100.0)
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "concept": "Daño comprobado",
        "amount": 10.02,
        "quantity": 1,
        "total": 10.02,
        "category": "danos",
        # Legacy Dev shape: active charges may have no explicit status.
        "posting_status": "posting_failed",
        "posting_error": "guest folio not found",
    }).inserted_id

    repair = getattr(charge_service, "repair_failed_charge", None)
    assert callable(repair)

    first = repair(str(charge_id), changed_by="historical_reconciliation")
    second = repair(str(charge_id), changed_by="historical_reconciliation")

    assert first is not None
    assert second is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio is not None
    assert first["posting_status"] == "posted"
    assert first["folio_id"] == str(folio["_id"])
    assert first["folio_number"] == folio["folio_number"]
    assert db.guest_folios.count_documents({
        "booking_id": booking_id,
        "postings": {"$elemMatch": {
            "reference_id": str(charge_id),
            "reference_type": "additional_charge",
        }},
    }) == 1
    assert db.additional_charges.find_one({"_id": charge_id})["posting_status"] == "posted"


def test_repair_cancelled_or_refunded_invoice_preserves_original_and_zeroes_net_value(db):
    from src.app.modules.billing.service.lifecycle import invoices as invoice_service

    booking_id = "BK-P1-REPAIR-INVOICE"
    _seed_booking(db, booking_id)
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_number": "INV-P1-REPAIR",
        "room_subtotal": 100.0,
        "extras_total": 0.0,
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "cancelled",
        "issued_at": datetime.now(timezone.utc),
    }).inserted_id

    repair = getattr(invoice_service, "repair_cancelled_or_refunded_invoice", None)
    assert callable(repair)

    first = repair(str(invoice_id), changed_by="historical_reconciliation")
    second = repair(str(invoice_id), changed_by="historical_reconciliation")

    assert first is not None
    assert second is not None
    stored = db.reservation_invoices.find_one({"_id": invoice_id})
    assert stored["total"] == 116.0
    assert stored["original_total"] == 116.0
    assert stored["recognized_total"] == 0.0
    assert stored["accounting_status"] == "reversed"
    fetched = invoice_service.get_invoice(str(invoice_id))
    assert fetched is not None
    assert fetched["total_pending_amount"] == 0.0
    assert db.ledger_transactions.count_documents({
        "source": "invoice_reversal",
        "source_id": "INV-P1-REPAIR",
    }) == 3
    rows = list(db.ledger_transactions.find({
        "source": "invoice_reversal",
        "source_id": "INV-P1-REPAIR",
    }))
    assert round(sum(float(row.get("debit", 0)) for row in rows), 2) == 116.0
    assert round(sum(float(row.get("credit", 0)) for row in rows), 2) == 116.0
    assert db.reservation_invoices.count_documents({"_id": invoice_id}) == 1
    assert db.fact_reservation_invoices.count_documents({"_id": invoice_id}) == 1
