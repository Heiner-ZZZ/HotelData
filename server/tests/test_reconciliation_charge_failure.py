from datetime import datetime, timezone

from src.app.modules.billing.service.folio import create_folio
from src.app.modules.financial_reconciliation.service import build_reconciliation_report
from src.app.modules.housekeeping.schemas import AdditionalChargeCreate
from src.app.modules.housekeeping.service.lifecycle.charges import create_additional_charge


def test_failed_charge_finding_exposes_retry_state_and_error(db):
    db.dim_hotels.insert_one({"prop_id": 707, "display_name": "Charge Failure Hotel"})
    charge_id = db.additional_charges.insert_one({
        "prop_id": 707,
        "booking_id": "BK-CHARGE-FAILED",
        "amount": 10.02,
        "posting_status": "posting_failed",
        "posting_error": "guest folio is not open",
    }).inserted_id

    report = build_reconciliation_report(707)

    finding = next(
        item for item in report["findings"]
        if item["domain"] == "charge" and str(charge_id) in item["source_ids"]
    )
    assert finding["actual"]["posting_status"] == "posting_failed"
    assert finding["actual"]["posting_error"] == "guest folio is not open"
    assert finding["repair_policy"] == "manual"


def test_charge_persists_complete_folio_trace_after_successful_posting(db):
    """A posted charge must retain its source-to-folio reference, not just a status."""
    db.dim_hotels.insert_one({"prop_id": 708, "display_name": "Charge Trace Hotel"})
    booking_id = "BK-CHARGE-TRACE"
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 708,
        "guest_name": "Charge Trace",
        "total_price": 100.0,
        "total_nights": 1,
        "status": "confirmed",
        "stay_status": "checked_in",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-11",
        "created_at": datetime.now(timezone.utc),
    })
    create_folio(booking_id)

    charge = create_additional_charge(AdditionalChargeCreate(
        booking_id=booking_id,
        prop_id=708,
        concept="Minibar",
        amount=12.50,
    ))

    assert charge is not None
    stored = db.additional_charges.find_one({"booking_id": booking_id})
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    posting = next(
        p for p in folio["postings"]
        if p.get("reference_id") == str(stored["_id"])
        and p.get("reference_type") == "additional_charge"
    )
    assert stored["posting_status"] == "posted"
    assert stored["folio_id"] == folio["_id"]
    assert stored["folio_number"] == folio["folio_number"]
    assert stored["posting_id"] == posting["posting_id"]
    assert stored["posting_reference"] == str(stored["_id"])
    assert db.hotel_domain_events.count_documents({
        "prop_id": 708,
        "event_type": "operations.additional_charge.posted",
        "idempotency_key": f"additional-charge-posting:v1:{stored['_id']}",
    }) == 1
    assert db.fact_hotel_domain_events.count_documents({
        "prop_id": 708,
        "event_type": "operations.additional_charge.posted",
        "idempotency_key": f"additional-charge-posting:v1:{stored['_id']}",
    }) == 1
