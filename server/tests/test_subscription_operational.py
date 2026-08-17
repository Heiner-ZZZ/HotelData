"""Fase 5 — Suspensión perezosa por impago + integración ``is_operational``.

Cubre (docs/PLAN_SUSCRIPCION_Y_PAGOS.md §9.3/§9.4/§10 + Fase 5):

- ``suspend`` escribe ``is_operational=false`` en ``dim_hotels`` (sigue publicado).
- ``verify_payment`` reactiva: ``is_operational=true`` + suscripción ``active``.
- ``cancel`` es terminal: ``is_operational=false`` + ``published=false``.
- ``sweep_due_subscriptions`` (perezoso, sin cron): renovación al vencer
  ``renews_at``, factura impaga vencida → ``overdue``, y gracia agotada →
  ``suspended``.
- ``emit_invoice`` avanza el período (no reusa el período anterior).
- El gate operativo existente (``non_operational_hotel`` + ``require_prop_permission``
  + middleware) bloquea un hotel suspendido aunque siga publicado, y lo deja
  pasar tras la reactivación.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from passlib.context import CryptContext

from src.app.modules.hotels.service.operational import non_operational_hotel
from src.app.modules.subscriptions import service as svc
from tests.conftest import login

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_hotel(db, *, prop_id: int, published: bool = True, operational: bool = True) -> None:
    """dim_hotels. ``operational=None`` no se soporta aquí (siempre explícito)."""
    doc: dict = {"prop_id": prop_id, "hotel_name": f"Hotel {prop_id}"}
    if published is not None:
        doc["published"] = published
    if operational is not None:
        doc["is_operational"] = operational
    db.dim_hotels.insert_one(doc)


def _make(db, *, prop_id: int = 1, band: int = 2, price: float = 89) -> dict:
    return svc.create_subscription(
        db, prop_id=prop_id, owner_user_id=ObjectId(), band=band, price_usd=price
    )


def _advance_to_active(db, sub_id) -> dict:
    inv = svc.emit_invoice(db, subscription_id=sub_id)
    pay = svc.submit_payment(
        db,
        subscription_id=sub_id,
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=inv["amount_usd"],
    )
    svc.verify_payment(db, payment_id=pay["_id"])
    return inv


def _advance_to_overdue(db, sub_id) -> dict:
    _advance_to_active(db, sub_id)
    renewal = svc.emit_invoice(db, subscription_id=sub_id)
    svc.mark_overdue(db, subscription_id=sub_id)
    return renewal


# ── emit_invoice: avance de período ───────────────────────────────────


async def test_emit_invoice_advances_period(db):
    """La renovación NO reusa el período anterior (necesario para el sweep)."""
    sub = _make(db)
    first = svc.emit_invoice(db, subscription_id=sub["_id"])
    second = svc.emit_invoice(db, subscription_id=sub["_id"])

    assert second["period_start"] == first["period_end"]
    assert second["period_end"] > second["period_start"]

    doc = db.subscriptions.find_one({"prop_id": 1})
    assert doc["renews_at"] == second["period_end"]
    assert doc["current_period_start"] == second["period_start"]
    assert doc["current_period_end"] == second["period_end"]


# ── Escrituras operativas ─────────────────────────────────────────────


async def test_suspend_writes_is_operational_false(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    _advance_to_overdue(db, sub["_id"])

    svc.suspend(db, subscription_id=sub["_id"])

    hotel = db.dim_hotels.find_one({"prop_id": 1})
    assert hotel["is_operational"] is False
    assert hotel["published"] is True  # presencia pública intacta (§12 edge case 3)


async def test_verify_reactivates_operational(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    overdue_inv = _advance_to_overdue(db, sub["_id"])
    svc.suspend(db, subscription_id=sub["_id"])
    assert db.dim_hotels.find_one({"prop_id": 1})["is_operational"] is False

    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=overdue_inv["_id"],
        method="bank_transfer",
        amount=overdue_inv["amount_usd"],
    )
    svc.verify_payment(db, payment_id=pay["_id"])

    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_ACTIVE
    assert db.dim_hotels.find_one({"prop_id": 1})["is_operational"] is True


async def test_cancel_deactivates_hotel(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)

    svc.cancel(db, subscription_id=sub["_id"], reason="Cierre del hotel")

    hotel = db.dim_hotels.find_one({"prop_id": 1})
    assert hotel["is_operational"] is False
    assert hotel["published"] is False  # cancelación terminal (§4)


# ── sweep_due_subscriptions (perezoso) ────────────────────────────────


async def test_sweep_emits_renewal_when_period_due(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    _advance_to_active(db, sub["_id"])
    db.subscriptions.update_one(
        {"_id": sub["_id"]}, {"$set": {"renews_at": _now() - timedelta(days=1)}}
    )
    before = db.subscription_invoices.count_documents({"subscription_id": sub["_id"]})

    result = svc.sweep_due_subscriptions(db, now=_now())

    assert result["renewals"] == 1
    assert result["overdue"] == 0
    assert result["suspended"] == 0
    assert (
        db.subscription_invoices.count_documents({"subscription_id": sub["_id"]})
        == before + 1
    )
    # Sigue active: la factura nueva tiene su propia gracia (due_date futuro).
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_ACTIVE


async def test_sweep_marks_overdue_when_invoice_due(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    _advance_to_active(db, sub["_id"])
    renewal = svc.emit_invoice(db, subscription_id=sub["_id"])
    db.subscription_invoices.update_one(
        {"_id": renewal["_id"]}, {"$set": {"due_date": _now() - timedelta(days=1)}}
    )

    result = svc.sweep_due_subscriptions(db, now=_now())

    assert result["overdue"] == 1
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_OVERDUE
    assert (
        db.subscription_invoices.find_one({"_id": renewal["_id"]})["status"]
        == svc.INVOICE_OVERDUE
    )


async def test_sweep_suspends_when_grace_expired(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    overdue_inv = _advance_to_overdue(db, sub["_id"])
    db.subscription_invoices.update_one(
        {"_id": overdue_inv["_id"]},
        {"$set": {"due_date": _now() - timedelta(days=svc.SUSPENSION_GRACE_DAYS + 1)}},
    )

    result = svc.sweep_due_subscriptions(db, now=_now())

    assert result["suspended"] == 1
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_SUSPENDED
    assert db.dim_hotels.find_one({"prop_id": 1})["is_operational"] is False
    assert db.dim_hotels.find_one({"prop_id": 1})["published"] is True


async def test_sweep_does_not_suspend_within_grace(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    _advance_to_overdue(db, sub["_id"])  # due_date de la renovación sigue futuro

    result = svc.sweep_due_subscriptions(db, now=_now())

    assert result["suspended"] == 0
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_OVERDUE


async def test_sweep_is_idempotent(db):
    _seed_hotel(db, prop_id=1, published=True, operational=True)
    sub = _make(db)
    _advance_to_active(db, sub["_id"])
    db.subscriptions.update_one(
        {"_id": sub["_id"]}, {"$set": {"renews_at": _now() - timedelta(days=1)}}
    )

    first = svc.sweep_due_subscriptions(db, now=_now())
    second = svc.sweep_due_subscriptions(db, now=_now())

    assert first["renewals"] == 1
    assert second["renewals"] == 0
    # 2 facturas: la pagada + la renovación. No se emiten duplicados.
    assert db.subscription_invoices.count_documents({"subscription_id": sub["_id"]}) == 2


# ── Gate operativo (hotel suspendido pero publicado) ──────────────────


async def test_non_operational_hotel_detects_suspended(db):
    _seed_hotel(db, prop_id=1, published=True, operational=False)
    assert non_operational_hotel(db, 1) is not None


async def test_non_operational_hotel_legacy_without_fields_passes(db):
    """Backward compat: legado sin ``published``/``is_operational`` → operativo."""
    db.dim_hotels.insert_one({"prop_id": 1, "hotel_name": "Legado"})
    assert non_operational_hotel(db, 1) is None


async def test_legacy_route_403_for_suspended_hotel(client, db, admin_user):
    """El middleware bloquea un hotel suspendido (publicado pero no operativo)."""
    _seed_hotel(db, prop_id=9002, published=True, operational=False)
    assert await login(client, "admin_test", "AdminPass123!") == 200

    resp = await client.get("/api/billing/invoices", params={"prop_id": 9002})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


# ── require_prop_permission: 403 suspendido → 200 tras reactivar ──────


def _seed_manager_with_hotel_role(db, prop_id: int) -> tuple[str, str]:
    """Catálogo + plantilla + hotel_role + usuario gerente + assignment."""
    db.permissions.insert_one(
        {
            "permission_code": "hotel.manage_roles",
            "description": "hotel.manage_roles",
            "is_system": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    template_id = db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": ["hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    hotel_role_id = db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": "gerente_hotel",
            "display_name": f"Gerente Hotel {prop_id}",
            "permissions": ["hotel.manage_roles"],
            "based_on_role_id": template_id,
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    user_id = db.users.insert_one(
        {
            "username": f"gerente_{prop_id}",
            "email": f"gerente_{prop_id}@hotel.local",
            "display_name": f"Gerente {prop_id}",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "gerente_hotel",
            "role_ids": [],
            "assigned_hotels": [prop_id],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": prop_id,
            "role_id": hotel_role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )
    return f"gerente_{prop_id}", "Pass123!"


async def test_prop_permission_403_suspended_and_200_after_reactivation(client, db):
    """Impago → suspended → 403; verify → active → 200 (gate existente)."""
    prop_id = 7001
    _seed_hotel(db, prop_id=prop_id, published=True, operational=True)
    username, password = _seed_manager_with_hotel_role(db, prop_id)

    # Impago → suspended → is_operational=false.
    sub = svc.create_subscription(
        db, prop_id=prop_id, owner_user_id=ObjectId(), band=2, price_usd=89
    )
    overdue_inv = _advance_to_overdue(db, sub["_id"])
    svc.suspend(db, subscription_id=sub["_id"])
    assert db.dim_hotels.find_one({"prop_id": prop_id})["is_operational"] is False

    assert await login(client, username, password) == 200

    resp = await client.get(f"/api/management/hotels/{prop_id}/roles")
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]

    # Reactivación: pago conciliado → active + is_operational=true.
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=overdue_inv["_id"],
        method="bank_transfer",
        amount=overdue_inv["amount_usd"],
    )
    svc.verify_payment(db, payment_id=pay["_id"])
    assert db.dim_hotels.find_one({"prop_id": prop_id})["is_operational"] is True

    resp = await client.get(f"/api/management/hotels/{prop_id}/roles")
    assert resp.status_code == 200
