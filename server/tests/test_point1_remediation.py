"""Red tests for Punto 1: financial and operational remediation invariants."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId

from src.app.modules.billing.schemas import PaymentCreate
from src.app.modules.billing.service.folio import close_folio, create_folio, post_to_folio
from src.app.modules.billing.service.lifecycle.payments import create_payment, refund_payment
from src.app.modules.housekeeping.schemas import AdditionalChargeCreate, MaintenanceTaskCreate
from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge
from src.app.modules.housekeeping.service.lifecycle.maintenance import create_maintenance_task
from src.app.modules.lost_and_found.service.lifecycle import delete_lost_item



def _booking(db, *, booking_id: str, prop_id: int = 901, total_price: float = 100.0) -> str:
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": f"Hotel {prop_id}"})
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "Punto 1",
        "total_price": total_price,
        "total_nights": 1,
        "status": "confirmed",
        "stay_status": "checked_in",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-11",
        "created_at": datetime.now(timezone.utc),
    })
    return booking_id


def test_close_folio_requires_zero_balance_or_documented_exception(db):
    booking_id = _booking(db, booking_id="BK-P1-CLOSE")
    create_folio(booking_id)

    assert close_folio(booking_id, closed_by="tester") is None
    assert db.guest_folios.find_one({"booking_id": booking_id})["status"] == "open"

    closed = close_folio(
        booking_id,
        closed_by="tester",
        close_reason="approved_write_off: P1 test",
    )
    assert closed is not None
    assert closed["status"] == "closed"
    assert closed["close_reason"].startswith("approved_write_off:")


def test_payment_rejects_malformed_or_foreign_invoice_reference(db):
    booking_id = _booking(db, booking_id="BK-P1-BAD-INVOICE", prop_id=901)

    import pytest
    with pytest.raises(ValueError, match="Factura"):
        create_payment(PaymentCreate(
            booking_id=booking_id,
            invoice_id="not-an-object-id",
            amount=10.0,
        ))

    other_booking = _booking(db, booking_id="BK-P1-OTHER-INVOICE", prop_id=902)
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": other_booking,
        "prop_id": 902,
        "invoice_number": "INV-P1-FOREIGN",
        "total": 10.0,
        "status": "issued",
    }).inserted_id
    with pytest.raises(ValueError, match="pertenece"):
        create_payment(PaymentCreate(
            booking_id=booking_id,
            invoice_id=str(invoice_id),
            amount=10.0,
        ))


def test_partial_payment_does_not_mark_invoice_as_paid(db):
    booking_id = _booking(db, booking_id="BK-P1-PARTIAL-PAYMENT", total_price=100.0)
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "invoice_number": "INV-P1-PARTIAL",
        "subtotal": 100.0,
        "taxes": 0.0,
        "total": 100.0,
        "status": "issued",
    }).inserted_id

    payment = create_payment(PaymentCreate(
        booking_id=booking_id,
        invoice_id=str(invoice_id),
        amount=40.0,
        method="card",
    ))

    assert payment is not None
    assert db.reservation_invoices.find_one({"_id": invoice_id})["status"] == "partially_paid"


def test_payment_overpay_is_rejected_without_creating_payment(db):
    booking_id = _booking(db, booking_id="BK-P1-OVERPAY")
    create_folio(booking_id)

    import pytest
    with pytest.raises(ValueError, match="saldo"):
        create_payment(PaymentCreate(booking_id=booking_id, amount=101.0, method="cash"))
    assert db.reservation_payments.count_documents({"booking_id": booking_id}) == 0


def test_refund_reverses_folio_payment_and_ledger_once(db):
    booking_id = _booking(db, booking_id="BK-P1-REFUND")
    create_folio(booking_id)
    payment = create_payment(PaymentCreate(booking_id=booking_id, amount=100.0, method="cash"))
    assert payment is not None
    post_to_folio(
        booking_id,
        posting_type="payment",
        category="Cash",
        concept="Original payment",
        amount=100.0,
        reference_id=payment["reference"],
        reference_type="payment",
    )

    refunded = refund_payment(payment["id"])
    assert refunded is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio["total_payments"] == 0
    assert folio["total_due"] == 100.0
    assert db.ledger_transactions.count_documents({
        "source": "payment_refund", "source_id": payment["reference"],
    }) == 2

    assert refund_payment(payment["id"]) is None
    assert db.ledger_transactions.count_documents({
        "source": "payment_refund", "source_id": payment["reference"],
    }) == 2


def test_charge_records_failed_posting_instead_of_silently_succeeding(db):
    booking_id = _booking(db, booking_id="BK-P1-CHARGE")
    result = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Late checkout",
        amount=25.0,
    ))

    assert result is not None
    stored = db.additional_charges.find_one({"_id": ObjectId(result["id"])})
    assert stored["posting_status"] == "posting_failed"
    assert stored["posting_error"]


def test_delete_charge_preserves_evidence_and_reverses_closed_folio(db):
    """Voiding a charge must never erase evidence or leave revenue overstated."""
    booking_id = _booking(db, booking_id="BK-P1-CHARGE-VOID")
    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Daño de habitación",
        amount=25.0,
    ))
    assert charge is not None
    db.guest_folios.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "closed"}},
    )

    from src.app.modules.housekeeping.service.lifecycle.charges import delete_additional_charge
    result = delete_additional_charge(charge["id"])

    assert result is not None
    assert result["status"] == "reversed"
    stored = db.additional_charges.find_one({"_id": ObjectId(charge["id"])})
    assert stored is not None
    assert stored["status"] == "reversed"
    assert stored["posting_status"] == "reversed"
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert any(
        p.get("reference_id") == f'{charge["id"]}:v1:reversal'
        and p.get("reference_type") == "charge_reversal"
        for p in folio["postings"]
    )
    assert folio["total_due"] == 100.0


def test_edit_charge_revisions_do_not_accumulate_amounts(db):
    booking_id = _booking(db, booking_id="BK-P1-CHARGE-EDIT-VERSIONS")
    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Room service",
        amount=10.0,
    ))
    assert charge is not None

    from src.app.modules.housekeeping.service.lifecycle.charges import update_additional_charge
    from src.app.modules.housekeeping.schemas import AdditionalChargeUpdate
    first = update_additional_charge(charge["id"], AdditionalChargeUpdate(amount=20.0))
    second = update_additional_charge(charge["id"], AdditionalChargeUpdate(amount=30.0))

    assert first is not None
    assert second is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio["total_charges"] == 30.0
    assert folio["total_due"] == 130.0
    assert len([p for p in folio["postings"] if p.get("reference_type") == "additional_charge_revision"]) == 2
    assert len([p for p in folio["postings"] if p.get("reference_type") == "charge_edit_reversal"]) == 2

    deleted = __import__("src.app.modules.housekeeping.service.lifecycle.charges", fromlist=["delete_additional_charge"]).delete_additional_charge(charge["id"])
    assert deleted is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio["total_charges"] == 0.0
    assert folio["total_due"] == 100.0


def test_edit_charge_failure_does_not_change_source_amount(db):
    booking_id = _booking(db, booking_id="BK-P1-CHARGE-EDIT-FAIL")
    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Room service",
        amount=10.0,
    ))
    assert charge is not None

    from src.app.modules.housekeeping.service.lifecycle import charges as charges_service
    from src.app.modules.housekeeping.schemas import AdditionalChargeUpdate
    with patch(
        "src.app.modules.billing.service.folio.post_to_folio",
        side_effect=[object(), None],
    ):
        result = charges_service.update_additional_charge(
            charge["id"], AdditionalChargeUpdate(amount=20.0),
        )

    assert result is not None
    assert result["posting_status"] == "posting_failed"
    stored = db.additional_charges.find_one({"_id": ObjectId(charge["id"])})
    assert stored["amount"] == 10.0
    assert stored["total"] == 10.0


def test_folio_idempotency_key_rejects_changed_amount(db):
    booking_id = _booking(db, booking_id="BK-P1-FOLIO-IDEMPOTENCY-CONFLICT")
    create_folio(booking_id)

    assert post_to_folio(
        booking_id,
        posting_type="charge",
        concept="Minibar",
        amount=10.0,
        reference_id="CHARGE-1",
        reference_type="additional_charge",
    ) is not None
    assert post_to_folio(
        booking_id,
        posting_type="charge",
        concept="Minibar corregido",
        amount=20.0,
        reference_id="CHARGE-1",
        reference_type="additional_charge",
    ) is None

    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio["total_charges"] == 10.0
    assert len([p for p in folio["postings"] if p.get("reference_id") == "CHARGE-1"]) == 1


def test_edit_charge_is_rejected_after_folio_close(db):
    booking_id = _booking(db, booking_id="BK-P1-CHARGE-EDIT-CLOSED")
    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Room service",
        amount=10.0,
    ))
    assert charge is not None
    db.guest_folios.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "closed"}},
    )

    from src.app.modules.housekeeping.service.lifecycle.charges import update_additional_charge
    from src.app.modules.housekeeping.schemas import AdditionalChargeUpdate
    result = update_additional_charge(charge["id"], AdditionalChargeUpdate(amount=20.0))

    assert result is None
    stored = db.additional_charges.find_one({"_id": ObjectId(charge["id"])})
    assert stored["amount"] == 10.0
    assert stored["total"] == 10.0
    assert stored["status"] == "active"


def test_delete_charge_is_idempotent_after_reversal(db):
    booking_id = _booking(db, booking_id="BK-P1-CHARGE-VOID-IDEMPOTENT")
    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Minibar",
        amount=10.0,
    ))
    assert charge is not None

    from src.app.modules.housekeeping.service.lifecycle.charges import delete_additional_charge
    first = delete_additional_charge(charge["id"])
    second = delete_additional_charge(charge["id"])

    assert first is not None
    assert second is not None
    assert db.additional_charges.count_documents({"_id": ObjectId(charge["id"])}) == 1
    assert db.guest_folios.count_documents({
        "booking_id": booking_id,
        "postings": {"$elemMatch": {
            "reference_id": f'{charge["id"]}:v1:reversal',
            "reference_type": "charge_reversal",
        }},
    }) == 1


def test_cleaning_damage_creates_traceable_maintenance_task(db):
    """A room-damage report must create a maintenance order with the room FK."""
    from src.app.modules.housekeeping.service.lifecycle.cleaning_actions import complete_cleaning

    prop_id = 922
    room_id = "HR-922-101"
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "Damage Hotel"})
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id,
        "prop_id": prop_id,
        "room_label": "101",
        "room_type_id": "standard",
    })
    db.room_status_log.insert_one({
        "prop_id": prop_id,
        "room_label": "101",
        "hotel_room_id": room_id,
        "room_type_id": "standard",
        "status": "cleaning_in_progress",
    })

    complete_cleaning(
        prop_id,
        "101",
        damage_found=True,
        damage_description="Grifo roto",
    )

    task = db.maintenance_tasks.find_one({"prop_id": prop_id})
    assert task is not None
    assert task["hotel_room_id"] == room_id
    assert task["room_label"] == "101"
    assert task["status"] == "scheduled"


def test_maintenance_persists_financial_fields(db):
    db.dim_hotels.insert_one({"prop_id": 902, "display_name": "Maintenance Hotel"})
    room_id = "HR-902-101"
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id,
        "prop_id": 902,
        "room_label": "101",
        "room_type_id": "standard",
    })
    task = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=902,
        room_id=room_id,
        task_type="corrective",
        title="HVAC",
        estimated_cost=150.0,
        actual_cost=125.0,
        currency="USD",
        vendor_name="Proveedor P1",
        expense_invoice_id="vendor-bill-1",
    ))

    stored = db.maintenance_tasks.find_one({"_id": ObjectId(task["id"])})
    assert stored["actual_cost"] == 125.0
    assert stored["currency"] == "USD"
    assert stored["vendor_name"] == "Proveedor P1"
    assert stored["expense_invoice_id"] == "vendor-bill-1"
    assert task["estimatedCost"] == 150.0
    assert task["actualCost"] == 125.0
    assert task["currency"] == "USD"
    assert task["vendorName"] == "Proveedor P1"
    assert task["financialLinkStatus"] == "invalid_invoice"


def test_lost_and_found_delete_is_logical_archive(db):
    item_id = db.lost_and_found.insert_one({
        "prop_id": 903,
        "item_name": "Wallet",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }).inserted_id

    result = delete_lost_item(str(item_id))
    assert result is not None
    assert result["status"] == "archived"
    assert db.lost_and_found.count_documents({"_id": item_id}) == 1


def test_invoice_backfill_uses_injected_database_for_ledger(db):
    from scripts.migrate_financial_reconciliation import migrate_invoice_ledger

    booking_id = _booking(db, booking_id="BK-P1-INVOICE-INJECTED", prop_id=904)
    db.reservation_invoices.insert_one({
        "prop_id": 904, "booking_id": booking_id, "invoice_number": "INV-P1-INJECTED",
        "subtotal": 100.0, "taxes": 16.0, "total": 116.0, "status": "paid",
        "issued_at": datetime.now(timezone.utc),
    })

    result = migrate_invoice_ledger(db, prop_id=904, apply=True)

    assert result["repaired"] == 1
    assert db.ledger_transactions.count_documents({
        "prop_id": 904, "source": "invoice", "source_id": "INV-P1-INJECTED",
    }) == 3


def test_invoice_backfill_migration_skips_cancelled_and_refunded(db):
    from scripts.migrate_financial_reconciliation import migrate_invoice_ledger

    booking_id = _booking(db, booking_id="BK-P1-INVOICE-SKIP", prop_id=904)
    for status in ("cancelled", "refunded"):
        db.reservation_invoices.insert_one({
            "prop_id": 904,
            "booking_id": booking_id,
            "invoice_number": f"INV-P1-{status.upper()}",
            "subtotal": 100.0,
            "taxes": 16.0,
            "total": 116.0,
            "status": status,
            "issued_at": datetime.now(timezone.utc),
        })

    result = migrate_invoice_ledger(db, prop_id=904, apply=True)

    assert result["candidates"] == 0
    assert db.ledger_transactions.count_documents({"prop_id": 904, "source": "invoice"}) == 0


def test_invoice_backfill_migration_is_idempotent(db):
    from scripts.migrate_financial_reconciliation import migrate_invoice_ledger

    booking_id = _booking(db, booking_id="BK-P1-INVOICE", prop_id=904)
    invoice_id = db.reservation_invoices.insert_one({
        "prop_id": 904,
        "booking_id": booking_id,
        "invoice_number": "INV-P1-001",
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "paid",
        "issued_at": datetime.now(timezone.utc),
    }).inserted_id

    first = migrate_invoice_ledger(db, prop_id=904, apply=True)
    second = migrate_invoice_ledger(db, prop_id=904, apply=True)

    assert first["repaired"] == 1
    assert second["repaired"] == 0
    assert db.ledger_transactions.count_documents({
        "prop_id": 904, "source": "invoice", "source_id": "INV-P1-001",
    }) == 3
    assert db.reservation_invoices.find_one({"_id": invoice_id})["metadata"]["migration_id"]


def test_split_invoice_stays_issued_when_accounting_reversal_fails(db):
    """Never hide an issued receivable if its reversal did not post."""
    from src.app.modules.billing.service import create_split_charges_invoice

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-REVERSAL-FAIL")
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id, "prop_id": 901, "concept": "Minibar",
        "amount": 10.0, "quantity": 1, "total": 10.0, "status": "active",
    }).inserted_id
    created = create_split_charges_invoice(booking_id)
    assert created is not None
    db.additional_charges.update_one({"_id": charge_id}, {"$set": {"status": "reversed"}})

    with patch(
        "src.app.modules.expenses.service.ledger_hooks.generate_reversal_from_invoice",
        side_effect=RuntimeError("ledger unavailable"),
    ):
        import pytest
        with pytest.raises(ValueError, match="reverso"):
            create_split_charges_invoice(booking_id)

    split = db.reservation_invoices.find_one({"_id": ObjectId(created["id"])})
    assert split["status"] == "issued"
    assert split["total"] == 11.6


def test_split_invoice_is_cancelled_when_all_source_charges_are_reversed(db):
    """A split invoice must not keep billing charges that no longer exist."""
    from src.app.modules.billing.service import create_split_charges_invoice

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-VOID")
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Minibar",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "status": "active",
    }).inserted_id

    created = create_split_charges_invoice(booking_id)
    assert created is not None
    db.additional_charges.update_one({"_id": charge_id}, {"$set": {"status": "reversed"}})

    assert create_split_charges_invoice(booking_id) is None
    split = db.reservation_invoices.find_one({"_id": ObjectId(created["id"])})
    assert split["status"] == "cancelled"
    assert split["total"] == 0.0
    assert db.booking_orders.find_one({"booking_id": booking_id})["total_charges"] == 0.0


def test_paid_split_invoice_is_not_zeroed_when_source_charges_are_reversed(db):
    """A paid split invoice requires compensation, never silent zeroing."""
    from src.app.modules.billing.service import create_split_charges_invoice

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-PAID-VOID")
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Minibar",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "status": "active",
    }).inserted_id
    created = create_split_charges_invoice(booking_id)
    assert created is not None
    db.reservation_payments.insert_one({
        "invoice_id": ObjectId(created["id"]),
        "booking_id": booking_id,
        "status": "confirmed",
        "amount": 11.6,
    })
    db.additional_charges.update_one({"_id": charge_id}, {"$set": {"status": "reversed"}})

    import pytest
    with pytest.raises(ValueError, match="compensatorio"):
        create_split_charges_invoice(booking_id)

    split = db.reservation_invoices.find_one({"_id": ObjectId(created["id"])})
    assert split["status"] == "issued"
    assert split["total"] == 11.6
    # The existing operational projection remains untouched until an explicit
    # compensating document reconciles the paid snapshot.
    assert db.booking_orders.find_one({"booking_id": booking_id}).get("total_charges", 0) == 10.0


def test_split_invoice_preserves_non_line_item_booking_charges(db):
    """Reconciliation must not erase other operational charge sources."""
    from src.app.modules.billing.service import create_split_charges_invoice

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-PRESERVE-OTHER")
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"line_items": [], "total_charges": 40.0}},
    )
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id, "prop_id": 901, "concept": "Minibar",
        "amount": 10.0, "quantity": 1, "total": 10.0, "status": "active",
    }).inserted_id
    created = create_split_charges_invoice(booking_id)
    assert created is not None
    db.additional_charges.update_one({"_id": charge_id}, {"$set": {"amount": 20.0, "total": 20.0}})

    create_split_charges_invoice(booking_id)

    assert db.booking_orders.find_one({"booking_id": booking_id})["total_charges"] == 50.0


def test_split_invoice_rebuild_updates_booking_total(db):
    """Rebuilding a split invoice updates the booking projection too."""
    from src.app.modules.billing.service import create_split_charges_invoice

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-REBUILD")
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Lavandería",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "status": "active",
    }).inserted_id
    created = create_split_charges_invoice(booking_id)
    assert created is not None

    db.additional_charges.update_one(
        {"_id": charge_id},
        {"$set": {"amount": 20.0, "total": 20.0}},
    )
    rebuilt = create_split_charges_invoice(booking_id)

    assert rebuilt is not None
    assert rebuilt["subtotal"] == 20.0
    assert db.booking_orders.find_one({"booking_id": booking_id})["total_charges"] == 20.0


def test_room_status_migration_preserves_legacy_value(db):
    from scripts.migrate_financial_reconciliation import normalize_room_statuses

    room_id = db.room_status_log.insert_one({
        "prop_id": 905,
        "room_label": "101",
        "status": "occupied",
    }).inserted_id

    result = normalize_room_statuses(db, prop_id=905, apply=True)
    doc = db.room_status_log.find_one({"_id": room_id})
    assert result["updated"] == 1
    assert doc["status"] == "occupied_clean"
    assert doc["metadata"]["original_status"] == "occupied"


def test_cleanup_expired_folio_does_not_close_positive_balance(db):
    from src.app.modules.billing.service.folio import cleanup_expired_folios

    booking_id = _booking(db, booking_id="BK-P1-EXPIRED-BALANCE")
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "status": "open",
        "check_out_date": "2020-01-01",
        "total_due": 20.0,
    })

    result = cleanup_expired_folios(prop_id=901)

    assert result["closed"] == 0
    assert db.guest_folios.find_one({"booking_id": booking_id})["status"] == "open"


def test_create_folio_reconciles_pending_additional_charges(db):
    """Charges created before check-in must post once when the folio exists."""
    booking_id = _booking(db, booking_id="BK-P1-PENDING-CHARGE")
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Desayuno",
        "amount": 12.0,
        "quantity": 1,
        "total": 12.0,
        "posting_status": "pending",
    }).inserted_id

    folio = create_folio(booking_id)

    assert folio is not None
    stored_charge = db.additional_charges.find_one({"_id": charge_id})
    assert stored_charge["posting_status"] == "posted"
    stored_folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert stored_folio["total_charges"] == 12.0
    assert any(str(p.get("reference_id")) == str(charge_id) for p in stored_folio["postings"])


def test_amenity_request_releases_stock_when_folio_posting_fails(db):
    """A failed financial posting must not consume amenity stock permanently."""
    from src.app.modules.amenities.service import request_amenities, set_amenity_stock

    booking_id = _booking(db, booking_id="BK-P1-AMENITY-ROLLBACK")
    db.hotel_content_pages.insert_one({
        "prop_id": 901,
        "amenity_prices": {"Toalla": 10.0},
    })
    set_amenity_stock(901, "Toalla", total_stock=2)

    result = request_amenities(booking_id, [{"label": "Toalla", "quantity": 1}])

    stock = db.amenity_stock.find_one({
        "prop_id": 901,
        "amenity_label": "Toalla",
        "room_type_id": "",
    })
    assert result["ok"] is False
    assert stock["available_stock"] == 2
    assert db.additional_charges.count_documents({"booking_id": booking_id}) == 1


def test_confirmed_payment_created_before_folio_is_reconciled_once(db):
    booking_id = _booking(db, booking_id="BK-P1-PAYMENT-BEFORE-FOLIO")

    payment = create_payment(PaymentCreate(booking_id=booking_id, amount=25.0, method="cash"))
    assert payment is not None
    assert db.guest_folios.count_documents({"booking_id": booking_id}) == 0

    create_folio(booking_id)
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    postings = [p for p in folio["postings"] if p.get("reference_id") == payment["reference"]]
    assert len(postings) == 1
    assert postings[0]["type"] == "payment"
    assert folio["total_payments"] == 25.0

    create_folio(booking_id)
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert len([p for p in folio["postings"] if p.get("reference_id") == payment["reference"]]) == 1


def test_confirmed_payment_posts_to_open_folio_once(db):
    """A confirmed payment must leave payment and folio evidence connected."""
    booking_id = _booking(db, booking_id="BK-P1-PAYMENT-FOLIO")
    create_folio(booking_id)

    payment = create_payment(PaymentCreate(booking_id=booking_id, amount=25.0, method="cash"))

    assert payment is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    postings = [p for p in folio["postings"] if p.get("reference_id") == payment["reference"]]
    assert len(postings) == 1
    assert postings[0]["type"] == "payment"
    assert folio["total_payments"] == 25.0
    assert folio["total_due"] == 75.0


def test_add_booking_line_item_rolls_back_unlimited_stock_without_mutating_inventory(db):
    from src.app.modules.partner.services.hotel_products import add_booking_line_item

    booking_id = _booking(db, booking_id="BK-P1-PRODUCT-UNLIMITED")
    db.hotel_products.insert_one({
        "prop_id": 901,
        "product_id": "PROD-P1-UNLIMITED",
        "name": "Agua",
        "unit_price": 5.0,
        "quantity_available": 0,
    })

    result = add_booking_line_item(
        booking_id,
        product_id="PROD-P1-UNLIMITED",
        name="Agua",
        unit_price=5.0,
        quantity=1,
    )

    assert result is None
    product = db.hotel_products.find_one({"prop_id": 901, "product_id": "PROD-P1-UNLIMITED"})
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    assert product["quantity_available"] == 0
    assert booking.get("line_items", []) == []


def test_restock_same_invoice_product_is_idempotent(db):
    """Retrying the same vendor bill line must not create stock twice."""
    from src.app.modules.partner.services.hotel_products import restock_product

    db.hotel_products.insert_one({
        "prop_id": 901,
        "product_id": "PROD-P1-RESTOCK-IDEMPOTENT",
        "name": "Agua",
        "quantity_available": 0,
    })
    invoice_id = db.expense_invoices.insert_one({
        "prop_id": 901,
        "status": "approved",
    }).inserted_id

    first = restock_product(
        901,
        "PROD-P1-RESTOCK-IDEMPOTENT",
        qty=5,
        unit_cost=2.0,
        invoice_id=str(invoice_id),
    )
    second = restock_product(
        901,
        "PROD-P1-RESTOCK-IDEMPOTENT",
        qty=5,
        unit_cost=2.0,
        invoice_id=str(invoice_id),
    )

    assert first is not None
    assert second is not None
    assert db.hotel_products.find_one({
        "prop_id": 901,
        "product_id": "PROD-P1-RESTOCK-IDEMPOTENT",
    })["quantity_available"] == 5
    assert db.fact_inventory.count_documents({
        "prop_id": 901,
        "product_id": "PROD-P1-RESTOCK-IDEMPOTENT",
        "invoice_ref": str(invoice_id),
    }) == 1


def test_remove_untracked_product_does_not_create_stock(db):
    from src.app.modules.partner.services.hotel_products import remove_booking_line_item

    booking_id = _booking(db, booking_id="BK-P1-PRODUCT-UNTRACKED-REMOVE")
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "status": "open",
        "total_due": 100.0,
        "total_charges": 5.0,
        "total_payments": 0.0,
        "postings": [],
        "posting_count": 0,
    })
    db.hotel_products.insert_one({
        "prop_id": 901,
        "product_id": "PROD-P1-UNTRACKED-REMOVE",
        "name": "Servicio ilimitado",
        "unit_price": 5.0,
        "quantity_available": 0,
        "stock_tracked": False,
    })
    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": {
        "line_items": [{
            "item_id": "LI-P1-UNTRACKED",
            "product_id": "PROD-P1-UNTRACKED-REMOVE",
            "quantity": 1,
            "total": 5.0,
        }],
    }})

    assert remove_booking_line_item(booking_id, "LI-P1-UNTRACKED") is True
    assert db.hotel_products.find_one({
        "product_id": "PROD-P1-UNTRACKED-REMOVE",
    })["quantity_available"] == 0


def test_pre_folio_payment_cannot_exceed_booking_total(db):
    import pytest

    booking_id = _booking(db, booking_id="BK-P1-PREFOLIO-OVERPAY", total_price=100.0)
    with pytest.raises(ValueError, match="saldo"):
        create_payment(PaymentCreate(
            booking_id=booking_id,
            amount=150.0,
            method="cash",
        ))
    assert db.reservation_payments.count_documents({"booking_id": booking_id}) == 0


def test_unapplied_prefolio_payment_is_marked_explicitly_when_folio_cannot_accept_it(db):
    from src.app.modules.billing.service.folio import create_folio

    booking_id = _booking(db, booking_id="BK-P1-PREFOLIO-UNAPPLIED", total_price=100.0)
    payment = create_payment(PaymentCreate(
        booking_id=booking_id,
        amount=40.0,
        method="cash",
    ))
    assert payment is not None
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "status": "open",
        "total_due": 20.0,
        "total_charges": 0.0,
        "total_payments": 0.0,
        "postings": [],
        "posting_count": 0,
    })

    create_folio(booking_id)

    stored = db.reservation_payments.find_one({"reference": payment["reference"]})
    assert stored["status"] == "unapplied"
    assert stored["unapplied_reason"] == "folio_balance_or_closed"


def test_refund_can_reverse_payment_after_folio_closed(db):
    booking_id = _booking(db, booking_id="BK-P1-REFUND-CLOSED")
    create_folio(booking_id)
    payment = create_payment(PaymentCreate(
        booking_id=booking_id,
        amount=100.0,
        method="cash",
    ))
    assert payment is not None
    db.guest_folios.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "closed"}},
    )

    refunded = refund_payment(payment["id"])

    assert refunded is not None
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    assert folio["status"] == "closed"
    assert folio["total_payments"] == 0
    assert any(p.get("reference_type") == "payment_refund" for p in folio["postings"])


def test_remove_last_tracked_product_restores_zero_stock(db):
    from src.app.modules.partner.services.hotel_products import add_booking_line_item, remove_booking_line_item

    booking_id = _booking(db, booking_id="BK-P1-PRODUCT-LAST-UNIT")
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "status": "open",
        "total_due": 100.0,
        "total_charges": 0.0,
        "total_payments": 0.0,
        "postings": [],
        "posting_count": 0,
    })
    db.hotel_products.insert_one({
        "prop_id": 901,
        "product_id": "PROD-P1-LAST-UNIT",
        "name": "Agua",
        "unit_price": 5.0,
        "quantity_available": 1,
        "stock_tracked": True,
    })

    item = add_booking_line_item(
        booking_id,
        product_id="PROD-P1-LAST-UNIT",
        name="Agua",
        unit_price=5.0,
        quantity=1,
    )
    assert item is not None
    assert db.hotel_products.find_one({"product_id": "PROD-P1-LAST-UNIT"})["quantity_available"] == 0

    assert remove_booking_line_item(booking_id, item["item_id"]) is True
    assert db.hotel_products.find_one({"product_id": "PROD-P1-LAST-UNIT"})["quantity_available"] == 1


def test_duplicate_amenity_lines_fail_without_partial_charge(db):
    from src.app.modules.amenities.service import request_amenities, set_amenity_stock

    booking_id = _booking(db, booking_id="BK-P1-AMENITY-DUPLICATE")
    db.hotel_content_pages.insert_one({"prop_id": 901, "amenity_prices": {"Toalla": 10.0}})
    set_amenity_stock(901, "Toalla", total_stock=1)

    result = request_amenities(booking_id, [
        {"label": "Toalla", "quantity": 1},
        {"label": "Toalla", "quantity": 1},
    ])

    assert result["ok"] is False
    assert result["items"] == []
    assert db.additional_charges.count_documents({"booking_id": booking_id}) == 0
    assert db.amenity_stock.find_one({"prop_id": 901, "amenity_label": "Toalla"})["available_stock"] == 1


def test_add_booking_line_item_rejects_insufficient_stock_without_mutation(db):
    """A product add-on cannot consume partial stock or create a line item."""
    from src.app.modules.partner.services.hotel_products import add_booking_line_item

    booking_id = _booking(db, booking_id="BK-P1-PRODUCT-STOCK")
    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": {"status": "confirmed"}})
    db.hotel_products.insert_one({
        "prop_id": 901,
        "product_id": "PROD-P1-STOCK",
        "name": "Agua",
        "unit_price": 5.0,
        "quantity_available": 2,
    })

    result = add_booking_line_item(
        booking_id,
        product_id="PROD-P1-STOCK",
        name="Agua",
        unit_price=5.0,
        quantity=3,
    )

    assert result is None
    product = db.hotel_products.find_one({"prop_id": 901, "product_id": "PROD-P1-STOCK"})
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    assert product["quantity_available"] == 2
    assert booking.get("line_items", []) == []


def test_close_folio_rejects_unapproved_writeoff_reason(db):
    booking_id = _booking(db, booking_id="BK-P1-CLOSE-REASON")
    create_folio(booking_id)

    assert close_folio(booking_id, closed_by="tester", close_reason="x") is None
    assert db.guest_folios.find_one({"booking_id": booking_id})["status"] == "open"


def test_room_status_writer_rejects_invalid_transition(db):
    from src.app.modules.housekeeping.schemas import RoomStatusLogCreate
    from src.app.modules.housekeeping.service.lifecycle.status import upsert_room_status

    upsert_room_status(RoomStatusLogCreate(
        prop_id=907,
        room_type_id="standard",
        room_label="101",
        status="vacant_clean",
    ))

    import pytest
    with pytest.raises(ValueError, match="transición"):
        upsert_room_status(RoomStatusLogCreate(
            prop_id=907,
            room_type_id="standard",
            room_label="101",
            status="occupied_dirty",
        ))


def test_confirmed_payment_rolls_back_when_existing_folio_posting_fails(db):
    """A race/lost folio posting must not leave a confirmed orphan payment."""
    booking_id = _booking(db, booking_id="BK-P1-PAYMENT-POST-FAIL")
    create_folio(booking_id)

    with patch(
        "src.app.modules.billing.service.folio.post_to_folio",
        return_value=None,
    ):
        payment = create_payment(PaymentCreate(
            booking_id=booking_id,
            amount=25.0,
            method="cash",
        ))

    assert payment is not None
    stored = db.reservation_payments.find_one({"reference": payment["reference"]})
    assert stored["status"] == "failed"
    assert db.ledger_transactions.count_documents({
        "source": "payment", "source_id": payment["reference"],
    }) == 0
    assert db.guest_folios.find_one({"booking_id": booking_id})["total_payments"] == 0


def test_refund_side_effect_failure_remains_retryable(db):
    """A failed reversal must not consume the payment state transition."""
    booking_id = _booking(db, booking_id="BK-P1-REFUND-RETRY")
    create_folio(booking_id)
    payment = create_payment(PaymentCreate(
        booking_id=booking_id,
        amount=25.0,
        method="cash",
    ))
    assert payment is not None

    with patch(
        "src.app.modules.expenses.service.ledger_hooks.post_journal_entry",
        side_effect=RuntimeError("ledger unavailable"),
    ):
        assert refund_payment(payment["id"]) is None

    stored = db.reservation_payments.find_one({"_id": ObjectId(payment["id"])})
    assert stored["status"] == "confirmed"
    assert db.guest_folios.count_documents({
        "booking_id": booking_id,
        "postings": {"$elemMatch": {"reference_type": "payment_refund"}},
    }) == 1

    refunded = refund_payment(payment["id"])
    assert refunded is not None
    assert db.reservation_payments.find_one({"_id": ObjectId(payment["id"])})["status"] == "refunded"
    assert db.ledger_transactions.count_documents({
        "source": "payment_refund", "source_id": payment["reference"],
    }) == 2


def test_bulk_room_status_rejects_invalid_transition_without_mutating_room(db):
    from src.app.modules.housekeeping.service.lifecycle.status import (
        update_room_status_bulk,
        upsert_room_status,
    )
    from src.app.modules.housekeeping.schemas import RoomStatusLogCreate

    upsert_room_status(RoomStatusLogCreate(
        prop_id=908,
        room_type_id="standard",
        room_label="101",
        status="vacant_clean",
    ))

    import pytest
    with pytest.raises(ValueError, match="transición"):
        update_room_status_bulk(908, ["101"], "occupied_dirty")

    assert db.room_status_log.find_one({
        "prop_id": 908, "room_label": "101",
    })["status"] == "vacant_clean"


def test_restock_uses_atomic_increment_when_stock_changes_between_read_and_write(db, monkeypatch):
    """A concurrent sale must not be overwritten by a restock's stale read."""
    from src.app.modules.partner.services import hotel_products as products_service

    db.hotel_products.insert_one({
        "prop_id": 909,
        "product_id": "PROD-P1-RESTOCK-RACE",
        "name": "Agua",
        "quantity_available": 10,
        "cost_price": 2.0,
    })
    real_collection = db.hotel_products

    class InterleavingCollection:
        def find_one(self, *args, **kwargs):
            return real_collection.find_one(*args, **kwargs)

        def update_one(self, query, update, *args, **kwargs):
            real_collection.update_one(
                {"prop_id": 909, "product_id": "PROD-P1-RESTOCK-RACE"},
                {"$inc": {"quantity_available": -3}},
            )
            return real_collection.update_one(query, update, *args, **kwargs)

    class DatabaseProxy:
        def __getattr__(self, name):
            if name == "hotel_products":
                return InterleavingCollection()
            return getattr(db, name)

        def __getitem__(self, name):
            return getattr(self, name)

    monkeypatch.setattr(products_service, "get_database", lambda: DatabaseProxy())
    products_service.restock_product(
        909,
        "PROD-P1-RESTOCK-RACE",
        qty=5,
        unit_cost=2.5,
    )

    assert db.hotel_products.find_one({
        "prop_id": 909, "product_id": "PROD-P1-RESTOCK-RACE",
    })["quantity_available"] == 12


def test_charge_mutations_reconcile_existing_invoice_immediately(db):
    """Create and void charge events must update an existing guest invoice."""
    from src.app.modules.billing.service import generate_invoice_for_booking
    from src.app.modules.housekeeping.service.lifecycle.charges import delete_additional_charge

    booking_id = _booking(db, booking_id="BK-P1-CHARGE-LIVE-INVOICE")
    invoice = generate_invoice_for_booking(booking_id)
    assert invoice is not None
    base_total = round(float(invoice["total"]), 2)
    create_folio(booking_id)

    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id, prop_id=901, concept="Minibar", amount=10.0,
    ))
    assert charge is not None
    current = db.reservation_invoices.find_one({"_id": ObjectId(invoice["id"])})
    assert current["extras_total"] == 10.0
    assert current["total"] > base_total

    assert delete_additional_charge(charge["id"]) is not None
    current = db.reservation_invoices.find_one({"_id": ObjectId(invoice["id"])})
    assert current["extras_total"] == 0.0
    assert current["total"] == base_total


def test_split_charge_invoice_ignores_reversed_charges_and_is_idempotent(db):
    from src.app.modules.billing.service import create_split_charges_invoice
    from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-CHARGES")
    first_charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id, prop_id=901, concept="Minibar", amount=10.0,
    ))
    reversed_charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id, prop_id=901, concept="Daño", amount=40.0,
    ))
    assert first_charge is not None and reversed_charge is not None
    db.additional_charges.update_one(
        {"_id": ObjectId(reversed_charge["id"])},
        {"$set": {"status": "reversed"}},
    )

    first = create_split_charges_invoice(booking_id)
    second = create_split_charges_invoice(booking_id)
    assert first is not None and second is not None
    assert first["id"] == second["id"]
    assert first["total"] == 11.6
    assert first["ledger_posting_status"] == "posted"
    assert [item["charge_id"] for item in first["line_items"]] == [first_charge["id"]]
    assert db.reservation_invoices.count_documents({
        "booking_id": booking_id, "split_type": "charges_only",
    }) == 1


def test_charge_invoice_reconciliation_surfaces_retryable_ledger_failure(db, monkeypatch):
    from src.app.modules.billing.service import generate_invoice_for_booking, update_invoice_additional_charges
    from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge

    booking_id = _booking(db, booking_id="BK-P1-CHARGE-LEDGER-FAIL")
    invoice = generate_invoice_for_booking(booking_id)
    assert invoice is not None
    create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id, prop_id=901, concept="Spa", amount=15.0,
    ))

    def fail_posting(**_kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(
        "src.app.modules.expenses.service.ledger_hooks.post_journal_entry",
        fail_posting,
    )
    result = update_invoice_additional_charges(booking_id)
    assert result is not None
    assert result["ledger_posting_status"] == "failed"
    assert "ledger unavailable" in result["ledger_posting_error"]


def test_charge_edit_or_delete_does_not_race_an_in_progress_posting(db):
    from src.app.modules.housekeeping.service.lifecycle.charges import (
        delete_additional_charge, update_additional_charge,
    )
    from src.app.modules.housekeeping.schemas import AdditionalChargeUpdate

    booking_id = _booking(db, booking_id="BK-P1-CHARGE-IN-PROGRESS")
    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id, prop_id=901, concept="Minibar", amount=10.0,
    ))
    assert charge is not None
    db.additional_charges.update_one(
        {"_id": ObjectId(charge["id"])},
        {"$set": {"posting_status": "updating"}},
    )

    current = update_additional_charge(charge["id"], AdditionalChargeUpdate(amount=20.0))
    assert current is not None
    assert current["postingStatus"] == "updating"
    assert db.additional_charges.find_one({"_id": ObjectId(charge["id"])})["amount"] == 10.0
    assert delete_additional_charge(charge["id"]) is None


def test_issued_invoice_with_confirmed_payment_cannot_be_mutated(db):
    from src.app.modules.billing.service.lifecycle.invoices import add_line_item, remove_line_item

    booking_id = _booking(db, booking_id="BK-P1-INVOICE-IMMUTABLE")
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "invoice_number": "INV-P1-IMMUTABLE",
        "room_subtotal": 100.0,
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "issued",
        "line_items": [{"item_id": "room-1", "type": "room", "total": 100.0}],
    }).inserted_id
    db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "invoice_id": invoice_id,
        "amount": 20.0,
        "status": "confirmed",
    })

    assert add_line_item(str(invoice_id), name="Parking", unit_price=10.0) is None
    assert remove_line_item(str(invoice_id), "room-1") is None
    assert db.reservation_invoices.find_one({"_id": invoice_id})["total"] == 116.0


def test_reconciliation_does_not_mutate_invoice_with_confirmed_payment(db):
    """A paid/partially-paid fiscal snapshot cannot be rewritten by a charge retry."""
    from src.app.modules.billing.service.lifecycle.invoices import update_invoice_additional_charges

    booking_id = _booking(db, booking_id="BK-P1-PAID-CHARGE-RECON")
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "invoice_number": "INV-P1-PAID-CHARGE",
        "room_subtotal": 100.0,
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "partially_paid",
        "line_items": [{"item_id": "room-1", "type": "room", "total": 100.0}],
    }).inserted_id
    db.reservation_payments.insert_one({
        "booking_id": booking_id,
        "invoice_id": invoice_id,
        "amount": 40.0,
        "status": "confirmed",
    })
    db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Late checkout",
        "amount": 25.0,
        "quantity": 1,
        "total": 25.0,
        "status": "active",
    })

    import pytest
    with pytest.raises(ValueError, match="pagos confirmados"):
        update_invoice_additional_charges(booking_id, changed_by="test")

    unchanged = db.reservation_invoices.find_one({"_id": invoice_id})
    assert unchanged["total"] == 116.0
    assert unchanged["line_items"] == [{"item_id": "room-1", "type": "room", "total": 100.0}]


def test_stuck_update_requires_reversal_and_replacement_before_recovery(db):
    """Recovery must not confirm a revision when the old posting was not reversed."""
    from src.app.modules.billing.service.lifecycle.invoices import update_invoice_additional_charges
    from src.app.modules.housekeeping.service.lifecycle.charges import recover_additional_charge

    booking_id = _booking(db, booking_id="BK-P1-UPDATE-RECOVERY")
    create_folio(booking_id)
    invoice_id = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "invoice_number": "INV-P1-UPDATE-RECOVERY",
        "room_subtotal": 100.0,
        "subtotal": 100.0,
        "taxes": 16.0,
        "total": 116.0,
        "status": "issued",
        "line_items": [{"item_id": "room-1", "type": "room", "total": 100.0}],
    }).inserted_id
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Room service",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "category": "room_service",
        "status": "active",
        "posting_status": "updating",
        "posting_version": 1,
        "pending_update": {"amount": 20.0, "quantity": 1, "total": 20.0, "concept": "Room service"},
    }).inserted_id
    post_to_folio(
        booking_id,
        posting_type="charge",
        category="room_service",
        concept="Room service",
        amount=20.0,
        reference_id=f"{charge_id}:v2",
        reference_type="additional_charge_revision",
    )

    incomplete = recover_additional_charge(str(charge_id))
    assert incomplete is not None
    assert incomplete["posting_status"] == "updating"
    assert db.additional_charges.find_one({"_id": charge_id})["amount"] == 10.0

    post_to_folio(
        booking_id,
        posting_type="charge_reversal",
        category="room_service",
        concept="[EDITADO] Room service",
        amount=10.0,
        reference_id=f"{charge_id}:v1:reversal",
        reference_type="charge_edit_reversal",
    )
    recovered = recover_additional_charge(str(charge_id))
    assert recovered is not None
    assert recovered["posting_status"] == "posted"
    assert recovered["amount"] == 20.0
    invoice = db.reservation_invoices.find_one({"_id": invoice_id})
    assert invoice["extras_total"] == 20.0
    assert invoice["total"] == 139.2


def test_migration_recovers_only_stuck_charges_with_existing_posting(db):
    from scripts.migrate_financial_reconciliation import recover_stuck_charges

    booking_id = _booking(db, booking_id="BK-P1-MIGRATION-RECOVERY")
    create_folio(booking_id)
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Minibar",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "category": "minibar",
        "status": "active",
        "posting_status": "reversing",
        "posting_version": 1,
    }).inserted_id
    post_to_folio(
        booking_id,
        posting_type="charge_reversal",
        category="minibar",
        concept="[ANULADO] Minibar",
        amount=10.0,
        reference_id=f"{charge_id}:v1:reversal",
        reference_type="charge_reversal",
    )

    result = recover_stuck_charges(db, prop_id=901, apply=True)
    assert result["recovered"] == 1
    assert db.additional_charges.find_one({"_id": charge_id})["status"] == "reversed"


def test_stuck_charge_recovery_finishes_existing_reversal(db):
    from src.app.modules.housekeeping.service.lifecycle.charges import recover_additional_charge

    booking_id = _booking(db, booking_id="BK-P1-CHARGE-RECOVER")
    create_folio(booking_id)
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Minibar",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "category": "minibar",
        "status": "active",
        "posting_status": "reversing",
        "posting_version": 1,
    }).inserted_id
    post_to_folio(
        booking_id,
        posting_type="charge_reversal",
        category="minibar",
        concept="[ANULADO] Minibar",
        amount=10.0,
        reference_id=f"{charge_id}:v1:reversal",
        reference_type="charge_reversal",
    )

    recovered = recover_additional_charge(str(charge_id))
    assert recovered is not None
    assert recovered["status"] == "reversed"
    assert recovered["posting_status"] == "reversed"
    assert db.guest_folios.count_documents({
        "booking_id": booking_id,
        "postings": {"$elemMatch": {"reference_id": f"{charge_id}:v1:reversal"}},
    }) == 1


def test_maintenance_delete_cleans_vendor_invoice_reverse_link(db):
    """Deleting a work order removes only its AP reverse link."""
    prop_id = 909
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "Delete Link Hotel"})
    room_id = "HR-909-101"
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id, "prop_id": prop_id, "room_label": "101", "room_type_id": "standard",
    })
    invoice_id = db.expense_invoices.insert_one({
        "prop_id": prop_id, "vendor_name": "Proveedor", "total": 125.0, "status": "approved",
    }).inserted_id
    task = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=prop_id, room_id=room_id, task_type="corrective", title="Bomba",
        expense_invoice_id=str(invoice_id),
    ))

    from src.app.modules.housekeeping.service.lifecycle.maintenance import delete_maintenance_task
    deleted = delete_maintenance_task(task["id"])
    assert deleted is not None
    linked = db.expense_invoices.find_one({"_id": invoice_id})
    assert linked["maintenance_task_ids"] == []
    assert linked["maintenance_task_id"] is None


def test_maintenance_create_response_contains_financial_link_state(db):
    """The create response must reflect the persisted invoice link immediately."""
    prop_id = 910
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "Response Link Hotel"})
    room_id = "HR-910-101"
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id, "prop_id": prop_id, "room_label": "101", "room_type_id": "standard",
    })
    invoice_id = db.expense_invoices.insert_one({
        "prop_id": prop_id, "vendor_name": "Proveedor", "total": 125.0, "status": "approved",
    }).inserted_id
    task = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=prop_id, room_id=room_id, task_type="corrective", title="Bomba",
        expense_invoice_id=str(invoice_id),
    ))
    assert task["financialLinkStatus"] == "linked"
    assert task["ledgerStatus"] == "pending"


def test_maintenance_relink_cleans_old_reverse_link_and_keeps_other_task(db):
    """Changing one work order must not leave stale or destructive AP links."""
    from src.app.modules.housekeeping.service.lifecycle.maintenance import update_maintenance_task

    prop_id = 908
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "Relink Hotel"})
    room_id = "HR-908-101"
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id, "prop_id": prop_id, "room_label": "101", "room_type_id": "standard",
    })
    invoice_id = db.expense_invoices.insert_one({
        "prop_id": prop_id, "vendor_name": "Proveedor", "total": 125.0, "status": "approved",
    }).inserted_id
    first = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=prop_id, room_id=room_id, task_type="corrective", title="Bomba A",
        expense_invoice_id=str(invoice_id),
    ))
    second = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=prop_id, room_id=room_id, task_type="corrective", title="Bomba B",
        expense_invoice_id=str(invoice_id),
    ))
    assert set(db.expense_invoices.find_one({"_id": invoice_id})["maintenance_task_ids"]) == {first["id"], second["id"]}

    update_maintenance_task(first["id"], MaintenanceTaskCreate(
        prop_id=prop_id, room_id=room_id, task_type="corrective", title="Bomba A",
        expense_invoice_id=None,
    ))
    linked = db.expense_invoices.find_one({"_id": invoice_id})
    assert linked["maintenance_task_ids"] == [second["id"]]
    assert linked.get("maintenance_task_id") == second["id"]


def test_split_invoice_reconciles_changed_active_charge_snapshot(db):
    """An issued split invoice converges when active charges change before payment."""
    from src.app.modules.billing.service.lifecycle.invoices import create_split_charges_invoice

    booking_id = _booking(db, booking_id="BK-P1-SPLIT-SNAPSHOT")
    charge_id = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 901,
        "concept": "Minibar",
        "amount": 10.0,
        "quantity": 1,
        "total": 10.0,
        "status": "active",
    }).inserted_id

    first = create_split_charges_invoice(booking_id)
    assert first is not None
    db.additional_charges.update_one({"_id": charge_id}, {"$set": {"amount": 20.0, "total": 20.0}})

    second = create_split_charges_invoice(booking_id)
    assert second is not None
    assert second["id"] == first["id"]
    assert second["total"] == 23.2
    assert db.reservation_invoices.count_documents({"booking_id": booking_id, "split_type": "charges_only"}) == 1


def test_maintenance_links_same_hotel_vendor_invoice_and_exposes_pending_ledger(db):
    from src.app.modules.housekeeping.service.lifecycle.maintenance import create_maintenance_task

    prop_id = 907
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "Maintenance Link Hotel"})
    room_id = "HR-907-101"
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id, "prop_id": prop_id, "room_label": "101", "room_type_id": "standard",
    })
    invoice_id = db.expense_invoices.insert_one({
        "prop_id": prop_id, "vendor_name": "Proveedor", "total": 125.0, "status": "approved",
    }).inserted_id

    task = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=prop_id, room_id=room_id, task_type="corrective", title="Bomba",
        actual_cost=125.0, currency="USD", vendor_name="Proveedor",
        expense_invoice_id=str(invoice_id),
    ))

    linked_invoice = db.expense_invoices.find_one({"_id": invoice_id})
    stored = db.maintenance_tasks.find_one({"_id": ObjectId(task["id"])})
    assert linked_invoice["maintenance_task_id"] == task["id"]
    assert stored["expense_invoice_id"] == str(invoice_id)
    assert stored["ledger_status"] == "pending"


def test_booking_persists_immutable_pricing_snapshot(db):
    """Changing the live calendar must not change the sold reservation terms."""
    from src.app.modules.reservations.service._helpers import ReservationInput
    from src.app.modules.reservations.service.lifecycle.create.core import create_booking

    prop_id = 906
    rate_plan_id = "RP-906-SNAPSHOT"
    for day in ("2026-08-10", "2026-08-11", "2026-08-12"):
        db.hotel_rate_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-906-deluxe",
            "rate_plan_id": rate_plan_id,
            "date": day,
            "rate_amount": 150.0,
            "currency": "USD",
        })
    db.rate_plans.insert_one({
        "prop_id": prop_id,
        "rate_plan_id": rate_plan_id,
        "name": "Snapshot Flexible",
    })
    for day in ("2026-08-10", "2026-08-11", "2026-08-12"):
        db.room_inventory_calendar.insert_one({
            "prop_id": prop_id,
            "room_type_id": "RT-906-deluxe",
            "date": day,
            "total_rooms": 10,
            "available_rooms": 10,
            "is_available": True,
        })

    result = create_booking(ReservationInput(
        prop_id=prop_id,
        guest_name="Snapshot Guest",
        guest_email="snapshot@test.com",
        room_type_id="RT-906-deluxe",
        rate_plan_id=rate_plan_id,
        check_in_date="2026-08-10",
        check_out_date="2026-08-13",
        adults=2,
        children=0,
        rooms=1,
        comment="",
        source="test",
        is_test=True,
    ))
    booking = db.booking_orders.find_one({"booking_id": result["booking_id"]})

    assert booking["pricing_source"] == "hotel_rate_calendar"
    assert booking["rate_plan_name_snapshot"] == "Snapshot Flexible"
    assert booking["price_snapshot"]["currency"] == "USD"
    assert len(booking["price_snapshot"]["nightly_breakdown"]) == 3
    assert sum(row["night_total"] for row in booking["price_snapshot"]["nightly_breakdown"]) == 450.0


def test_additional_charge_invoice_reconciliation_is_exact_and_idempotent(db):
    """Invoice, booking total and ledger must converge to active charges only."""
    from src.app.modules.billing.service import generate_invoice_for_booking, update_invoice_additional_charges
    from src.app.modules.housekeeping.service.lifecycle.charges import (
        delete_additional_charge,
    )

    booking_id = _booking(db, booking_id="BK-P1-CHARGE-INVOICE-SYNC")
    invoice = generate_invoice_for_booking(booking_id)
    assert invoice is not None

    create_folio(booking_id)
    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=901,
        concept="Daño de habitación",
        amount=25.0,
    ))
    assert charge is not None
    assert charge["posting_status"] == "posted"

    first = update_invoice_additional_charges(booking_id)
    second = update_invoice_additional_charges(booking_id)
    assert first is not None
    assert second is not None
    base_total = round(float(invoice["total"]), 2)
    expected_with_charge = round(
        float(invoice["room_subtotal"]) + 25.0
        + round((float(invoice["room_subtotal"]) + 25.0) * 0.16, 2),
        2,
    )
    assert first["total"] == expected_with_charge
    assert second["total"] == expected_with_charge
    assert second["extras_total"] == 25.0
    assert len([
        item for item in second["line_items"]
        if item.get("type") == "additional_charge"
    ]) == 1
    assert db.booking_orders.find_one({"booking_id": booking_id})["total_charges"] == 25.0

    adjustment_rows = list(db.ledger_transactions.find({
        "source": "invoice_additional_charge_adjustment",
        "source_id": invoice["invoice_number"],
    }))
    assert len(adjustment_rows) == 2
    assert round(sum(row.get("debit", 0) for row in adjustment_rows), 2) == 25.0
    assert round(sum(row.get("credit", 0) for row in adjustment_rows), 2) == 25.0

    assert delete_additional_charge(charge["id"]) is not None
    after_void = update_invoice_additional_charges(booking_id)
    assert after_void is not None
    assert after_void["total"] == base_total
    assert after_void["extras_total"] == 0.0
    assert not any(
        item.get("type") == "additional_charge"
        for item in after_void["line_items"]
    )
    assert db.ledger_transactions.count_documents({
        "source": "invoice_additional_charge_adjustment",
        "source_id": invoice["invoice_number"],
    }) == 0

    # A retry after the void must not recreate a charge or a ledger adjustment.
    retry = update_invoice_additional_charges(booking_id)
    assert retry is not None
    assert retry["total"] == base_total
    assert db.ledger_transactions.count_documents({
        "source": "invoice_additional_charge_adjustment",
        "source_id": invoice["invoice_number"],
    }) == 0
