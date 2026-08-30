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


def _seed_shift(db, *, employee: str = "Teller Uno", opened_by: str = "cajero1") -> str:
    """Insert a reception shift and return its string id (for stamping)."""
    from datetime import datetime, timezone

    res = db.reception_shifts.insert_one(
        {
            "prop_id": 999,
            "status": "closed",
            "shift_type": "morning",
            "employee": employee,
            "opened_by": opened_by,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    return str(res.inserted_id)


def _seed_open_folio_for_payment(db, booking_id: str, due: float) -> None:
    """Insert an open guest folio with a positive balance for payment tests."""
    from datetime import datetime, timezone

    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 999,
        "folio_number": f"FL-PAY-{booking_id}",
        "status": "open",
        "total_room": due,
        "total_charges": due,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": due,
        "postings": [],
        "posting_count": 0,
        "created_at": datetime.now(timezone.utc),
    })


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

    def test_create_invoice_rejects_zero_with_zero_value_line_items(self, db, seeded_booking):
        """Guard ampliado: una reserva con line_items pero SIN valor real no
        puede producir una factura en $0.

        La guarda anterior solo rechazaba el caso de ``line_items`` vacíos
        (``not line_items``), así que una reserva con line_items cuyos totales
        suman $0 se colaba y persistía una factura en $0 — contaminando los
        KPIs tácticos (F1.4/F1.5) exactamente igual que el caso sin conceptos.
        """
        db.booking_orders.update_one(
            {"booking_id": seeded_booking},
            {"$set": {"line_items": [{"item_id": "x1", "name": "Extra $0", "total": 0.0}]}},
        )
        payload = InvoiceCreate(booking_id=seeded_booking, subtotal=0.0, taxes=0.0)
        result = create_invoice(payload)
        assert result is None
        # Nada persistido en ninguna de las dos colecciones.
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

    def test_cancel_invoice_stores_reason_and_actor(self, db, seeded_booking):
        """Cancel reason/note + actor must persist on the invoice doc (Mongo,
        both mirrors) so the cancellation has an observable history."""
        inv = create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        result = cancel_invoice(
            inv["id"],
            cancel_reason="Cliente canceló por cambio de planes",
            cancelled_by="teller-01",
        )
        assert result is not None
        assert result["status"] == "cancelled"
        assert result["cancel_reason"] == "Cliente canceló por cambio de planes"
        assert result["cancelled_by"] == "teller-01"
        # Persistido en Mongo (colección principal y espejo de hechos).
        raw = db.reservation_invoices.find_one({"_id": ObjectId(inv["id"])})
        assert raw["cancel_reason"] == "Cliente canceló por cambio de planes"
        assert raw["cancelled_by"] == "teller-01"
        raw_fact = db.fact_reservation_invoices.find_one({"_id": ObjectId(inv["id"])})
        assert raw_fact["cancel_reason"] == "Cliente canceló por cambio de planes"
        assert raw_fact["cancelled_by"] == "teller-01"

    def test_cancel_invoice_reason_optional(self, db, seeded_booking):
        """Without a reason, the cancellation still works and leaves no
        ``cancel_reason``/``cancelled_by`` on the doc (backwards compatible)."""
        inv = create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0))
        result = cancel_invoice(inv["id"])
        assert result is not None
        assert result["status"] == "cancelled"
        assert "cancel_reason" not in result
        assert "cancelled_by" not in result


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

    def test_full_payment_marks_folio_settled_when_balance_reaches_zero(self, db, seeded_booking):
        """Registrar Pago: pagar el saldo completo del folio lo cierra como settled."""
        _seed_open_folio_for_payment(db, seeded_booking, 120.0)

        result = create_payment(PaymentCreate(
            booking_id=seeded_booking,
            amount=120.0,
            method="card",
        ))

        assert result is not None
        assert result["status"] == "confirmed"
        folio = db.guest_folios.find_one({"booking_id": seeded_booking})
        assert folio["status"] == "settled"
        assert folio["total_due"] == 0.0
        assert folio["settlement_type"] == "payment"
        assert folio["settled_by"] == "system"
        payment = db.reservation_payments.find_one({
            "booking_id": seeded_booking,
            "status": "confirmed",
        })
        assert payment is not None
        assert folio["settled_at"] == payment["paid_at"]
        # El pago quedó posteado al folio como evidencia del cierre.
        assert any(
            p.get("type") == "payment" and p.get("reference_type") == "payment"
            for p in folio["postings"]
        )

    def test_partial_payment_keeps_folio_open_with_remaining_balance(self, db, seeded_booking):
        """Un pago parcial NO debe cerrar el folio: sigue open con saldo restante."""
        _seed_open_folio_for_payment(db, seeded_booking, 120.0)

        result = create_payment(PaymentCreate(
            booking_id=seeded_booking,
            amount=50.0,
            method="card",
        ))

        assert result is not None
        assert result["status"] == "confirmed"
        folio = db.guest_folios.find_one({"booking_id": seeded_booking})
        assert folio["status"] == "open"
        assert round(folio["total_due"], 2) == 70.0
        assert "settled_at" not in folio

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

    def test_create_payment_malformed_invoice_id_is_rejected(self, db, seeded_booking):
        """A malformed invoice link must be rejected, not silently orphaned."""
        with pytest.raises(ValueError, match="Factura"):
            create_payment(PaymentCreate(
                booking_id=seeded_booking,
                invoice_id="factura-1",  # not a valid ObjectId
                amount=25.0,
            ))
        assert db.reservation_payments.count_documents({"booking_id": seeded_booking}) == 0


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

    def test_list_payments_exposes_legacy_pending_count_per_prop(self, db, seeded_booking):
        """The list exposes how many unattributed (legacy) payments the hotel
        still has pending linking, scoped to that hotel only."""
        prop_a = db.booking_orders.find_one({"booking_id": seeded_booking})["prop_id"]
        other_bid = _create_test_booking(db, prop_id=888)
        # prop_a: 2 legacy sin turno + 1 con turno estampado; otro hotel: 1 legacy.
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=50.0))
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=30.0), shift_id="6a78d993c9e391c6684414f3")
        create_payment(PaymentCreate(booking_id=other_bid, amount=20.0))

        result = list_payments(prop_id=prop_a)

        assert result["legacy_pending_count"] == 2

    def test_list_payments_legacy_pending_count_matches_sin_turno_filter(self, db, seeded_booking):
        """The badge count equals what the "Sin turno" filter would show for
        the hotel, so the chip is honest about what it filters."""
        prop_a = db.booking_orders.find_one({"booking_id": seeded_booking})["prop_id"]
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=50.0))
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=30.0), shift_id="6a78d993c9e391c6684414f3")

        result = list_payments(prop_id=prop_a, sin_turno=True)

        assert result["total"] == 2
        assert result["legacy_pending_count"] == 2

    def test_list_payments_filters_by_shift_and_employee(self, db, seeded_booking):
        """Filtros de auditoría: por turno exacto (shift_id) y por cajero
        (coincide con shift_employee o shift_opened_by, sin distinguir mayúsculas)."""
        shift_a = _seed_shift(db, employee="Teller Uno", opened_by="cajero1")
        shift_b = _seed_shift(db, employee="Teller Dos", opened_by="cajero2")
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0), shift_id=shift_a)
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=50.0), shift_id=shift_b)
        create_payment(PaymentCreate(booking_id=seeded_booking, amount=25.0))  # legacy sin turno

        by_shift = list_payments(shift_id=shift_a)
        assert by_shift["total"] == 1
        assert by_shift["items"][0]["amount"] == 100.0

        by_employee = list_payments(employee="teller UNO")
        assert by_employee["total"] == 1
        assert by_employee["items"][0]["amount"] == 100.0

        by_opener = list_payments(employee="cajero2")
        assert by_opener["total"] == 1
        assert by_opener["items"][0]["amount"] == 50.0

    def test_list_invoices_filters_by_shift_and_employee(self, db, seeded_booking):
        """El listado de facturas filtra por turno que emitió y por cajero
        (shift_employee / shift_opened_by de la estampa de emisión)."""
        shift_a = _seed_shift(db, employee="Teller Uno", opened_by="cajero1")
        shift_b = _seed_shift(db, employee="Teller Dos", opened_by="cajero2")
        create_invoice(
            InvoiceCreate(booking_id=seeded_booking, subtotal=100.0, taxes=10.0),
            shift_id=shift_a,
            shift_attribution={
                "shift_employee": "Teller Uno",
                "shift_opened_by": "cajero1",
                "shift_type": "morning",
            },
        )
        create_invoice(
            InvoiceCreate(booking_id=seeded_booking, subtotal=50.0, taxes=0.0),
            shift_id=shift_b,
            shift_attribution={
                "shift_employee": "Teller Dos",
                "shift_opened_by": "cajero2",
                "shift_type": "morning",
            },
        )
        create_invoice(InvoiceCreate(booking_id=seeded_booking, subtotal=30.0, taxes=0.0))  # sin turno

        by_shift = list_invoices(shift_id=shift_a)
        assert by_shift["total"] == 1
        assert by_shift["items"][0]["total"] == 110.0

        by_employee = list_invoices(employee="teller UNO")
        assert by_employee["total"] == 1
        assert by_employee["items"][0]["total"] == 110.0

        by_opener = list_invoices(employee="cajero2")
        assert by_opener["total"] == 1

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

    def test_refund_payment_stores_reason_and_actor(self, db, seeded_booking):
        """Refund reason/note + actor must persist on the payment doc (Mongo,
        both mirrors) so the refund has an observable history."""
        pay = create_payment(PaymentCreate(booking_id=seeded_booking, amount=100.0))
        result = refund_payment(
            pay["id"],
            refund_reason="Cliente insatisfecho con el servicio",
            changed_by="teller-01",
        )
        assert result is not None
        assert result["status"] == "refunded"
        assert result["refund_reason"] == "Cliente insatisfecho con el servicio"
        assert result["refunded_by"] == "teller-01"
        assert result["refunded_at"] is not None
        # Persistido en Mongo (colección principal y espejo de hechos).
        raw = db.reservation_payments.find_one({"_id": ObjectId(pay["id"])})
        assert raw["refund_reason"] == "Cliente insatisfecho con el servicio"
        assert raw["refunded_by"] == "teller-01"
        raw_fact = db.fact_reservation_payments.find_one({"_id": ObjectId(pay["id"])})
        assert raw_fact["refund_reason"] == "Cliente insatisfecho con el servicio"
        assert raw_fact["refunded_by"] == "teller-01"

    def test_refund_payment_reason_optional(self, db, seeded_booking):
        """Without a reason, the refund still works and leaves no
        ``refund_reason``/``refunded_by`` on the doc (backwards compatible)."""
        pay = create_payment(PaymentCreate(booking_id=seeded_booking, amount=50.0))
        result = refund_payment(pay["id"])
        assert result is not None
        assert result["status"] == "refunded"
        assert "refund_reason" not in result
        assert "refunded_by" not in result




# ---------------------------------------------------------------------------
# Client-facing "Mis facturas" (billing/routes.py)
# ---------------------------------------------------------------------------

class TestMyInvoicesClientFacing:
    """Client-facing "Mis facturas" endpoints must resolve bookings by the
    BUSINESS ``booking_id`` (``BK-…`` = fecha + ticket), NOT by the Mongo
    ``_id``. ``reservation_invoices.booking_id`` stores the string business
    key (GAP-042 pinned the write side), so joining with ``_id`` (ObjectId)
    silently returns nothing: an empty "Mis facturas" list and a permanent
    403 on pay — even though the invoice exists in the DB.
    """

    @pytest.fixture
    def cliente_role(self, db):
        """Seed the global ``cliente`` role with the account.* permissions
        the my-invoices routes gate on (``require_permission`` reads
        ``roles.permissions``)."""
        db.roles.insert_one({
            "role_name": "cliente",
            "display_name": "Cliente",
            "permissions": ["account.read", "account.update", "reservations.read"],
            "is_system": True,
        })

    def _owned_booking(self, db, user_id: str) -> str:
        """Insert a booking owned by ``user_id`` (ObjectId FK) and return
        its business ``booking_id`` (BK-…)."""
        from src.app.modules.reservations.service._helpers import generate_prefixed_id, utc_now
        # dim_hotels row so create_invoice's resolve_hotel_id doesn't warn.
        if not db.dim_hotels.find_one({"prop_id": 999}, {"_id": 1}):
            db.dim_hotels.insert_one({"prop_id": 999, "hotel_name": "Test Hotel", "display_name": "Test Hotel"})
        bid = generate_prefixed_id("BK")
        db.booking_orders.insert_one({
            "booking_id": bid,
            "user_id": ObjectId(user_id),
            "prop_id": 999,
            "status": "confirmed",
            "guest_name": "Cliente Facturas",
            "guest_email": "cliente_test@example.com",
            "check_in_date": "2026-09-01",
            "check_out_date": "2026-09-04",
            "adults": 2,
            "children": 0,
            "rooms": 1,
            "total_price": 450.0,
            "created_at": utc_now(),
        })
        return bid

    @pytest.mark.asyncio
    async def test_my_invoices_finds_invoice_by_business_booking_id(
        self, client, db, cliente_user, cliente_role
    ):
        """GET /api/billing/my-invoices must return the invoice of a booking
        owned by the client, joined by business ``booking_id``."""
        bid = self._owned_booking(db, cliente_user["user_id"])
        create_invoice(InvoiceCreate(booking_id=bid, subtotal=100.0, taxes=10.0))

        lr = await client.post(
            "/api/auth/login",
            json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
        )
        assert lr.status_code == 200, lr.text

        resp = await client.get("/api/billing/my-invoices")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 1, (
            f"El cliente debe ver su factura via booking_id de negocio, vio: {body}"
        )
        assert body["items"][0]["booking_id"] == bid

    @pytest.mark.asyncio
    async def test_my_invoice_pay_accepts_own_invoice(
        self, client, db, cliente_user, cliente_role
    ):
        """POST /api/billing/my-invoices/{id}/pay must accept a client paying
        their OWN invoice (ownership check by business booking_id)."""
        bid = self._owned_booking(db, cliente_user["user_id"])
        inv = create_invoice(InvoiceCreate(booking_id=bid, subtotal=100.0, taxes=10.0))

        lr = await client.post(
            "/api/auth/login",
            json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
        )
        assert lr.status_code == 200, lr.text

        resp = await client.post(f"/api/billing/my-invoices/{inv['id']}/pay")
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_my_invoice_pay_partial_amount_marks_partially_paid(
        self, client, db, cliente_user, cliente_role
    ):
        """Pago parcial con amount → confirmado y la factura queda partially_paid
        con el monto pagado reflejado (sin require_prop_permission: el gate es
        account.update)."""
        bid = self._owned_booking(db, cliente_user["user_id"])
        inv = create_invoice(InvoiceCreate(booking_id=bid, subtotal=100.0, taxes=10.0))

        lr = await client.post(
            "/api/auth/login",
            json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
        )
        assert lr.status_code == 200, lr.text

        resp = await client.post(f"/api/billing/my-invoices/{inv['id']}/pay", json={"amount": 50})
        assert resp.status_code == 200, resp.text
        updated = get_invoice(inv["id"])
        assert updated["status"] == "partially_paid"
        assert round(float(updated["total_paid_amount"]), 2) == 50.0

    @pytest.mark.asyncio
    async def test_my_invoice_pay_rejects_amount_over_remaining(
        self, client, db, cliente_user, cliente_role
    ):
        """Un amount > saldo pendiente se rechaza con 400 (sin crear pago)."""
        bid = self._owned_booking(db, cliente_user["user_id"])
        inv = create_invoice(InvoiceCreate(booking_id=bid, subtotal=100.0, taxes=10.0))

        lr = await client.post(
            "/api/auth/login",
            json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
        )
        assert lr.status_code == 200, lr.text

        resp = await client.post(f"/api/billing/my-invoices/{inv['id']}/pay", json={"amount": 120})
        assert resp.status_code == 400, resp.text
        assert "excede el saldo pendiente" in resp.json()["detail"]
        assert get_invoice(inv["id"])["status"] == "issued"
