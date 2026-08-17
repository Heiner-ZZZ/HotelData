from __future__ import annotations

from bson import ObjectId

from src.app.modules.reservations.service.cleanup import cleanup_test_booking


BOOKING_ID = "BK-CLEANUP-AGGREGATE"


def test_cleanup_test_booking_removes_the_full_cross_module_aggregate(db):
    booking_oid = ObjectId()
    folio_oid = ObjectId()
    invoice_oid = ObjectId()
    payment_oid = ObjectId()
    settlement_event_oid = ObjectId()
    shift_oid = ObjectId()
    posting_id = "POST-CLEANUP-ROOM"
    invoice_number = "INV-CLEANUP-001"
    folio_number = "FL-CLEANUP-001"

    db.booking_orders.insert_one(
        {
            "_id": booking_oid,
            "booking_id": BOOKING_ID,
            "is_test": True,
            "prop_id": 990,
            "guest_name": "Synthetic Guest",
        }
    )
    db.booking_guests.insert_one({"booking_id": BOOKING_ID, "guest_name": "Synthetic Guest"})
    db.booking_room_guests.insert_one({"booking_id": BOOKING_ID, "room_index": 0})
    db.booking_status_history.insert_many([
        {"booking_id": BOOKING_ID, "status": "pending"},
        {"booking_id": BOOKING_ID, "status": "confirmed"},
    ])
    db.manual_reservations.insert_one({"booking_id": BOOKING_ID})

    db.guest_folios.insert_one(
        {
            "_id": folio_oid,
            "booking_id": BOOKING_ID,
            "folio_number": folio_number,
            "status": "open",
            "postings": [{"posting_id": posting_id, "amount": 100.0}],
        }
    )
    db.additional_charges.insert_one(
        {
            "booking_id": BOOKING_ID,
            "folio_id": folio_oid,
            "total": 20.0,
            "posting_id": "POST-CLEANUP-CHARGE",
        }
    )
    db.reservation_invoices.insert_one(
        {
            "_id": invoice_oid,
            "booking_id": BOOKING_ID,
            "invoice_number": invoice_number,
            "total": 120.0,
            "status": "issued",
        }
    )
    db.fact_reservation_invoices.insert_one(
        {
            "_id": invoice_oid,
            "booking_id": BOOKING_ID,
            "invoice_number": invoice_number,
            "total": 120.0,
        }
    )
    db.reservation_payments.insert_one(
        {
            "_id": payment_oid,
            "booking_id": BOOKING_ID,
            "invoice_id": invoice_oid,
            "amount": 20.0,
            "status": "confirmed",
        }
    )
    db.fact_reservation_payments.insert_one(
        {
            "_id": payment_oid,
            "booking_id": BOOKING_ID,
            "invoice_id": invoice_oid,
            "amount": 20.0,
        }
    )
    db.refund_documents.insert_one(
        {"payment_id": payment_oid, "invoice_id": invoice_oid, "document_number": "RF-CLEANUP-001"}
    )
    db.fact_refund_documents.insert_one(
        {"payment_id": payment_oid, "invoice_id": invoice_oid, "document_number": "RF-CLEANUP-001"}
    )
    db.folio_settlement_events.insert_one(
        {
            "_id": settlement_event_oid,
            "booking_id": BOOKING_ID,
            "folio_id": folio_oid,
            "invoice_id": invoice_oid,
            "payment_id": payment_oid,
        }
    )
    db.fact_folio_settlement_events.insert_one(
        {
            "_id": settlement_event_oid,
            "booking_id": BOOKING_ID,
            "folio_id": folio_oid,
            "invoice_id": invoice_oid,
            "payment_id": payment_oid,
        }
    )
    db.ledger_transactions.insert_many([
        {"booking_id": BOOKING_ID, "source": "invoice", "source_id": invoice_number},
        {"booking_id": BOOKING_ID, "source": "folio_posting", "source_id": posting_id},
    ])
    db.platform_earnings.insert_one({"booking_id": BOOKING_ID, "booking_total": 120.0})
    db.notification_log.insert_many([
        {"booking_id": BOOKING_ID, "notification_type": "guest_confirmed"},
        {"entity_id": BOOKING_ID, "notification_type": "housekeeping_check_in"},
    ])
    db.hotel_domain_events.insert_one(
        {
            "event_id": "EV-CLEANUP-001",
            "payload": {"booking_id": BOOKING_ID, "folio_id": str(folio_oid)},
            "source_id": invoice_number,
        }
    )
    db.fact_hotel_domain_events.insert_one(
        {
            "_id": ObjectId(),
            "event_id": "EV-CLEANUP-001",
            "payload": {"booking_id": BOOKING_ID, "folio_id": str(folio_oid)},
            "source_id": invoice_number,
        }
    )
    db.audit_log.insert_many([
        {"entity_type": "reservation", "entity_id": BOOKING_ID},
        {
            "entity_type": "permission",
            "summary": f"403 path /api/reservations/{BOOKING_ID}/special-requests",
            "metadata": {"path": f"/api/reservations/{BOOKING_ID}/special-requests"},
        },
    ])
    db.outbox.insert_many([
        {
            "event_type": "insert",
            "document": {"booking_id": BOOKING_ID, "invoice_number": invoice_number},
            "status": "processed",
        },
        {
            "event_type": "audit_log_insert",
            "document": {
                "summary": f"403 path /api/reservations/{BOOKING_ID}/special-requests",
                "metadata": {"path": f"/api/reservations/{BOOKING_ID}/special-requests"},
            },
            "status": "processed",
        },
    ])
    db.reception_shifts.insert_one(
        {
            "_id": shift_oid,
            "prop_id": 990,
            "status": "closed",
            "booking_ids": [str(booking_oid), "BK-OTHER"],
            "folio_ids": [str(folio_oid), "FL-OTHER"],
            "transactions": [
                {"booking_id": BOOKING_ID, "amount": 120.0},
                {"booking_id": "BK-OTHER", "amount": 50.0},
            ],
        }
    )

    result = cleanup_test_booking(BOOKING_ID)

    assert result["deleted"] is True
    assert result["booking_id"] == BOOKING_ID
    assert result["counts"]["booking_orders"] == 1
    assert result["counts"]["guest_folios"] == 1
    assert result["counts"]["reservation_invoices"] == 1
    assert result["counts"]["reservation_payments"] == 1
    assert result["counts"]["ledger_transactions"] == 2
    assert result["counts"]["hotel_domain_events"] == 1
    assert result["counts"]["fact_hotel_domain_events"] == 1

    for collection in (
        "booking_orders",
        "booking_guests",
        "booking_room_guests",
        "booking_status_history",
        "manual_reservations",
        "guest_folios",
        "additional_charges",
        "reservation_invoices",
        "fact_reservation_invoices",
        "reservation_payments",
        "fact_reservation_payments",
        "refund_documents",
        "fact_refund_documents",
        "folio_settlement_events",
        "fact_folio_settlement_events",
        "ledger_transactions",
        "platform_earnings",
        "notification_log",
        "hotel_domain_events",
        "fact_hotel_domain_events",
        "audit_log",
        "outbox",
    ):
        assert db[collection].count_documents({"booking_id": BOOKING_ID}) == 0
        assert db[collection].count_documents({"folio_id": folio_oid}) == 0
        assert db[collection].count_documents({"invoice_id": invoice_oid}) == 0
    assert db.notification_log.count_documents({"entity_id": BOOKING_ID}) == 0

    shift = db.reception_shifts.find_one({"_id": shift_oid})
    assert shift["booking_ids"] == ["BK-OTHER"]
    assert shift["folio_ids"] == ["FL-OTHER"]
    assert shift["transactions"] == [{"booking_id": "BK-OTHER", "amount": 50.0}]


def test_cleanup_test_booking_refuses_non_test_booking(db):
    db.booking_orders.insert_one({"booking_id": "BK-NOT-TEST", "is_test": False})

    result = cleanup_test_booking("BK-NOT-TEST")

    assert result == {
        "booking_id": "BK-NOT-TEST",
        "deleted": False,
        "reason": "not_marked_as_test",
    }
    assert db.booking_orders.find_one({"booking_id": "BK-NOT-TEST"}) is not None
