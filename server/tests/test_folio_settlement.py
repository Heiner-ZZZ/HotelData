"""Regression tests for explicit historical folio settlement outcomes."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest


def _seed_open_folio(db, booking_id: str, due: float = 100.0) -> None:
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Settlement Test",
        "total_price": due,
        "total_nights": 1,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc),
    })
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": f"FL-TEST-{booking_id}",
        "status": "open",
        "total_room": due,
        "total_charges": due,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": due,
        "postings": [],
        "posting_count": 0,
    })


def test_payment_settlement_closes_only_after_full_balance_and_is_idempotent(db):
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-PAYMENT"
    _seed_open_folio(db, booking_id, 100.0)
    payload = {
        "settlement_type": "payment",
        "amount": 100.0,
        "method": "card",
        "idempotency_key": "settlement-payment-1",
    }

    first = settle_folio(booking_id, payload, changed_by="cashier")
    second = settle_folio(booking_id, payload, changed_by="cashier")

    assert first is not None
    assert second is not None
    assert first["status"] == "settled"
    assert first["total_due"] == 0.0
    assert db.guest_folios.count_documents({"booking_id": booking_id, "status": "settled"}) == 1
    assert db.reservation_payments.count_documents({"booking_id": booking_id, "status": "confirmed"}) == 1
    assert db.folio_settlement_events.count_documents({
        "booking_id": booking_id,
        "idempotency_key": "settlement-payment-1",
    }) == 1
    event = db.folio_settlement_events.find_one({"booking_id": booking_id})
    assert db.fact_folio_settlement_events.find_one({"_id": event["_id"]}) is not None
    assert db.ledger_transactions.count_documents({
        "source": "payment",
        "booking_id": booking_id,
    }) == 2


def test_historical_cash_payment_preserves_effective_date_evidence_and_shift_trace(db):
    from bson import ObjectId
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-HISTORICAL-CASH"
    checkout_at = datetime(2026, 7, 1, 3, 43, tzinfo=timezone.utc)
    _seed_open_folio(db, booking_id, 203.30)
    folio_id = db.guest_folios.find_one({"booking_id": booking_id})["_id"]
    booking_oid = db.booking_orders.find_one({"booking_id": booking_id})["_id"]
    actor_user_id = ObjectId()
    shift_id = db.reception_shifts.insert_one({
        "_id": ObjectId(),
        "prop_id": 1,
        "status": "closed",
        "shift_type": "evening",
        "transactions": [],
        "payment_ids": [],
        "folio_ids": [],
        "booking_ids": [booking_oid],
        "total_collected": 0.0,
        "payment_breakdown": {"cash": 0.0, "card": 0.0, "transfer": 0.0, "other": 0.0, "total": 0.0},
    }).inserted_id

    result = settle_folio(booking_id, {
        "settlement_type": "payment",
        "amount": 203.30,
        "method": "cash",
        "idempotency_key": "settlement-historical-cash-1",
        "settlement_at": checkout_at.isoformat(),
        "evidence_type": "manager_attestation",
        "evidence_reference": "gerente",
    }, changed_by="socio.gta6", actor_user_id=actor_user_id, shift_id=str(shift_id))

    assert result is not None
    assert result["status"] == "settled"
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio["settled_by"] == "socio.gta6"
    assert folio["settled_by_user_id"] == actor_user_id
    payment = db.reservation_payments.find_one({"booking_id": booking_id})
    assert payment["status"] == "confirmed"
    assert payment["actor_user_id"] == actor_user_id
    assert payment["method"] == "cash"
    assert payment["paid_at"] == checkout_at.replace(tzinfo=None)
    assert payment["evidence_type"] == "manager_attestation"
    assert payment["evidence_reference"] == "gerente"
    assert payment["payment_source"] == "historical_attestation"

    ledger = list(db.ledger_transactions.find({"source": "payment", "source_id": payment["reference"]}))
    assert len(ledger) == 2
    assert all(row["tx_date"] == checkout_at.replace(tzinfo=None) for row in ledger)

    shift = db.reception_shifts.find_one({"_id": shift_id})
    assert payment["_id"] in shift["payment_ids"]
    assert folio_id in shift["folio_ids"]
    assert shift["transactions"][0]["folio_id"] == folio_id
    assert shift["total_collected"] == 203.30
    assert shift["payment_breakdown"]["cash"] == 203.30
    assert len(shift["transactions"]) == 1
    assert shift["transactions"][0]["payment_method"] == "cash"
    assert shift["transactions"][0]["timestamp"] == checkout_at.isoformat()

    settlement = db.folio_settlement_events.find_one({"booking_id": booking_id})
    assert settlement["actor_user_id"] == actor_user_id
    assert settlement["changed_by"] == "socio.gta6"
    assert settlement["effective_at"] == checkout_at.replace(tzinfo=None)
    assert settlement["evidence_reference"] == "gerente"
    audit = db.audit_log.find_one({
        "entity_type": "folio_settlement",
        "entity_id": booking_id,
        "action": "payment",
    })
    assert audit["changed_by"] == "socio.gta6"
    assert audit["metadata"]["actor_user_id"] == str(actor_user_id)


def test_partial_payment_keeps_folio_open_with_remaining_balance(db):
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-PARTIAL"
    _seed_open_folio(db, booking_id, 100.0)

    result = settle_folio(booking_id, {
        "settlement_type": "payment",
        "amount": 40.0,
        "method": "card",
        "idempotency_key": "settlement-partial-1",
    }, changed_by="cashier")

    assert result is not None
    assert result["status"] == "open"
    assert result["total_due"] == 60.0
    assert db.guest_folios.find_one({"booking_id": booking_id})["status"] == "open"

    final = settle_folio(booking_id, {
        "settlement_type": "payment",
        "amount": 60.0,
        "method": "card",
        "idempotency_key": "settlement-partial-2",
    }, changed_by="cashier")

    assert final["status"] == "settled"
    assert final["total_due"] == 0.0
    assert final["settlement_amount"] == 100.0


def test_write_off_requires_approval_and_zeroes_balance_with_audited_ledger(db):
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-WRITEOFF"
    _seed_open_folio(db, booking_id, 75.5)

    with pytest.raises(ValueError, match="approval|aprobación"):
        settle_folio(booking_id, {
            "settlement_type": "write_off",
            "reason": "Cliente no localizable",
            "idempotency_key": "settlement-writeoff-1",
        }, changed_by="cashier")

    result = settle_folio(booking_id, {
        "settlement_type": "write_off",
        "reason": "Cliente no localizable",
        "approval_reference": "AUTH-WO-001",
        "idempotency_key": "settlement-writeoff-1",
    }, changed_by="manager")

    assert result is not None
    assert result["status"] == "written_off"
    assert result["total_due"] == 0.0
    rows = list(db.ledger_transactions.find({
        "source": "folio_write_off",
        "source_id": "settlement-writeoff-1",
    }))
    assert len(rows) == 2
    assert sum(float(row.get("debit", 0)) for row in rows) == 75.5
    assert sum(float(row.get("credit", 0)) for row in rows) == 75.5


def test_external_settlement_requires_reference_and_is_traceable(db):
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-EXTERNAL"
    _seed_open_folio(db, booking_id, 55.0)

    with pytest.raises(ValueError, match="reference|referencia"):
        settle_folio(booking_id, {
            "settlement_type": "external_settlement",
            "reason": "Compensación bancaria",
            "idempotency_key": "settlement-external-1",
        }, changed_by="manager")

    result = settle_folio(booking_id, {
        "settlement_type": "external_settlement",
        "reason": "Compensación bancaria",
        "external_reference": "BANK-SETTLE-001",
        "approval_reference": "AUTH-EXT-001",
        "idempotency_key": "settlement-external-1",
    }, changed_by="manager")

    assert result is not None
    assert result["status"] == "settled"
    assert result["total_due"] == 0.0
    event = db.folio_settlement_events.find_one({"booking_id": booking_id})
    assert event["settlement_type"] == "external_settlement"
    assert event["external_reference"] == "BANK-SETTLE-001"
    assert db.ledger_transactions.count_documents({
        "source": "folio_external_settlement",
        "source_id": "settlement-external-1",
    }) == 2


def test_settlement_cannot_close_a_positive_balance_without_explicit_outcome(db):
    from src.app.modules.billing.service.folio import close_folio

    booking_id = "BK-SETTLE-GUARD"
    _seed_open_folio(db, booking_id, 10.0)

    assert close_folio(booking_id, closed_by="cashier") is None
    stored = db.guest_folios.find_one({"booking_id": booking_id})
    assert stored["status"] == "open"
    assert stored["total_due"] == 10.0


def test_historical_cash_accepts_a_closed_real_checkout_shift_for_the_same_booking():
    from src.app.modules.billing.service.folio import is_historical_cash_shift_eligible

    reconstructed = {
        "status": "closed",
        "metadata": {"reconciliation": {"category": "historical_reconstructed"}},
        "transactions": [],
    }
    real_checkout = {
        "status": "closed",
        "metadata": {},
        "transactions": [{
            "type": "check_out",
            "booking_id": "BK-REAL-CHECKOUT",
        }],
    }
    unrelated = {
        "status": "closed",
        "metadata": {},
        "transactions": [{
            "type": "check_out",
            "booking_id": "BK-OTHER",
        }],
    }

    assert is_historical_cash_shift_eligible(reconstructed, "BK-ANY") is True
    assert is_historical_cash_shift_eligible(real_checkout, "BK-REAL-CHECKOUT") is True
    assert is_historical_cash_shift_eligible(unrelated, "BK-REAL-CHECKOUT") is False


def test_reopen_settled_folio_when_refund_restores_a_collectible_balance(db):
    from src.app.modules.billing.service.folio import reopen_folio_with_balance

    booking_id = "BK-REOPEN-SETTLED-REFUND"
    _seed_open_folio(db, booking_id, 104.0)
    db.guest_folios.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "settled", "total_due": 1.0, "settled_at": datetime.now(timezone.utc)}},
    )

    result = reopen_folio_with_balance(booking_id, changed_by="socio.gta6")

    assert result is not None
    assert result["status"] == "open"
    assert result["total_due"] == 1.0
    assert result["metadata"]["reconciliation"]["previous_status"] == "settled"


def test_settlement_trace_links_payment_folio_shift_and_existing_invoice(db):
    from bson import ObjectId
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-TRACE-LINKS"
    folio_id = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-TRACE-LINKS",
        "status": "open",
        "total_room": 100.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": 100.0,
        "postings": [{
            "posting_id": ObjectId(), "type": "room", "amount": 100.0,
            "quantity": 1, "unit_price": 100.0, "reference_id": booking_id,
            "reference_type": "booking", "posted_at": datetime.now(timezone.utc),
        }],
        "posting_count": 1,
    }).inserted_id
    db.booking_orders.insert_one({"booking_id": booking_id, "prop_id": 1, "total_price": 100.0})
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id, "prop_id": 1, "invoice_number": "INV-TRACE-LINKS",
        "total": 100.0, "status": "issued",
    }).inserted_id
    db.guest_folios.update_one({"_id": folio_id}, {"$set": {"invoice_id": invoice_id}})
    shift_id = db.reception_shifts.insert_one({
        "prop_id": 1, "status": "closed", "metadata": {"reconciliation": {"category": "historical_reconstructed"}},
        "transactions": [], "payment_ids": [], "folio_ids": [],
        "payment_breakdown": {"cash": 0.0, "card": 0.0, "transfer": 0.0, "other": 0.0, "total": 0.0},
        "total_collected": 0.0,
    }).inserted_id

    result = settle_folio(booking_id, {
        "settlement_type": "payment", "amount": 100.0, "method": "cash",
        "idempotency_key": "settlement-trace-links-1",
        "settlement_at": "2026-08-01T03:00:00+00:00",
        "evidence_type": "manager_attestation", "evidence_reference": "TRACE-APPROVAL-1",
    }, changed_by="manager", actor_user_id=ObjectId(), shift_id=str(shift_id))

    assert result is not None
    payment = db.reservation_payments.find_one({"booking_id": booking_id})
    event = db.folio_settlement_events.find_one({"booking_id": booking_id})
    fact_event = db.fact_folio_settlement_events.find_one({"_id": event["_id"]})
    assert payment["folio_id"] == folio_id
    assert event["shift_id"] == shift_id
    assert event["invoice_id"] == invoice_id
    assert fact_event["shift_id"] == shift_id
    assert fact_event["invoice_id"] == invoice_id


def test_multiple_settlements_preserve_every_payment_and_event_trace(db):
    from src.app.modules.billing.service.folio import settle_folio

    booking_id = "BK-SETTLE-TRACE-MULTIPLE"
    db.booking_orders.insert_one({"booking_id": booking_id, "prop_id": 1, "total_price": 100.0})
    db.guest_folios.insert_one({
        "booking_id": booking_id, "prop_id": 1, "folio_number": "FL-TRACE-MULTIPLE",
        "status": "open", "total_room": 100.0, "total_charges": 0.0,
        "total_discounts": 0.0, "total_payments": 0.0, "total_due": 100.0,
        "postings": [], "posting_count": 0,
    })

    first = settle_folio(booking_id, {
        "settlement_type": "payment", "amount": 60.0, "method": "card",
        "idempotency_key": "settlement-trace-multiple-1",
    }, changed_by="manager")
    second = settle_folio(booking_id, {
        "settlement_type": "payment", "amount": 40.0, "method": "card",
        "idempotency_key": "settlement-trace-multiple-2",
    }, changed_by="manager")

    assert first is not None and second is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    events = list(db.folio_settlement_events.find({"booking_id": booking_id}).sort("created_at", 1))
    assert len(events) == 2
    assert len(folio.get("settlement_event_ids", [])) == 2
    assert len(folio.get("settlement_payment_ids", [])) == 2
    assert set(folio["settlement_event_ids"]) == {event["_id"] for event in events}
    assert set(folio["settlement_payment_ids"]) == {event["payment_id"] for event in events}


def test_historical_invoice_reconciliation_backfills_settlement_invoice_link(db):
    from bson import ObjectId
    from src.app.modules.billing.service.folio import settle_folio
    from src.app.modules.billing.service.lifecycle.invoices import reconstruct_historical_invoice_for_folio

    booking_id = "BK-SETTLE-TRACE-INVOICE-LATER"
    db.booking_orders.insert_one({
        "booking_id": booking_id, "prop_id": 1, "total_price": 100.0,
        "stay_status": "checked_out",
    })
    db.guest_folios.insert_one({
        "booking_id": booking_id, "prop_id": 1, "folio_number": "FL-TRACE-INVOICE-LATER",
        "status": "open", "total_room": 100.0, "total_charges": 0.0,
        "total_discounts": 0.0, "total_payments": 0.0, "total_due": 100.0,
        "postings": [{
            "posting_id": ObjectId(), "type": "room", "amount": 100.0,
            "quantity": 1, "unit_price": 100.0, "reference_id": booking_id,
            "reference_type": "booking", "posted_at": datetime.now(timezone.utc),
        }], "posting_count": 1,
    })
    settled = settle_folio(booking_id, {
        "settlement_type": "payment", "amount": 100.0, "method": "card",
        "idempotency_key": "settlement-trace-invoice-later-1",
    }, changed_by="manager")
    assert settled is not None

    invoice = reconstruct_historical_invoice_for_folio(
        booking_id, changed_by="manager", approval_reference="TRACE-APPROVAL-2",
    )

    assert invoice is not None
    event = db.folio_settlement_events.find_one({"booking_id": booking_id})
    payment = db.reservation_payments.find_one({"booking_id": booking_id})
    assert payment["folio_id"] == db.guest_folios.find_one({"booking_id": booking_id})["_id"]
    assert event["invoice_id"] == ObjectId(invoice["id"])
    assert db.fact_folio_settlement_events.find_one({"_id": event["_id"]})["invoice_id"] == ObjectId(invoice["id"])


def test_historical_checkout_can_use_immutable_status_history_when_actual_fields_are_missing(db):
    from datetime import datetime, timezone
    from src.app.modules.billing.service.folio import resolve_checkout_at

    booking_id = "BK-CHECKOUT-HISTORY-FALLBACK"
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "check_out_date_actual": None,
        "check_out_time_actual": None,
    })
    checkout_at = datetime(2026, 6, 27, 0, 39, 37, tzinfo=timezone.utc)
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "checked_out",
        "changed_at": checkout_at,
    })

    assert resolve_checkout_at(db, booking_id) == checkout_at.replace(tzinfo=None)
