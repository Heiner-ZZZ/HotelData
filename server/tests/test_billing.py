"""Tests for the billing module (spec 009).

Covers:
- GAP-042: Invoice/payment creation uses string booking_id (not ObjectId)
- Invoice lifecycle: create → list → get → cancel
- Payment lifecycle: create → list → get → refund
- Payment cascades invoice status to "paid"
- Refund cascades invoice status to "refunded"
"""
from __future__ import annotations

from bson import ObjectId
import pytest

from src.app.modules.billing.schemas import InvoiceCreate, PaymentCreate
from src.app.modules.billing.service.lifecycle import (
    cancel_invoice,
    create_invoice,
    create_payment,
    get_invoice,
    list_invoices,
    list_payments,
    get_payment,
    refund_payment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_booking(db, prop_id: int = 999) -> str:
    """Insert a minimal booking and return its string booking_id."""
    from src.app.modules.reservations.service._helpers import generate_prefixed_id, utc_now
    bid = generate_prefixed_id("BK")
    db.booking_orders.insert_one({
        "booking_id": bid,
        "prop_id": prop_id,
        "status": "pending",
        "guest_name": "Billing Test",
        "guest_email": "billing@test.com",
        "check_in_date": "2026-09-01",
        "check_out_date": "2026-09-04",
        "adults": 2,
        "children": 0,
        "rooms": 1,
        "created_at": utc_now(),
    })
    return bid


@pytest.fixture
def seeded_booking(db):
    """Fixture returning a string booking_id."""
    return _create_test_booking(db)


# ---------------------------------------------------------------------------
# GAP-042: Invoice creation uses string booking_id
# ---------------------------------------------------------------------------

class TestCreateInvoice:
    def test_create_invoice_success(self, db, seeded_booking):
        payload = InvoiceCreate(
            booking_id=seeded_booking,
            subtotal=450.00,
            taxes=45.00,
            notes="Test invoice",
        )
        result = create_invoice(payload)
        assert result is not None
        assert result["booking_id"] == seeded_booking
        assert result["subtotal"] == 450.00
        assert result["taxes"] == 45.00
        assert result["total"] == 495.00
        assert result["status"] == "issued"
        assert result["invoice_number"].startswith("INV-")

    def test_create_invoice_invalid_booking(self):
        payload = InvoiceCreate(
            booking_id="NONEXISTENT",
            subtotal=100.0,
            taxes=10.0,
        )
        result = create_invoice(payload)
        assert result is None

    def test_create_invoice_rejects_zero_without_line_items(self, db, seeded_booking):
        """Guard: never emit $0 invoices for bookings without a price (reservas sin tarifa)."""
        payload = InvoiceCreate(
            booking_id=seeded_booking,
            subtotal=0.0,
            taxes=0.0,
        )
        result = create_invoice(payload)
        assert result is None
        # Nothing persisted to either collection.
        assert db.reservation_invoices.count_documents({"booking_id": seeded_booking}) == 0
        assert db.fact_reservation_invoices.count_documents({"booking_id": seeded_booking}) == 0

    def test_invoice_stored_with_string_booking_id(self, db, seeded_booking):
        """Verify the DB stores string booking_id, not ObjectId (GAP-042)."""
        payload = InvoiceCreate(booking_id=seeded_booking, subtotal=200.0, taxes=20.0)
        result = create_invoice(payload)
        raw = db.reservation_invoices.find_one({"_id": ObjectId(result["id"])})
        assert isinstance(raw["booking_id"], str), (
            f"Expected string booking_id, got {type(raw['booking_id'])}"
        )
        assert raw["booking_id"] == seeded_booking


class TestListGetInvoice:
    def test_list_invoices(self, db, seeded_booking):
        create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=200.0, taxes=20.0))
        result = list_invoices()
        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_list_invoices_filter_by_booking_id(self, db, seeded_booking):
        """Filter by string booking_id works (GAP-042)."""
        create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        result = list_invoices(booking_id=seeded_booking)
        assert result["total"] == 1

    def test_list_invoices_filter_by_status(self, db, seeded_booking):
        create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        result = list_invoices(status="issued")
        assert result["total"] == 1
        result = list_invoices(status="paid")
        assert result["total"] == 0

    def test_get_invoice(self, db, seeded_booking):
        inv = create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        fetched = get_invoice(inv["id"])
        assert fetched is not None
        assert fetched["id"] == inv["id"]
        assert fetched["total"] == 110.0

    def test_get_invoice_not_found(self):
        assert get_invoice("000000000000000000000000") is None


class TestCancelInvoice:
    def test_cancel_invoice(self, db, seeded_booking):
        inv = create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        result = cancel_invoice(inv["id"])
        assert result is not None
        assert result["status"] == "cancelled"

    def test_cancel_already_cancelled_fails(self, db, seeded_booking):
        inv = create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        cancel_invoice(inv["id"])
        # Second cancel should return None (can't cancel non-issued)
        result = cancel_invoice(inv["id"])
        assert result is None


class TestCreatePayment:
    def test_create_payment_success(self, db, seeded_booking):
        payload = PaymentCreate(
            booking_id=seeded_booking,
            amount=495.00,
            method="credit_card",
        )
        result = create_payment(payload)
        assert result is not None
        assert result["booking_id"] == seeded_booking
        assert result["amount"] == 495.00
        assert result["status"] == "confirmed"
        assert result["reference"].startswith("PAY-")

    def test_create_payment_invalid_booking(self):
        payload = PaymentCreate(booking_id="NONEXISTENT", amount=100.0)
        result = create_payment(payload)
        assert result is None

    def test_payment_with_invoice_cascades_status(self, db, seeded_booking):
        """Paying an invoice should mark it as 'paid'."""
        inv = create_invoice(InvoiceCreate(
            booking_id=seeded_booking, subtotal=100.0, taxes=10.0,
        ))
        pay = create_payment(PaymentCreate(
            booking_id=seeded_booking,
            invoice_id=inv["id"],
            amount=110.0,
        ))
        assert pay is not None
        # Check invoice status updated
        updated_inv = get_invoice(inv["id"])
        assert updated_inv["status"] == "paid"

    def test_create_failed_payment_keeps_invoice_issued(self, db, seeded_booking):
        """A failed/rejected attempt must NOT mark the invoice as paid (F1.5)."""
        inv = create_invoice(InvoiceCreate(
            booking_id=seeded_booking, subtotal=100.0, taxes=10.0,
        ))
        pay = create_payment(PaymentCreate(
            booking_id=seeded_booking,
            invoice_id=inv["id"],
            amount=110.0,
            status="failed",
        ))
        assert pay is not None
        assert pay["status"] == "failed"
        updated_inv = get_invoice(inv["id"])
        assert updated_inv["status"] == "issued"

    def test_create_rejected_payment_status_roundtrip(self, db, seeded_booking):
        """Rejected attempts keep their status for the failed KPI aggregation."""
        pay = create_payment(PaymentCreate(
            booking_id=seeded_booking,
            amount=75.0,
            method="card",
            status="rejected",
        ))
        assert pay is not None
        assert pay["status"] == "rejected"
        fetched = get_payment(pay["id"])
        assert fetched["status"] == "rejected"


class TestListGetPayment:
    def test_list_payments(self, db, seeded_booking):
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=200.0))
        result = list_payments()
        assert result["total"] == 2

    def test_list_payments_filter_by_booking_id(self, db, seeded_booking):
        """Filter by string booking_id works (GAP-042)."""
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        other_bid = _create_test_booking(db, prop_id=888)
        create_payment(PaymentCreate(booking_id=other_bid, amount=50.0))
        result = list_payments(booking_id=seeded_booking)
        assert result["total"] == 1

    def test_get_payment(self, db, seeded_booking):
        pay = create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        fetched = get_payment(pay["id"])
        assert fetched is not None
        assert fetched["id"] == pay["id"]

    def test_get_payment_not_found(self):
        assert get_payment("000000000000000000000000") is None


class TestRefundPayment:
    def test_refund_payment(self, db, seeded_booking):
        pay = create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        result = refund_payment(pay["id"])
        assert result is not None
        assert result["status"] == "refunded"

    def test_refund_payment_with_invoice_cascades(self, db, seeded_booking):
        """Refunding a payment should also mark the invoice as 'refunded'."""
        inv = create_invoice(InvoiceCreate(
            booking_id=seeded_booking, subtotal=100.0, taxes=10.0,
        ))
        pay = create_payment(PaymentCreate(
            booking_id=seeded_booking,
            invoice_id=inv["id"],
            amount=110.0,
        ))
        refund_payment(pay["id"])
        updated_inv = get_invoice(inv["id"])
        assert updated_inv["status"] == "refunded"

    def test_double_refund_fails(self, db, seeded_booking):
        pay = create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        refund_payment(pay["id"])
        result = refund_payment(pay["id"])
        assert result is None
