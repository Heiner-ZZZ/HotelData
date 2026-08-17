"""Fase 3 — endpoints del dueño ``/api/billing/subscriptions/me`` (PLAN §6.1).

Rutas:
- ``GET  /me``            → suscripción + plan + estado + próxima factura + métodos.
- ``POST /me/choose``     → confirma banda derivada + ciclo + método de pago.
- ``POST /me/pay``        → registra comprobante (pending_verification).
- ``GET  /me/invoices``   → historial de facturas.

Gate: ``require_login`` + pertenencia estricta (el dueño solo ve SU suscripción,
resuelta por ``owner_user_id`` — deny-by-default estructural, sin prop_id en el path).
"""

from __future__ import annotations

import pytest
from passlib.context import CryptContext

from src.app.modules.subscriptions import service as subs

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

OWNER_PASSWORD = "OwnerPass123!"


def _seed_owner(db, *, prop_id: int = 42) -> dict:
    """Crea dueño (hotel_partner) + hotel + suscripción pendiente con factura."""
    owner_id = db.users.insert_one(
        {
            "username": f"owner_{prop_id}",
            "email": f"owner{prop_id}@hotel.local",
            "display_name": "Dueño Hotel",
            "password_hash": _pwd.hash(OWNER_PASSWORD),
            "primary_role": "hotel_partner",
            "assigned_hotels": [prop_id],
            "approval_status": "approved",
            "is_active": True,
            "created_at": None,
        }
    ).inserted_id
    db.dim_hotels.insert_one(
        {
            "prop_id": prop_id,
            "hotel_name": f"Hotel {prop_id}",
            "approval_status": "approved",
            "is_operational": True,
            "published": True,
            "owner_user_id": owner_id,
            "currency": "USD",
            "total_rooms_declared": 20,
        }
    )
    sub = subs.create_subscription(
        db,
        prop_id=prop_id,
        owner_user_id=owner_id,
        band=2,
        price_usd=89,
    )
    inv = subs.emit_invoice(db, subscription_id=sub["_id"])
    return {
        "user_id": owner_id,
        "username": f"owner_{prop_id}",
        "email": f"owner{prop_id}@hotel.local",
        "password": OWNER_PASSWORD,
        "prop_id": prop_id,
        "subscription": sub,
        "invoice": inv,
    }


async def _login_owner(client, owner: dict) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": owner["username"], "password": owner["password"]},
    )
    assert resp.status_code == 200, resp.text


# ── GET /me ────────────────────────────────────────────────────────────


async def test_me_requires_auth(client):
    resp = await client.get("/api/billing/subscriptions/me")
    assert resp.status_code == 401


async def test_me_returns_subscription(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.get("/api/billing/subscriptions/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["prop_id"] == 42
    assert body["band"] == 2
    assert body["band_label"] == "Pequeño"
    assert body["status"] == subs.STATUS_PENDING_PAYMENT
    assert body["billing_cycle"] == "monthly"
    assert body["price_usd"] == 89
    assert body["id"]  # _id serializado como string
    assert len(body["payment_methods"]) == 3


async def test_me_returns_next_invoice(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.get("/api/billing/subscriptions/me")
    body = resp.json()
    assert body["next_invoice"] is not None
    assert body["next_invoice"]["status"] == subs.INVOICE_UNPAID
    assert body["next_invoice"]["amount_usd"] == 89
    assert body["next_invoice"]["invoice_number"].startswith("SUB-42-")


async def test_me_404_when_owner_has_no_subscription(client, db):
    db.users.insert_one(
        {
            "username": "sin_sub",
            "email": "sin_sub@hotel.local",
            "password_hash": _pwd.hash(OWNER_PASSWORD),
            "primary_role": "hotel_partner",
            "assigned_hotels": [99],
            "approval_status": "approved",
            "is_active": True,
        }
    )
    db.dim_hotels.insert_one(
        {
            "prop_id": 99,
            "hotel_name": "Hotel Sin Suscripción",
            "approval_status": "approved",
            "owner_user_id": db.users.find_one({"username": "sin_sub"})["_id"],
        }
    )
    await _login_owner(
        client,
        {"username": "sin_sub", "password": OWNER_PASSWORD, "prop_id": 99},
    )

    resp = await client.get("/api/billing/subscriptions/me")
    assert resp.status_code == 404


async def test_me_deny_by_default_for_non_owner(client, db):
    """Un usuario sin hotel propio (cliente) no accede a ninguna suscripción."""
    db.users.insert_one(
        {
            "username": "cliente_x",
            "email": "cliente_x@hotel.local",
            "password_hash": _pwd.hash(OWNER_PASSWORD),
            "primary_role": "cliente",
            "is_active": True,
        }
    )
    await _login_owner(
        client,
        {"username": "cliente_x", "password": OWNER_PASSWORD, "prop_id": 0},
    )

    resp = await client.get("/api/billing/subscriptions/me")
    assert resp.status_code == 404


# ── POST /me/choose ────────────────────────────────────────────────────


async def test_choose_updates_cycle_and_method(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.post(
        "/api/billing/subscriptions/me/choose",
        json={"band": 2, "billing_cycle": "annual", "payment_method": "bank_transfer"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["billing_cycle"] == "annual"
    assert body["payment_method"] == "bank_transfer"
    assert body["price_usd"] == 69  # anual = 3 cuotas gratis

    sub = db.subscriptions.find_one({"prop_id": 42})
    assert sub["billing_cycle"] == "annual"
    assert sub["payment_method"] == "bank_transfer"
    assert sub["price_usd"] == 69


async def test_choose_rejects_mismatched_band(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.post(
        "/api/billing/subscriptions/me/choose",
        json={"band": 4, "billing_cycle": "monthly", "payment_method": "bank_transfer"},
    )
    assert resp.status_code == 400
    assert "no corresponde" in resp.json()["detail"]


async def test_choose_rejects_invalid_payment_method(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.post(
        "/api/billing/subscriptions/me/choose",
        json={"band": 2, "billing_cycle": "monthly", "payment_method": "credit_card"},
    )
    assert resp.status_code == 400


async def test_choose_conflict_when_active_cycle_changes(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    # Llevar la suscripción a active (verify el pago de la primera factura).
    pay = subs.submit_payment(
        db,
        subscription_id=owner["subscription"]["_id"],
        invoice_id=owner["invoice"]["_id"],
        method="bank_transfer",
        amount=89,
    )
    subs.verify_payment(db, payment_id=pay["_id"])

    resp = await client.post(
        "/api/billing/subscriptions/me/choose",
        json={"band": 2, "billing_cycle": "annual", "payment_method": "bank_transfer"},
    )
    assert resp.status_code == 409


# ── POST /me/pay ───────────────────────────────────────────────────────


async def test_pay_registers_pending_payment(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.post(
        "/api/billing/subscriptions/me/pay",
        json={
            "invoice_id": str(owner["invoice"]["_id"]),
            "method": "bank_transfer",
            "reference": "TX-42",
            "amount": 89,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == subs.PAYMENT_PENDING_VERIFICATION
    assert body["id"]

    assert db.subscriptions.find_one({"prop_id": 42})["status"] == subs.STATUS_PAYMENT_SUBMITTED
    pay = db.subscription_payments.find_one({"reference": "TX-42"})
    assert pay is not None
    assert pay["method"] == "bank_transfer"


async def test_pay_rejects_invoice_from_other_subscription(client, db):
    owner_a = _seed_owner(db, prop_id=42)
    other = _seed_owner(db, prop_id=43)
    await _login_owner(client, owner_a)

    resp = await client.post(
        "/api/billing/subscriptions/me/pay",
        json={
            "invoice_id": str(other["invoice"]["_id"]),
            "method": "bank_transfer",
            "reference": "TX-ROBADO",
            "amount": 89,
        },
    )
    assert resp.status_code == 404


async def test_pay_duplicate_conflict(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    payload = {
        "invoice_id": str(owner["invoice"]["_id"]),
        "method": "bank_transfer",
        "reference": "TX-DOBLE",
        "amount": 89,
    }
    first = await client.post("/api/billing/subscriptions/me/pay", json=payload)
    assert first.status_code == 200, first.text

    second = await client.post("/api/billing/subscriptions/me/pay", json=payload)
    assert second.status_code == 409


# ── GET /me/invoices ───────────────────────────────────────────────────


async def test_invoices_lists_history(client, db):
    owner = _seed_owner(db)
    await _login_owner(client, owner)

    resp = await client.get("/api/billing/subscriptions/me/invoices")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == subs.INVOICE_UNPAID
    assert body["items"][0]["invoice_number"].startswith("SUB-42-")
