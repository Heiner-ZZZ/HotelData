"""Admin tooling for bookings without a price.

Spec: las reservas creadas sin tarifa disponible quedan con
``total_price=None``. Para el banner "reservas sin precio" del admin:

- ``GET /api/reservations/unpriced`` → lista las reservas sin precio
  (staff, ``reservations.update``), respetando el filtro de hoteles.
- ``POST /api/reservations/{booking_id}/recalculate-price`` → recalcula el
  precio de una sola reserva con el path canónico ``_calculate_total_price``
  (fallback a ``rate_plans.base_rate``) y corrige folio/penalizaciones,
  reutilizando la lógica de ``scripts/migrate_backfill_booking_prices.py``.

Reglas:
- Ya con precio → no-op (200 con ``already_priced``).
- Sin tarifa calculable → 200 con ``skipped=unpricable``, no escribe.
- Reserva inexistente → 404.
- Solo staff (``reservations.update``); cliente → 403.
- El POST respeta el alcance de hoteles del usuario (``user_can_access_hotel``):
  un gerente no puede recalcular reservas de hoteles fuera de su
  ``assigned_hotels`` (403) — mismo hardening que el GET /unpriced.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from passlib.context import CryptContext

from tests.conftest import login

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_booking(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 9001,
        "status": "confirmed",
        "room_type_id": "RT-9001-doble",
        "rate_plan_id": "",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-13",
        "rooms": 1,
        "adults": 2,
        "children": 0,
        "total_nights": 3,
        "currency": "USD",
        "total_price": None,
        "original_total_price": None,
        "is_test": True,
    }
    doc.update(overrides)
    db.booking_orders.insert_one(doc)


def _seed_invoice(db, booking_id: str, **overrides) -> None:
    # En producción ``_write_both`` crea factura + mirror con el MISMO _id
    # (update_with_outbox hace update sin upsert sobre el mirror).
    doc = {
        "invoice_number": "INV-TEST-1",
        "booking_id": booking_id,
        "prop_id": 9001,
        "room_subtotal": 0.0,
        "extras_total": 0.0,
        "subtotal": 0.0,
        "taxes": 0.0,
        "total": 0.0,
        "status": "issued",
        "line_items": [
            {
                "item_id": "it-minibar", "type": "additional_charge",
                "concept": "Minibar", "amount": 10.0, "quantity": 1,
                "total": 10.0,
                "created_at": datetime.now(timezone.utc),
            }
        ],
        "issued_at": datetime.now(timezone.utc),
    }
    doc.update(overrides)
    inserted = db.reservation_invoices.insert_one(doc)
    db.fact_reservation_invoices.insert_one({**doc, "_id": inserted.inserted_id})


def _seed_folio(db, booking_id: str) -> None:
    from datetime import datetime, timezone

    from bson import ObjectId

    db.guest_folios.insert_one(
        {
            "folio_number": "FL-TEST-1",
            "booking_id": booking_id,
            "prop_id": 9001,
            "status": "open",
            "total_room": 0.0,
            "total_charges": 5.0,
            "total_discounts": 0.0,
            "total_payments": 2.0,
            "total_due": 3.0,
            "postings": [
                {
                    "posting_id": ObjectId(),
                    "type": "room",
                    "category": "Habitación",
                    "concept": "Habitación — 3 noche(s)",
                    "amount": 0.0,
                    "quantity": 3,
                    "unit_price": 0.0,
                    "reference_id": booking_id,
                    "reference_type": "booking",
                    "posted_at": datetime.now(timezone.utc),
                }
            ],
            "posting_count": 1,
        }
    )


async def test_recalculate_price_backfills_booking_and_folio(client, db, admin_user):
    """Recalcula el precio (fallback a base_rate) y corrige el folio en $0."""
    db.rate_plans.insert_one({"prop_id": 9001, "rate_plan_id": "RP-9001-flex", "base_rate": 120.0})
    _seed_booking(db, "BK-REC-0001")
    _seed_folio(db, "BK-REC-0001")
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0001/recalculate-price", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_price"] == 360.0  # 3 noches × $120
    assert body["penalty_recomputed"] is False
    assert body["folio_recomputed"] is True

    booking = db.booking_orders.find_one({"booking_id": "BK-REC-0001"})
    assert booking["total_price"] == 360.0
    assert booking["metadata"]["migration_id"] == "backfill_booking_prices_v1"
    folio = db.guest_folios.find_one({"booking_id": "BK-REC-0001"})
    assert folio["total_room"] == 360.0
    assert folio["total_due"] == 363.0  # 360 + 5 − 2


async def test_recalculate_price_already_priced_is_noop(client, db, admin_user):
    """Reserva con precio → no-op, no se re-toca."""
    _seed_booking(db, "BK-REC-0002", total_price=500.0)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0002/recalculate-price", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("already_priced") is True
    assert db.booking_orders.find_one({"booking_id": "BK-REC-0002"})["total_price"] == 500.0


async def test_recalculate_price_unpricable_skips(client, db, admin_user):
    """Sin calendario ni rate plans → no se fabrica precio."""
    _seed_booking(db, "BK-REC-0003", prop_id=99999)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0003/recalculate-price", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["skipped"] == "unpricable"
    assert db.booking_orders.find_one({"booking_id": "BK-REC-0003"})["total_price"] is None


async def test_recalculate_price_not_found_404(client, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.post("/api/reservations/BK-NO-EXISTE/recalculate-price", json={})
    assert resp.status_code == 404


async def test_recalculate_price_requires_staff_permission(client, db, cliente_user):
    """El rol cliente no puede recalcular precios."""
    _seed_booking(db, "BK-REC-0004")
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.post("/api/reservations/BK-REC-0004/recalculate-price", json={})
    assert resp.status_code == 403


async def test_unpriced_list_returns_only_missing_prices(client, db, admin_user):
    """GET /unpriced → solo reservas sin total_price, respeta filtro de hotel."""
    db.rate_plans.insert_one({"prop_id": 9001, "rate_plan_id": "RP-9001-flex", "base_rate": 120.0})
    _seed_booking(db, "BK-REC-0005")  # sin precio → aparece
    _seed_booking(db, "BK-REC-0006", total_price=200.0)  # con precio → no aparece
    _seed_booking(db, "BK-REC-0007", prop_id=9002)  # sin precio, otro hotel → sí (superadmin ve todo)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.get("/api/reservations/unpriced")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = [i["booking_id"] for i in body["items"]]
    assert "BK-REC-0005" in ids
    assert "BK-REC-0007" in ids
    assert "BK-REC-0006" not in ids
    assert body["total"] == len(body["items"])


async def test_unpriced_list_requires_staff(client, db, cliente_user):
    """El rol cliente no ve la lista de sin precio."""
    _seed_booking(db, "BK-REC-0008")
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.get("/api/reservations/unpriced")
    assert resp.status_code == 403


def _seed_hotel_scoped_user(db, *, username: str, password: str, assigned_hotels: list[int]) -> dict:
    """Usuario con rol global ``gerente_hotel`` (con ``reservations.update``)
    y alcance limitado a ``assigned_hotels`` (mismo patrón que
    ``test_hotel_operational_gates``)."""
    db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": ["reservations.read", "reservations.update"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username,
            "password_hash": _pwd.hash(password),
            "primary_role": "gerente_hotel",
            "role_ids": [],
            "assigned_hotels": assigned_hotels,
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {
        "user_id": str(user_id),
        "username": username,
        "password": password,
        "primary_role": "gerente_hotel",
    }


async def test_recalculate_price_backfills_invoice_too(client, db, admin_user):
    """El POST también recalcula la factura en $0 de la reserva.

    Mirror de ``generate_invoice_for_booking``: con total 360 (3 noches ×
    $120) y un line_item extra de $10, la factura queda room_subtotal =
    360/1.16 = 310.34, taxes = 49.66, extras_total = 10, subtotal = 320.34,
    total = 370.00. El desglose de line_items se preserva y el mirror
    fact_reservation_invoices se actualiza."""
    db.rate_plans.insert_one({"prop_id": 9001, "rate_plan_id": "RP-9001-flex", "base_rate": 120.0})
    _seed_booking(db, "BK-REC-0010")
    _seed_invoice(db, "BK-REC-0010")
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0010/recalculate-price", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_price"] == 360.0
    assert body["invoice_recomputed"] is True

    inv = db.reservation_invoices.find_one({"booking_id": "BK-REC-0010"})
    assert inv["room_subtotal"] == 310.34
    assert inv["taxes"] == 49.66
    assert inv["extras_total"] == 10.0
    assert inv["subtotal"] == 320.34
    assert inv["total"] == 370.0
    assert len(inv["line_items"]) == 1  # desglose intacto
    assert inv["metadata"]["migration_id"] == "backfill_booking_prices_v1"
    mirror = db.fact_reservation_invoices.find_one({"booking_id": "BK-REC-0010"})
    assert mirror is not None and mirror["total"] == 370.0


async def test_recalculate_price_keeps_priced_invoice(client, db, admin_user):
    """Factura con total real (> 0) no se re-toca."""
    db.rate_plans.insert_one({"prop_id": 9001, "rate_plan_id": "RP-9001-flex", "base_rate": 120.0})
    _seed_booking(db, "BK-REC-0011")
    db.reservation_invoices.insert_one(
        {
            "invoice_number": "INV-TEST-2",
            "booking_id": "BK-REC-0011",
            "prop_id": 9001,
            "room_subtotal": 500.0, "subtotal": 500.0,
            "taxes": 0.0, "total": 500.0,
            "status": "issued", "line_items": [],
            "issued_at": datetime.now(timezone.utc),
        }
    )
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0011/recalculate-price", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json().get("invoice_recomputed") is False
    assert db.reservation_invoices.find_one({"booking_id": "BK-REC-0011"})["total"] == 500.0


async def test_recalculate_price_denied_for_other_hotel(client, db):
    """RED: un gerente de hotel 9001 NO puede recalcular una reserva del 9002.

    El GET /unpriced ya respeta el filtro de hoteles, pero el POST por
    booking_id no validaba el alcance: un gerente con ``reservations.update``
    global podía mutar reservas de hoteles que no administra.
    """
    _seed_booking(db, "BK-REC-0091", prop_id=9002)
    user = _seed_hotel_scoped_user(
        db, username="gerente_scope", password="Pass123!", assigned_hotels=[9001]
    )
    assert await login(client, user["username"], user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0091/recalculate-price", json={})
    assert resp.status_code == 403
    # Y no se escribió nada sobre la reserva del otro hotel.
    assert db.booking_orders.find_one({"booking_id": "BK-REC-0091"})["total_price"] is None


async def test_recalculate_price_allowed_for_own_hotel(client, db):
    """Control: el mismo gerente SÍ recalcula una reserva de SU hotel (9001)."""
    db.rate_plans.insert_one({"prop_id": 9001, "rate_plan_id": "RP-9001-flex", "base_rate": 120.0})
    _seed_booking(db, "BK-REC-0092", prop_id=9001)
    user = _seed_hotel_scoped_user(
        db, username="gerente_scope2", password="Pass123!", assigned_hotels=[9001]
    )
    assert await login(client, user["username"], user["password"]) == 200

    resp = await client.post("/api/reservations/BK-REC-0092/recalculate-price", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_price"] == 360.0  # 3 noches × $120
