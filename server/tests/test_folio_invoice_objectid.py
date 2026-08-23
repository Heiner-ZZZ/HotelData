"""Folio FK migration: guest_folios.invoice_id must be a BSON ObjectId.

The 2026-08 audit found ``guest_folios.invoice_id`` stored as a hex STRING
(``reservations/_checkout.py`` passed ``str(inv_doc["_id"])``) while the same
reference in ``reservation_payments.invoice_id`` is stored as ObjectId — the
same type-drift class that made ``booking_orders.user_id`` hide a client's
bookings. These tests pin the canonical behavior end-to-end:

1. ``close_folio`` (service) stores ``invoice_id`` as ObjectId even when the
   caller passes the hex string (the current checkout + API callers).
2. ``POST /api/billing/folios/{booking_id}/close`` persists ObjectId.
3. The wire shape still serializes ``invoice_id`` as a hex string
   (frontend contract unchanged — ``to_json_safe`` at the API boundary).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId


def _seed_booking(db, *, booking_id="BK-TESTFOLIO-0001", **extra):
    """Insert a minimal booking; returns its ``booking_id``."""
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Test Folio Guest",
        "total_price": 120.0,
        "total_nights": 2,
        "status": "confirmed",
        "stay_status": "checked_in",
        "created_at": datetime.now(timezone.utc),
    }
    doc.update(extra)
    db.booking_orders.insert_one(doc)
    return booking_id


def _seed_folio(db, booking_id, *, status="open", invoice_id=None):
    """Insert an open folio for the booking; returns its ``folio_number``."""
    folio_number = f"FL-TEST-{ObjectId()}"
    db.guest_folios.insert_one(
        {
            "folio_number": folio_number,
            "booking_id": booking_id,
            "prop_id": 1,
            "status": status,
            "total_room": 120.0,
            "total_due": 120.0,
            "postings": [],
            "posting_count": 0,
            "created_at": datetime.now(timezone.utc),
            "closed_at": None,
            "closed_by": None,
            "invoice_id": invoice_id,
        }
    )
    return folio_number


def _seed_invoice(db, booking_id):
    """Insert an invoice for the booking; returns its ``_id`` (ObjectId)."""
    return db.reservation_invoices.insert_one(
        {
            "booking_id": booking_id,
            "invoice_number": f"INV-TEST-{ObjectId()}",
            "status": "issued",
            "total": 120.0,
            "issued_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id


async def _login_admin(client, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    assert resp.status_code == 200, resp.text


class TestCloseFolioInvoiceIdObjectIdFk:
    """guest_folios.invoice_id must be a BSON ObjectId FK to reservation_invoices._id."""

    def test_close_folio_normalizes_hex_string_to_object_id(self, db):
        """close_folio with a hex invoice_id must persist it as ObjectId."""
        from src.app.modules.billing.service import close_folio

        booking_id = _seed_booking(db)
        inv_id = _seed_invoice(db, booking_id)
        _seed_folio(db, booking_id, status="open")

        result = close_folio(
            booking_id,
            invoice_id=str(inv_id),
            closed_by="tester",
            close_reason="approved_external_settlement: test",
        )

        assert result is not None
        assert result["status"] == "closed"
        doc = db.guest_folios.find_one({"booking_id": booking_id})
        assert doc is not None
        stored = doc.get("invoice_id")
        assert isinstance(stored, ObjectId), (
            f"close_folio must store invoice_id as ObjectId, got {type(stored).__name__}"
        )
        assert stored == inv_id, "the stored invoice_id must equal the invoice's _id"
        assert db.reservation_invoices.count_documents({"_id": stored}) == 1, (
            "the stored invoice_id must resolve to a real reservation_invoices._id"
        )

    def test_get_folio_uses_booking_invoice_when_folio_fk_is_missing(self, db):
        """The printed folio still exposes coverage for historical missing FKs."""
        from src.app.modules.billing.service import get_folio

        booking_id = _seed_booking(db, booking_id="BK-TESTFOLIO-COVERAGE")
        invoice_id = _seed_invoice(db, booking_id)
        db.reservation_invoices.update_one(
            {"_id": invoice_id},
            {"$set": {"subtotal": 100.0}},
        )
        _seed_folio(db, booking_id, status="open")

        result = get_folio(booking_id)

        assert result is not None
        assert result["has_invoice"] is True
        assert result["invoice_id"] == invoice_id
        assert result["invoice_number"].startswith("INV-TEST-")
        assert result["invoice_covered_subtotal"] == 100.0

    @pytest.mark.asyncio
    async def test_close_folio_api_stores_object_id(self, client, db, admin_user):
        """POST /api/billing/folios/{booking_id}/close must persist ObjectId."""
        await _login_admin(client, admin_user)
        booking_id = _seed_booking(db, booking_id="BK-TESTFOLIO-API")
        inv_id = _seed_invoice(db, booking_id)
        _seed_folio(db, booking_id, status="open")

        resp = await client.post(
            f"/api/billing/folios/{booking_id}/close?prop_id=1",
            json={
                "invoice_id": str(inv_id),
                "close_reason": "approved_external_settlement: test",
            },  # hex string from the client
        )
        assert resp.status_code == 200, resp.text

        doc = db.guest_folios.find_one({"booking_id": booking_id})
        assert doc is not None
        stored = doc.get("invoice_id")
        assert isinstance(stored, ObjectId), (
            f"close-folio API must store invoice_id as ObjectId, got {type(stored).__name__}"
        )
        assert stored == inv_id

        # Wire shape: the response serializes invoice_id as a hex string.
        body = resp.json()
        assert body["status"] == "closed"
        assert body.get("invoice_id") == str(inv_id), (
            f"API wire shape must expose invoice_id as hex string, got {body.get('invoice_id')!r}"
        )
