"""Staff money operations require an active cash shift.

Every operation that moves money at the front desk — payments of ANY method,
refunds, invoice payment, folio settlement and folio postings — now requires
an open shift for the property, and the resulting document carries the shift
plus the responsible employee in Mongo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from tests.conftest import login

_UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _open_shift(db, prop_id: int, *, employee: str = "Teller Demo") -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    result = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": employee,
            "opened_by": "admin_test",
            "start_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    return str(result.inserted_id)


def _seed_booking(db, prop_id: int = 930) -> str:
    bid = f"BK-GATE-{prop_id}"
    db.booking_orders.insert_one(
        {
            "booking_id": bid,
            "prop_id": prop_id,
            "status": "confirmed",
            "guest_name": "Gate Test Guest",
            "guest_email": "gate@test.local",
            "check_in_date": "2026-09-01",
            "check_out_date": "2026-09-04",
            "total_price": 200.0,
            "total_nights": 3,
            "created_at": datetime.now(_UTC),
        }
    )
    return bid


def _seed_open_folio(db, booking_id: str, due: float = 100.0) -> None:
    db.guest_folios.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 930,
            "folio_number": f"FL-GATE-{booking_id}",
            "status": "open",
            "total_room": due,
            "total_charges": due,
            "total_discounts": 0.0,
            "total_payments": 0.0,
            "total_due": due,
            "postings": [],
            "posting_count": 0,
        }
    )


async def _login(client, admin_user) -> None:
    assert await login(client, admin_user["username"], admin_user["password"]) == 200


# ── Payments (ALL methods) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_card_payment_requires_active_shift(client, admin_user, db):
    booking_id = _seed_booking(db)

    await _login(client, admin_user)
    response = await client.post(
        "/api/billing/payments?prop_id=930",
        json={"booking_id": booking_id, "amount": 50.0, "method": "credit_card"},
    )

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_card_payment_with_shift_stamps_shift_and_employee(client, admin_user, db):
    booking_id = _seed_booking(db)
    shift_id = _open_shift(db, 930, employee="Teller Demo")

    await _login(client, admin_user)
    response = await client.post(
        "/api/billing/payments?prop_id=930",
        json={"booking_id": booking_id, "amount": 50.0, "method": "credit_card"},
    )

    assert response.status_code == 201
    raw = db.reservation_payments.find_one({"booking_id": booking_id})
    assert raw is not None
    assert str(raw["shift_id"]) == shift_id
    assert raw["shift_employee"] == "Teller Demo"
    assert raw["shift_opened_by"] == "admin_test"


# ── Refunds ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_refund_requires_active_shift(client, admin_user, db):
    from src.app.modules.billing.schemas import PaymentCreate
    from src.app.modules.billing.service.lifecycle.payments import create_payment

    booking_id = _seed_booking(db)
    pay = create_payment(PaymentCreate(booking_id=booking_id, amount=50.0, method="cash"))

    await _login(client, admin_user)
    response = await client.post(f"/api/billing/payments/{pay['id']}/refund?prop_id=930", json={})

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_refund_with_shift_stamps_refund_shift(client, admin_user, db):
    from src.app.modules.billing.schemas import PaymentCreate
    from src.app.modules.billing.service.lifecycle.payments import create_payment

    booking_id = _seed_booking(db)
    pay = create_payment(PaymentCreate(booking_id=booking_id, amount=50.0, method="cash"))
    shift_id = _open_shift(db, 930)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/payments/{pay['id']}/refund?prop_id=930",
        json={"reason": "Cambio de planes"},
    )

    assert response.status_code == 200
    raw = db.reservation_payments.find_one({"booking_id": booking_id})
    assert raw["status"] == "refunded"
    assert str(raw["refund_shift_id"]) == shift_id
    assert raw["refund_shift_employee"] == "Teller Demo"


# ── Invoice payment (staff "Registrar Pago") ─────────────────────────────


@pytest.mark.asyncio
async def test_http_pay_invoice_requires_active_shift(client, admin_user, db):
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))

    await _login(client, admin_user)
    response = await client.post(f"/api/billing/invoices/{inv['id']}/pay?prop_id=930")

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_pay_invoice_with_shift_stamps_payment(client, admin_user, db):
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))
    shift_id = _open_shift(db, 930)

    await _login(client, admin_user)
    response = await client.post(f"/api/billing/invoices/{inv['id']}/pay?prop_id=930")

    assert response.status_code == 200
    raw = db.reservation_payments.find_one({"invoice_id": ObjectId(inv["id"])})
    assert raw is not None
    assert str(raw["shift_id"]) == shift_id
    assert raw["shift_employee"] == "Teller Demo"


# ── Folio settlement (all methods) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_settle_card_requires_active_shift(client, admin_user, db):
    booking_id = _seed_booking(db)
    _seed_open_folio(db, booking_id)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/folios/{booking_id}/settle?prop_id=930",
        json={"settlement_type": "payment", "amount": 100.0, "method": "card", "idempotency_key": "gate-settle-1"},
    )

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_settle_card_with_shift_succeeds(client, admin_user, db):
    booking_id = _seed_booking(db)
    _seed_open_folio(db, booking_id)
    _open_shift(db, 930)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/folios/{booking_id}/settle?prop_id=930",
        json={"settlement_type": "payment", "amount": 100.0, "method": "card", "idempotency_key": "gate-settle-2"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "settled"


# ── Folio postings (Agregar cargo) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_folio_post_requires_active_shift(client, admin_user, db):
    booking_id = _seed_booking(db)
    _seed_open_folio(db, booking_id)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/folios/{booking_id}/post?prop_id=930",
        json={"posting_type": "charge", "category": "Minibar", "concept": "Coca Cola", "amount": 5.0},
    )

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_folio_post_with_shift_stamps_posting(client, admin_user, db):
    booking_id = _seed_booking(db)
    _seed_open_folio(db, booking_id)
    shift_id = _open_shift(db, 930)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/folios/{booking_id}/post?prop_id=930",
        json={"posting_type": "charge", "category": "Minibar", "concept": "Coca Cola", "amount": 5.0},
    )

    assert response.status_code == 200
    folio = db.guest_folios.find_one({"booking_id": booking_id})
    posting = folio["postings"][0]
    assert str(posting["shift_id"]) == shift_id
    assert posting["shift_employee"] == "Teller Demo"


# ── Manual invoice issuance (POST /invoices) ─────────────────────────────


@pytest.mark.asyncio
async def test_http_manual_invoice_issuance_requires_active_shift(client, admin_user, db):
    booking_id = _seed_booking(db, prop_id=931)

    await _login(client, admin_user)
    response = await client.post(
        "/api/billing/invoices?prop_id=931",
        json={"booking_id": booking_id, "subtotal": 100.0, "taxes": 10.0},
    )

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]
    assert db.reservation_invoices.count_documents({"booking_id": booking_id}) == 0


@pytest.mark.asyncio
async def test_http_manual_invoice_issuance_with_shift_succeeds(client, admin_user, db):
    booking_id = _seed_booking(db, prop_id=931)
    _open_shift(db, 931)

    await _login(client, admin_user)
    response = await client.post(
        "/api/billing/invoices?prop_id=931",
        json={"booking_id": booking_id, "subtotal": 100.0, "taxes": 10.0},
    )

    assert response.status_code == 201
    assert db.reservation_invoices.count_documents({"booking_id": booking_id}) == 1


@pytest.mark.asyncio
async def test_http_manual_invoice_issuance_stamps_shift_on_doc(client, admin_user, db):
    """Emission stamps the issuing shift + employee on the invoice doc and its
    facts mirror (parity with payments/folio postings)."""
    booking_id = _seed_booking(db, prop_id=935)
    shift_id = _open_shift(db, 935, employee="Teller Demo")

    await _login(client, admin_user)
    response = await client.post(
        "/api/billing/invoices?prop_id=935",
        json={"booking_id": booking_id, "subtotal": 100.0, "taxes": 10.0},
    )

    assert response.status_code == 201
    raw = db.reservation_invoices.find_one({"booking_id": booking_id})
    assert raw is not None
    assert str(raw["shift_id"]) == shift_id
    assert raw["shift_employee"] == "Teller Demo"
    assert raw["shift_opened_by"] == "admin_test"
    assert raw["shift_type"] == "morning"
    # El espejo de hechos lleva la misma estampa.
    mirror = db.fact_reservation_invoices.find_one({"booking_id": booking_id})
    assert mirror is not None
    assert str(mirror["shift_id"]) == shift_id
    assert mirror["shift_employee"] == "Teller Demo"
    # La respuesta del wire expone la atribución (paridad con pagos).
    body = response.json()
    assert body["shift_id"] == shift_id
    assert body["shift_employee"] == "Teller Demo"


# ── Invoice cancellation (POST /invoices/{id}/cancel) ────────────────────


@pytest.mark.asyncio
async def test_http_cancel_invoice_requires_active_shift(client, admin_user, db):
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db, prop_id=932)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/invoices/{inv['id']}/cancel?prop_id=932",
        json={"reason": "Factura duplicada"},
    )

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]
    assert db.reservation_invoices.find_one({"_id": ObjectId(inv["id"])})["status"] == "issued"


@pytest.mark.asyncio
async def test_http_cancel_invoice_with_shift_succeeds(client, admin_user, db):
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db, prop_id=932)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))
    _open_shift(db, 932)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/invoices/{inv['id']}/cancel?prop_id=932",
        json={"reason": "Factura duplicada"},
    )

    assert response.status_code == 200
    assert db.reservation_invoices.find_one({"_id": ObjectId(inv["id"])})["status"] == "cancelled"


@pytest.mark.asyncio
async def test_http_cancel_invoice_stamps_cancel_shift_on_doc(client, admin_user, db):
    """Cancellation stamps the cancelling shift (separate from the issuing one)
    on the invoice doc and its facts mirror, keeping both attributions."""
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db, prop_id=936)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))
    shift_id = _open_shift(db, 936, employee="Teller Demo")

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/invoices/{inv['id']}/cancel?prop_id=936",
        json={"reason": "Factura duplicada"},
    )

    assert response.status_code == 200
    raw = db.reservation_invoices.find_one({"_id": ObjectId(inv["id"])})
    assert raw["status"] == "cancelled"
    assert str(raw["cancelled_shift_id"]) == shift_id
    assert raw["cancelled_shift_employee"] == "Teller Demo"
    assert raw["cancelled_shift_opened_by"] == "admin_test"
    assert raw["cancelled_shift_type"] == "morning"
    mirror = db.fact_reservation_invoices.find_one({"_id": ObjectId(inv["id"])})
    assert str(mirror["cancelled_shift_id"]) == shift_id
    assert mirror["cancelled_shift_employee"] == "Teller Demo"


# ── Credit note emission (POST /invoices/{id}/credit-note) ──────────────


def _seed_cancelled_invoice(db, prop_id: int = 933, total: float = 116.0) -> str:
    """A cancelled invoice eligible for a credit note (reversal + total > 0)."""
    booking_id = _seed_booking(db, prop_id=prop_id)
    invoice_id = db.reservation_invoices.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            "invoice_number": f"INV-GATE-CN-{prop_id}",
            "room_subtotal": total - 16.0,
            "extras_total": 0.0,
            "subtotal": total - 16.0,
            "taxes": 16.0,
            "total": total,
            "status": "cancelled",
        }
    ).inserted_id
    return str(invoice_id)


@pytest.mark.asyncio
async def test_http_credit_note_requires_active_shift(client, admin_user, db):
    invoice_id = _seed_cancelled_invoice(db)

    await _login(client, admin_user)
    response = await client.post(f"/api/billing/invoices/{invoice_id}/credit-note?prop_id=933")

    # La factura anulada es elegible para nota de crédito; el único 409 que
    # puede responder es el del gate de turno → el gate corre ANTES.
    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_credit_note_with_shift_succeeds(client, admin_user, db):
    invoice_id = _seed_cancelled_invoice(db)
    _open_shift(db, 933)

    await _login(client, admin_user)
    response = await client.post(f"/api/billing/invoices/{invoice_id}/credit-note?prop_id=933")

    assert response.status_code == 200
    assert db.refund_documents.find_one(
        {"invoice_id": ObjectId(invoice_id), "document_type": "credit_note"}
    ) is not None


@pytest.mark.asyncio
async def test_http_credit_note_stamps_shift_and_employee_on_doc(client, admin_user, db):
    """Credit-note emission stamps the issuing shift + employee on the refund
    document and its facts mirror (parity with invoices/payments/folios)."""
    invoice_id = _seed_cancelled_invoice(db)
    shift_id = _open_shift(db, 933, employee="Teller Demo")

    await _login(client, admin_user)
    response = await client.post(f"/api/billing/invoices/{invoice_id}/credit-note?prop_id=933")

    assert response.status_code == 200
    document = db.refund_documents.find_one(
        {"invoice_id": ObjectId(invoice_id), "document_type": "credit_note"}
    )
    assert document is not None
    assert str(document["shift_id"]) == shift_id
    assert document["shift_employee"] == "Teller Demo"
    assert document["shift_opened_by"] == "admin_test"
    assert document["shift_type"] == "morning"
    # El espejo de hechos lleva la misma estampa.
    mirror = db.fact_refund_documents.find_one({"_id": document["_id"]})
    assert mirror is not None
    assert str(mirror["shift_id"]) == shift_id
    assert mirror["shift_employee"] == "Teller Demo"
    assert mirror["shift_opened_by"] == "admin_test"


# ── Additional charges on invoice detail (POST /invoices/{id}/items) ─────


@pytest.mark.asyncio
async def test_http_add_line_item_requires_active_shift(client, admin_user, db):
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db, prop_id=934)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/invoices/{inv['id']}/items?prop_id=934",
        json={"name": "Parking", "quantity": 1, "unit_price": 20.0, "category": "parking"},
    )

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]
    line_items = db.reservation_invoices.find_one({"_id": ObjectId(inv["id"])}).get("line_items", [])
    assert len(line_items) == 0


@pytest.mark.asyncio
async def test_http_add_line_item_with_shift_succeeds(client, admin_user, db):
    from src.app.modules.billing.schemas import InvoiceCreate
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice

    booking_id = _seed_booking(db, prop_id=934)
    inv = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=100.0, taxes=10.0))
    _open_shift(db, 934)

    await _login(client, admin_user)
    response = await client.post(
        f"/api/billing/invoices/{inv['id']}/items?prop_id=934",
        json={"name": "Parking", "quantity": 1, "unit_price": 20.0, "category": "parking"},
    )

    assert response.status_code == 201
    line_items = db.reservation_invoices.find_one({"_id": ObjectId(inv["id"])}).get("line_items", [])
    assert any(li.get("name") == "Parking" for li in line_items)
