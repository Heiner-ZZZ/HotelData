"""Tests for the line_items ↔ guest folio reconciliation circuit.

Direction booking → folio: a product added to the booking posts a charge to
the folio; removing it must post a compensating ``charge_reversal`` so the
folio never keeps orphan revenue.

Direction folio → booking: a manual folio charge ("Agregar cargo") must be
mirrored into ``booking.line_items`` so the reservation detail and invoice
see it — closing the two-source gap.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.partner.services.hotel_products import (
    add_booking_line_item,
    remove_booking_line_item,
)


def _seed_booking(db, booking_id: str = "BK-FOLIO-RECON", prop_id: int = 1) -> None:
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "Reconcile Guest",
        "status": "confirmed",
        "stay_status": "checked_in",
        "total_price": 100.0,
        "total_charges": 0.0,
        "line_items": [],
        "created_at": datetime.now(timezone.utc),
    })


def _seed_open_folio(db, booking_id: str, prop_id: int = 1) -> str:
    folio = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "folio_number": f"FL-RECON-{booking_id}",
        "status": "open",
        "total_room": 100.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": 100.0,
        "postings": [],
        "posting_count": 0,
        "created_at": datetime.now(timezone.utc),
    })
    return str(folio.inserted_id)


def _seed_product(db, prop_id: int = 1, product_id: str = "PROD-RECON") -> None:
    db.hotel_products.insert_one({
        "prop_id": prop_id,
        "hotel_id": f"H-{prop_id}",
        "product_id": product_id,
        "name": "Minibar",
        "unit_price": 12.0,
        "quantity_available": 10,
        "stock_tracked": True,
        "category": "Minibar",
        "is_active": True,
    })


class TestManualFolioChargeMirrorsToBooking:
    def test_manual_charge_creates_line_item_and_updates_totals(self, db):
        from src.app.modules.billing.service.folio import post_to_folio
        _seed_booking(db)
        _seed_open_folio(db, "BK-FOLIO-RECON")

        result = post_to_folio(
            "BK-FOLIO-RECON",
            posting_type="charge",
            category="restaurante",
            concept="Masaje relajante",
            amount=40.0,
            quantity=1,
            reference_type="manual",
        )
        assert result is not None

        booking = db.booking_orders.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert booking["total_charges"] == 40.0
        items = booking["line_items"]
        assert len(items) == 1
        assert items[0]["type"] == "folio_charge"
        assert items[0]["name"] == "Masaje relajante"
        assert items[0]["total"] == 40.0
        assert items[0]["category"] == "restaurante"

    def test_manual_charge_syncs_into_issued_invoice(self, db):
        from src.app.modules.billing.service.folio import post_to_folio
        _seed_booking(db)
        _seed_open_folio(db, "BK-FOLIO-RECON")
        db.reservation_invoices.insert_one({
            "booking_id": "BK-FOLIO-RECON",
            "prop_id": 1,
            "invoice_number": "INV-RECON-001",
            "status": "issued",
            "line_items": [],
            "room_subtotal": 100.0,
            "extras_total": 0.0,
            "subtotal": 100.0,
            "taxes": 0.0,
            "total": 100.0,
        })

        post_to_folio(
            "BK-FOLIO-RECON",
            posting_type="charge",
            category="minibar",
            concept="Agua mineral",
            amount=5.0,
            quantity=1,
            reference_type="manual",
        )

        inv = db.reservation_invoices.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert inv["extras_total"] == 5.0
        assert len(inv["line_items"]) == 1
        assert inv["line_items"][0]["name"] == "Agua mineral"

    def test_charge_reversal_removes_mirrored_line_item(self, db):
        from src.app.modules.billing.service.folio import post_to_folio
        _seed_booking(db)
        _seed_open_folio(db, "BK-FOLIO-RECON")

        posted = post_to_folio(
            "BK-FOLIO-RECON",
            posting_type="charge",
            category="restaurante",
            concept="Cena",
            amount=25.0,
            quantity=1,
            reference_type="manual",
        )
        posting = next(p for p in posted["postings"] if p["type"] == "charge")
        posting_id = str(posting["posting_id"])

        reversed_folio = post_to_folio(
            "BK-FOLIO-RECON",
            posting_type="charge_reversal",
            category="restaurante",
            concept="Anulación Cena",
            amount=25.0,
            quantity=1,
            reference_id=posting_id,
            reference_type="manual",
        )
        assert reversed_folio is not None
        assert reversed_folio["total_charges"] == 0.0

        booking = db.booking_orders.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert booking["total_charges"] == 0.0
        assert booking["line_items"] == []

    def test_additional_charge_postings_are_not_mirrored(self, db):
        """Reservation-time amenities/requests use their own flow — no line_item."""
        from src.app.modules.billing.service.folio import post_to_folio
        _seed_booking(db)
        _seed_open_folio(db, "BK-FOLIO-RECON")

        for ref_type in ("additional_charge", "additional_charge_revision", "no_show_penalty"):
            post_to_folio(
                "BK-FOLIO-RECON",
                posting_type="charge",
                category="Otros",
                concept=f"Cargo {ref_type}",
                amount=10.0,
                quantity=1,
                reference_id=f"ref-{ref_type}",
                reference_type=ref_type,
            )
        booking = db.booking_orders.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert booking["line_items"] == []
        assert booking["total_charges"] == 0.0


class TestRemoveLineItemReversesFolio:
    def test_remove_line_item_posts_charge_reversal_to_folio(self, db):
        _seed_booking(db)
        _seed_open_folio(db, "BK-FOLIO-RECON")
        _seed_product(db)

        added = add_booking_line_item(
            "BK-FOLIO-RECON",
            product_id="PROD-RECON",
            name="Minibar",
            unit_price=12.0,
            quantity=2,
            changed_by="tester",
        )
        assert added is not None
        item_id = added["item_id"]

        folio_before = db.guest_folios.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert folio_before["total_charges"] == 24.0
        assert any(
            p.get("reference_type") == "hotel_product" and p.get("reference_id") == item_id
            for p in folio_before["postings"]
        )

        removed = remove_booking_line_item("BK-FOLIO-RECON", item_id, changed_by="tester")
        assert removed is True

        folio_after = db.guest_folios.find_one({"booking_id": "BK-FOLIO-RECON"})
        reversal = next(
            (p for p in folio_after["postings"] if p["type"] == "charge_reversal"),
            None,
        )
        assert reversal is not None
        assert reversal["reference_id"] == item_id
        assert folio_after["total_charges"] == 0.0
        assert folio_after["total_due"] == 100.0

        booking = db.booking_orders.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert booking["line_items"] == []
        assert booking["total_charges"] == 0.0

    def test_remove_line_item_syncs_issued_invoice(self, db):
        _seed_booking(db)
        _seed_open_folio(db, "BK-FOLIO-RECON")
        _seed_product(db)
        db.reservation_invoices.insert_one({
            "booking_id": "BK-FOLIO-RECON",
            "prop_id": 1,
            "invoice_number": "INV-RECON-002",
            "status": "issued",
            "line_items": [],
            "room_subtotal": 100.0,
            "extras_total": 0.0,
            "subtotal": 100.0,
            "taxes": 0.0,
            "total": 100.0,
        })

        added = add_booking_line_item(
            "BK-FOLIO-RECON", product_id="PROD-RECON", name="Minibar",
            unit_price=12.0, quantity=1, changed_by="tester",
        )
        inv = db.reservation_invoices.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert inv["extras_total"] == 12.0

        remove_booking_line_item("BK-FOLIO-RECON", added["item_id"], changed_by="tester")

        inv = db.reservation_invoices.find_one({"booking_id": "BK-FOLIO-RECON"})
        assert inv["extras_total"] == 0.0
        assert inv["line_items"] == []
