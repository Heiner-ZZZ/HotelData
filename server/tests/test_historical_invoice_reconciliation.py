"""Tests for historical internal invoice reconstruction."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId


def _seed_settled_folio_without_room_ledger(db, booking_id: str) -> tuple[ObjectId, ObjectId]:
    checkout_at = datetime(2026, 7, 1, 3, 43, tzinfo=timezone.utc)
    booking_oid = db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Historical Guest",
        "guest_email": "guest@example.test",
        "total_price": 203.0,
        "total_nights": 1,
        "currency": "USD",
        "check_out_date_actual": "2026-07-01",
        "check_out_time_actual": "03:43",
        "stay_status": "checked_out",
        "created_at": checkout_at,
    }).inserted_id
    folio_id = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-HIST-0001",
        "status": "settled",
        "total_room": 203.0,
        "total_charges": 0.3,
        "total_payments": 203.3,
        "total_due": 0.0,
        "postings": [
            {
                "posting_id": ObjectId(),
                "type": "room",
                "category": "Habitación",
                "concept": "Habitación — 1 noche(s)",
                "amount": 203.0,
                "quantity": 1,
                "reference_id": booking_id,
                "reference_type": "booking",
                "posted_at": checkout_at,
            },
            {
                "posting_id": ObjectId(),
                "type": "charge",
                "category": "restaurante",
                "concept": "Comida",
                "amount": 0.3,
                "quantity": 1,
                "reference_id": "CHARGE-HIST-1",
                "reference_type": "additional_charge",
                "posted_at": checkout_at,
            },
            {
                "posting_id": ObjectId(),
                "type": "payment",
                "category": "Cash",
                "concept": "Pago histórico",
                "amount": 203.3,
                "quantity": 1,
                "reference_id": "PAY-HIST-1",
                "reference_type": "payment",
                "posted_at": checkout_at,
            },
        ],
        "posting_count": 3,
        "created_at": checkout_at,
    }).inserted_id
    payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "amount": 203.3,
        "method": "cash",
        "status": "confirmed",
        "reference": "PAY-HIST-1",
        "paid_at": checkout_at,
        "invoice_id": None,
    }).inserted_id
    db.guest_folios.update_one({"_id": folio_id}, {"$set": {"payment_id": payment_id}})
    return folio_id, payment_id


def test_reconstruct_historical_invoice_posts_only_unrecognized_room_revenue_and_is_idempotent(db):
    from src.app.modules.billing.service.lifecycle.invoices import reconstruct_historical_invoice_for_folio

    booking_id = "BK-HISTORICAL-INVOICE-1"
    folio_id, payment_id = _seed_settled_folio_without_room_ledger(db, booking_id)

    first = reconstruct_historical_invoice_for_folio(
        booking_id,
        changed_by="gerente",
        approval_reference="APROBACION-GERENTE-20260701-001",
    )
    second = reconstruct_historical_invoice_for_folio(
        booking_id,
        changed_by="gerente",
        approval_reference="APROBACION-GERENTE-20260701-001",
    )

    assert first is not None
    assert second is not None
    assert first["id"] == second["id"]
    assert first["status"] == "paid"
    assert first["source"] == "historical_reconstruction"
    assert first["total"] == 203.3
    assert first["accounting_status"] == "posted"

    invoice_id = ObjectId(first["id"])
    folio = db.guest_folios.find_one({"_id": folio_id})
    payment = db.reservation_payments.find_one({"_id": payment_id})
    assert folio["invoice_id"] == invoice_id
    assert payment["invoice_id"] == invoice_id
    assert db.fact_reservation_invoices.count_documents({"_id": invoice_id}) == 1
    assert db.fact_reservation_payments.find_one({"_id": payment_id})["invoice_id"] == invoice_id

    rows = list(db.ledger_transactions.find({
        "source": "historical_invoice",
        "source_id": first["invoice_number"],
    }))
    assert len(rows) == 2
    assert sum(float(row.get("debit", 0)) for row in rows) == 203.0
    assert sum(float(row.get("credit", 0)) for row in rows) == 203.0
    assert db.ledger_transactions.count_documents({
        "source": "historical_invoice",
        "source_id": first["invoice_number"],
    }) == 2
    assert db.reservation_invoices.count_documents({"booking_id": booking_id}) == 1
    assert db.hotel_domain_events.count_documents({"payload.booking_id": booking_id}) >= 1
    assert db.audit_log.count_documents({
        "entity_type": "historical_invoice",
        "entity_id": booking_id,
        "action": "reconstruct",
    }) == 1


def test_reconstruction_links_cancelled_invoice_and_separates_transfer_from_service_revenue(db):
    from src.app.modules.billing.service.lifecycle.invoices import reconstruct_historical_invoice_for_folio

    booking_id = "BK-HISTORICAL-INVOICE-TRANSFER"
    checkout_at = datetime(2026, 8, 1, 3, 9, tzinfo=timezone.utc)
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Transfer Guest",
        "total_price": 100.0,
        "total_nights": 1,
        "stay_status": "checked_out",
        "created_at": checkout_at,
    })
    old_invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_number": "INV-HIST-CANCELLED",
        "total": 100.0,
        "status": "cancelled",
    }).inserted_id
    room_posting_id = ObjectId()
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-HIST-TRANSFER",
        "status": "settled",
        "total_room": 100.0,
        "total_charges": 10.0,
        "total_payments": 110.0,
        "total_due": 0.0,
        "postings": [
            {"posting_id": room_posting_id, "type": "room", "amount": 100.0, "quantity": 1, "unit_price": 100.0, "concept": "Room", "reference_type": "booking", "reference_id": booking_id, "posted_at": checkout_at},
            {"posting_id": ObjectId(), "type": "adjustment", "amount": -10.0, "quantity": 1, "unit_price": -10.0, "concept": "Transfer out", "reference_type": "folio_transfer_out", "reference_id": "XFR-OUT-FL-HIST-TRANSFER", "posted_at": checkout_at},
            {"posting_id": ObjectId(), "type": "charge", "amount": 20.0, "quantity": 1, "unit_price": 20.0, "concept": "Service", "reference_type": "additional_charge", "reference_id": "SERVICE-HIST-TRANSFER", "posted_at": checkout_at},
        ],
    })
    payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "amount": 110.0,
        "method": "cash",
        "status": "confirmed",
        "reference": "PAY-HIST-TRANSFER",
        "paid_at": checkout_at,
    }).inserted_id
    db.ledger_transactions.insert_many([
        {"journal_entry_id": "JE-ROOM-HIST", "account_code": "1030", "debit": 100.0, "credit": 0.0, "source": "folio_posting", "source_id": str(room_posting_id), "booking_id": booking_id, "prop_id": 1},
        {"journal_entry_id": "JE-ROOM-HIST", "account_code": "4010", "debit": 0.0, "credit": 100.0, "source": "folio_posting", "source_id": str(room_posting_id), "booking_id": booking_id, "prop_id": 1},
    ])

    invoice = reconstruct_historical_invoice_for_folio(
        booking_id,
        changed_by="gerente",
        approval_reference="APROBACION-GERENTE-20260701-001",
    )

    assert invoice is not None
    stored_old = db.reservation_invoices.find_one({"_id": old_invoice_id})
    assert invoice["supersedes_invoice_id"] == old_invoice_id
    assert stored_old["is_deleted"] is True
    assert stored_old["replaced_by_invoice_id"] == ObjectId(invoice["id"])
    assert db.reservation_payments.find_one({"_id": payment_id})["invoice_id"] == ObjectId(invoice["id"])
    assert db.ledger_transactions.count_documents({"source": "historical_invoice", "source_id": invoice["invoice_number"] + ":services"}) == 2
    assert db.ledger_transactions.count_documents({"source": "folio_transfer", "source_id": "XFR-OUT-FL-HIST-TRANSFER"}) == 2


def test_reconstruction_uses_payment_applied_to_folio_not_unapplied_confirmed_payment(db):
    from src.app.modules.billing.service.lifecycle.invoices import reconstruct_historical_invoice_for_folio

    booking_id = "BK-HISTORICAL-INVOICE-APPLIED-PAYMENT"
    checkout_at = datetime(2026, 7, 5, 15, 14, tzinfo=timezone.utc)
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Applied Payment Guest",
        "total_price": 283.0,
        "total_nights": 1,
        "stay_status": "checked_out",
        "check_out_date_actual": "2026-07-05",
        "check_out_time_actual": "15:14",
    })
    folio_id = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-HIST-APPLIED-PAYMENT",
        "status": "settled",
        "total_room": 283.0,
        "total_charges": 283.0,
        "total_payments": 283.0,
        "total_due": 0.0,
        "postings": [{
            "posting_id": ObjectId(),
            "type": "room",
            "amount": 283.0,
            "quantity": 1,
            "unit_price": 283.0,
            "concept": "Room",
            "reference_type": "booking",
            "reference_id": booking_id,
            "posted_at": checkout_at,
        }, {
            "posting_id": ObjectId(),
            "type": "payment",
            "amount": 283.0,
            "quantity": 1,
            "unit_price": 283.0,
            "concept": "Historical cash",
            "reference_type": "payment",
            "reference_id": "PAY-APPLIED-CASH",
            "posted_at": checkout_at,
        }],
    }).inserted_id
    applied_id = db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "amount": 283.0,
        "method": "cash",
        "status": "confirmed",
        "reference": "PAY-APPLIED-CASH",
        "paid_at": checkout_at,
    }).inserted_id
    db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "amount": 92.8,
        "method": "simulated",
        "status": "confirmed",
        "reference": "PAY-UNAPPLIED-SIMULATED",
        "paid_at": checkout_at.replace(day=6),
    })

    invoice = reconstruct_historical_invoice_for_folio(
        booking_id,
        changed_by="socio.gta6",
        approval_reference="APROBACION-GERENTE-20260701-001",
    )

    assert invoice is not None
    assert invoice["total"] == 283.0
    assert db.reservation_payments.find_one({"_id": applied_id})["invoice_id"] == ObjectId(invoice["id"])
    assert db.reservation_payments.find_one({"reference": "PAY-UNAPPLIED-SIMULATED"}).get("invoice_id") is None
    assert db.guest_folios.find_one({"_id": folio_id})["invoice_id"] == ObjectId(invoice["id"])


def test_reconstruction_links_all_confirmed_payments_applied_to_folio(db):
    from src.app.modules.billing.service.lifecycle.invoices import reconstruct_historical_invoice_for_folio

    booking_id = "BK-HISTORICAL-INVOICE-MULTI-PAYMENT"
    checkout_at = datetime(2026, 8, 7, 19, 31, tzinfo=timezone.utc)
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Multiple Payment Guest",
        "total_price": 104.0,
        "total_nights": 1,
        "stay_status": "checked_out",
    })
    folio_id = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-HIST-MULTI-PAYMENT",
        "status": "settled",
        "total_room": 94.0,
        "total_charges": 10.0,
        "total_payments": 104.0,
        "total_due": 0.0,
        "postings": [{
            "posting_id": ObjectId(), "type": "room", "amount": 94.0,
            "quantity": 1, "unit_price": 94.0, "reference_type": "booking",
            "reference_id": booking_id, "posted_at": checkout_at,
        }, {
            "posting_id": ObjectId(), "type": "charge", "amount": 10.0,
            "quantity": 1, "unit_price": 10.0, "reference_type": "quick_charge",
            "reference_id": "CHARGE-MULTI", "posted_at": checkout_at,
        }, {
            "posting_id": ObjectId(), "type": "payment", "amount": 103.0,
            "quantity": 1, "unit_price": 103.0, "reference_type": "payment",
            "reference_id": "PAY-MULTI-103", "posted_at": checkout_at,
        }, {
            "posting_id": ObjectId(), "type": "payment", "amount": 1.0,
            "quantity": 1, "unit_price": 1.0, "reference_type": "payment",
            "reference_id": "PAY-MULTI-1", "posted_at": checkout_at,
        }],
    }).inserted_id
    first_payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id, "prop_id": 1, "amount": 103.0,
        "method": "cash", "status": "confirmed", "reference": "PAY-MULTI-103",
        "paid_at": checkout_at,
    }).inserted_id
    second_payment_id = db.reservation_payments.insert_one({
        "booking_id": booking_id, "prop_id": 1, "amount": 1.0,
        "method": "cash", "status": "confirmed", "reference": "PAY-MULTI-1",
        "paid_at": checkout_at,
    }).inserted_id

    invoice = reconstruct_historical_invoice_for_folio(
        booking_id,
        changed_by="socio.gta6",
        approval_reference="APROBACION-GERENTE-20260701-001",
    )

    assert invoice is not None
    assert invoice["total"] == 104.0
    assert db.reservation_payments.find_one({"_id": first_payment_id})["invoice_id"] == ObjectId(invoice["id"])
    assert db.reservation_payments.find_one({"_id": second_payment_id})["invoice_id"] == ObjectId(invoice["id"])
    assert db.reservation_invoices.find_one({"_id": ObjectId(invoice["id"])})["total_paid_amount"] == 104.0
