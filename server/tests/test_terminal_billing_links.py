"""Regression tests for terminal-reservation billing links.

The operational booking key is the business ``booking_id`` (``BK-...``),
while older migrations may have stored an invoice FK as the booking's Mongo
``_id``. Reception detail pages must resolve both forms and must recover a
persisted folio after a reload instead of relying on transient UI state.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.modules.reservations.service._checkout_detail import get_check_out_detail
from src.app.modules.reservations.service.queries import get_booking_detail


def _seed_booking(db, booking_id: str, **overrides) -> object:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Terminal Link Guest",
        "guest_email": "terminal-links@test.com",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-12",
        "total_price": 218.0,
        "currency": "USD",
        "total_nights": 2,
        "rooms": 1,
        "assigned_rooms": [],
        "status": "confirmed",
        "stay_status": "checked_out",
        "created_at": datetime.now(timezone.utc),
        "is_test": True,
    }
    doc.update(overrides)
    return db.booking_orders.insert_one(doc).inserted_id


def test_reservation_detail_finds_invoice_by_business_booking_id(db):
    """Reloading reservation detail must show invoices written with ``BK-...``."""
    booking_id = "BK-TERMINAL-BUSINESS-KEY"
    _seed_booking(db, booking_id)
    db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "invoice_number": "INV-BUSINESS-KEY",
        "subtotal": 188.0,
        "taxes": 30.0,
        "total": 218.0,
        "status": "issued",
    })

    detail = get_booking_detail(booking_id)

    assert detail is not None
    assert detail["invoice"]["invoice_number"] == "INV-BUSINESS-KEY"


def test_reservation_detail_keeps_legacy_object_id_invoice_links(db):
    """Historical invoice rows keyed by the booking Mongo id remain readable."""
    booking_id = "BK-TERMINAL-LEGACY-KEY"
    booking_oid = _seed_booking(db, booking_id)
    db.reservation_invoices.insert_one({
        "booking_id": booking_oid,
        "prop_id": 1,
        "invoice_number": "INV-LEGACY-OBJECT-ID",
        "subtotal": 188.0,
        "taxes": 30.0,
        "total": 218.0,
        "status": "issued",
    })

    detail = get_booking_detail(booking_id)

    assert detail is not None
    assert detail["invoice"]["invoice_number"] == "INV-LEGACY-OBJECT-ID"


def test_checkout_detail_falls_back_to_persisted_guest_folio(db):
    """Checkout reload uses ``guest_folios`` when booking.folio is empty."""
    booking_id = "BK-TERMINAL-FOLIO-FALLBACK"
    _seed_booking(db, booking_id, stay_status="checked_out", folio=None)
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": "FL-PERSISTED-CHECKOUT",
        "status": "closed",
    })

    detail = get_check_out_detail(booking_id)

    assert detail["folio"] == "FL-PERSISTED-CHECKOUT"


def test_checkout_detail_exposes_persisted_no_show_penalty_after_reload(db):
    """A reloaded no-show keeps the amount needed to render its billing link."""
    booking_id = "BK-TERMINAL-NOSHOW-RELOAD"
    _seed_booking(
        db,
        booking_id,
        stay_status="no_show",
        folio="FL-NS-PERSISTED",
        no_show_penalty_amount=94.0,
        no_show_penalty_percent=50,
    )

    detail = get_check_out_detail(booking_id)

    assert detail["stay_status"] == "no_show"
    assert detail["folio"] == "FL-NS-PERSISTED"
    assert detail["no_show_penalty_amount"] == 94.0
