from src.app.modules.billing.schemas import PaymentCreate
from src.app.modules.billing.service.lifecycle.payments import create_payment, refund_payment
from src.app.modules.billing.service.folio import create_folio


def test_refund_retry_with_same_refund_id_is_idempotent(db):
    prop_id = 991
    booking_id = "BK-P1-REFUND-RETRY"
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "Refund Retry Hotel"})
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "status": "confirmed",
        "stay_status": "checked_in",
        "guest_name": "Refund Retry",
        "total_price": 100.0,
        "total_nights": 1,
    })
    create_folio(booking_id)
    payment = create_payment(PaymentCreate(booking_id=booking_id, amount=100.0, method="card"))

    first = refund_payment(payment["id"], refund_id="RF-P1-REFUND-RETRY")
    retry = refund_payment(payment["id"], refund_id="RF-P1-REFUND-RETRY")

    assert first is not None
    assert retry is not None
    assert retry["status"] == "refunded"
    assert retry["refund_id"] == "RF-P1-REFUND-RETRY"
    assert db.guest_folios.count_documents({
        "booking_id": booking_id,
        "postings.reference_id": "RF-P1-REFUND-RETRY",
    }) == 1
    assert db.ledger_transactions.count_documents({
        "source": "payment_refund",
        "source_id": "RF-P1-REFUND-RETRY",
    }) == 2
