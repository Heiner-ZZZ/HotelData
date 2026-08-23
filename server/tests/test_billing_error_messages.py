"""Error messages of the billing/payments flow must tell the user what to do.

Extiende el criterio de mensajes con acción a los errores del flujo de
facturación y pagos (emitir/cancelar factura, registrar pago, split invoice,
folios y vinculación de turnos): el mensaje describe el estado Y la acción
concreta para resolverlo, en español y en voseo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import login

_UTC = UTC


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _seed_booking(db, prop_id: int = 999, booking_id: str | None = None) -> str:
    bid = booking_id or f"BK-MSG-{prop_id}"
    db.booking_orders.insert_one(
        {
            "booking_id": bid,
            "prop_id": prop_id,
            "status": "confirmed",
            "guest_name": "Msg Test Guest",
            "guest_email": "msg@test.local",
            "check_in_date": "2026-09-01",
            "check_out_date": "2026-09-04",
            "total_price": 200.0,
            "total_nights": 3,
            "created_at": datetime.now(_UTC),
        }
    )
    return bid


def _open_shift(db, prop_id: int, *, employee: str = "Teller Msg") -> str:
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


def _seed_payment(db, prop_id: int, *, status: str = "confirmed") -> str:
    result = db.reservation_payments.insert_one(
        {
            "prop_id": prop_id,
            "booking_id": f"BK-PAY-{prop_id}",
            "invoice_id": None,
            "amount": 50.0,
            "method": "cash",
            "status": status,
            "reference": f"REF-{status}-{prop_id}",
            "created_at": datetime.now(_UTC),
        }
    )
    return str(result.inserted_id)


async def _login(client, admin_user) -> None:
    assert await login(client, admin_user["username"], admin_user["password"]) == 200


async def _create_invoice(client, booking_id: str, *, prop_id: int = 999) -> str:
    """Create an issued invoice via the API (needs an open shift for prop)."""
    resp = await client.post(
        f"/api/billing/invoices?prop_id={prop_id}",
        json={"booking_id": booking_id, "subtotal": 100.0, "taxes": 10.0},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── Emitir factura ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_invoice_invalid_booking_message(client, admin_user):
    await _login(client, admin_user)

    resp = await client.post(
        "/api/billing/invoices?prop_id=999",
        json={"booking_id": "BK-NO-EXISTE", "subtotal": 100.0, "taxes": 10.0},
    )

    assert resp.status_code == 400
    body = resp.json()["detail"]
    assert "No se pudo crear la factura" in body
    assert "Verificá que la reserva esté confirmada" in body
    assert "e intentá de nuevo" in body


# ── Cancelar factura ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_already_cancelled_invoice_message(client, admin_user, db):
    await _login(client, admin_user)
    booking_id = _seed_booking(db)
    _open_shift(db, 999)
    invoice_id = await _create_invoice(client, booking_id)

    first = await client.post(f"/api/billing/invoices/{invoice_id}/cancel?prop_id=999", json={})
    assert first.status_code == 200, first.text

    second = await client.post(f"/api/billing/invoices/{invoice_id}/cancel?prop_id=999", json={})
    assert second.status_code == 400
    body = second.json()["detail"]
    assert "No se pudo cancelar la factura" in body
    assert "sin pagos confirmados" in body
    assert "e intentá de nuevo" in body


# ── Registrar pago ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pay_already_paid_invoice_message(client, admin_user, db):
    await _login(client, admin_user)
    booking_id = _seed_booking(db)
    _open_shift(db, 999)
    invoice_id = await _create_invoice(client, booking_id)

    first = await client.post(f"/api/billing/invoices/{invoice_id}/pay?prop_id=999")
    assert first.status_code == 200, first.text

    second = await client.post(f"/api/billing/invoices/{invoice_id}/pay?prop_id=999")
    assert second.status_code == 400
    body = second.json()["detail"]
    assert "La factura no está pendiente de pago" in body
    assert "Solo se pueden pagar facturas emitidas sin pagos confirmados" in body
    assert "verificá el estado de la factura" in body


@pytest.mark.asyncio
async def test_refund_already_refunded_payment_message(client, admin_user, db):
    await _login(client, admin_user)
    _open_shift(db, 999)
    payment_id = _seed_payment(db, 999, status="refunded")

    resp = await client.post(f"/api/billing/payments/{payment_id}/refund?prop_id=999", json={})
    assert resp.status_code == 400
    body = resp.json()["detail"]
    assert "No se pudo reembolsar el pago" in body
    assert "Verificá que el pago esté confirmado" in body
    assert "turno de caja activo" in body


@pytest.mark.asyncio
async def test_link_shift_prop_mismatch_message(client, admin_user, db):
    await _login(client, admin_user)
    payment_id = _seed_payment(db, 999)
    foreign_shift_id = _open_shift(db, 888)

    resp = await client.post(
        f"/api/billing/payments/{payment_id}/link-shift?prop_id=999",
        json={"shift_id": foreign_shift_id},
    )
    assert resp.status_code == 400
    body = resp.json()["detail"]
    assert "El turno pertenece a otro hotel" in body
    assert "Elegí un turno abierto del hotel del pago" in body
    assert "e intentá de nuevo" in body


# ── Folios ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_folio_not_found_message(client, admin_user):
    await _login(client, admin_user)

    resp = await client.get("/api/billing/folios/BK-NO-EXISTE?prop_id=999")

    assert resp.status_code == 404
    body = resp.json()["detail"]
    assert "No se encontró un folio para esta reserva" in body
    assert "Verificá el número de reserva" in body
    assert "e intentá de nuevo" in body


@pytest.mark.asyncio
async def test_reopen_folio_not_found_message(client, admin_user):
    await _login(client, admin_user)

    resp = await client.post("/api/billing/folios/BK-NO-EXISTE/reopen?prop_id=999")

    assert resp.status_code == 409
    body = resp.json()["detail"]
    assert "saldo positivo cobrable o no existe" in body
    assert "Verificá que el folio esté cerrado" in body
    assert "e intentá de nuevo" in body
