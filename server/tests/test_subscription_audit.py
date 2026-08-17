"""Fase 7 — Auditoría completa de suscripciones (PLAN_SUSCRIPCION_Y_PAGOS.md §4).

El invariante del plan (§4): *"Toda transición queda en `audit_log`
(entity_type `subscription`, vía `enqueue_audit_log`, mismo patrón que
`hotel_registration`)."*

Cubre que cada transición de la máquina de estados escriba exactamente un
``audit_log`` con ``entity_type="subscription"``, acción canónica, ``prop_id``
y ``changed_by`` correcto (el actor real en verify/reject/submit/choose/
cancel/override; ``system`` en las transiciones del sweep: overdue/suspend y
en create/emit desde aprobación/migración).
"""

from __future__ import annotations

import pytest
from bson import ObjectId

from src.app.modules.subscriptions import service as svc

pytestmark = pytest.mark.asyncio

SUBSCRIPTION_ENTITY = "subscription"


# ── Helpers ────────────────────────────────────────────────────────────


def _make(db, *, prop_id=1, band=3, price=149):
    return svc.create_subscription(
        db,
        prop_id=prop_id,
        owner_user_id=ObjectId(),
        band=band,
        price_usd=price,
    )


def _sub_id(db, prop_id=1):
    return db.subscriptions.find_one({"prop_id": prop_id})["_id"]


def _audit_entries(db, **extra):
    return list(db.audit_log.find({"entity_type": SUBSCRIPTION_ENTITY, **extra}))


def _advance_to_active(db, sub_id):
    inv = svc.emit_invoice(db, subscription_id=sub_id)
    pay = svc.submit_payment(
        db,
        subscription_id=sub_id,
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=inv["amount_usd"],
        changed_by="owner_test",
    )
    svc.verify_payment(db, payment_id=pay["_id"], verified_by="admin_test")
    return inv


def _advance_to_overdue(db, sub_id):
    _advance_to_active(db, sub_id)
    svc.emit_invoice(db, subscription_id=sub_id)
    svc.mark_overdue(db, subscription_id=sub_id)


# ── create_subscription / emit_invoice ─────────────────────────────────


async def test_create_subscription_audited(db):
    sub = _make(db)
    entries = _audit_entries(db, action="subscription.created")
    assert len(entries) == 1
    entry = entries[0]
    assert entry["prop_id"] == 1
    assert entry["entity_id"] == str(sub["_id"])
    assert entry["changed_by"] == "system"


async def test_emit_invoice_audited(db):
    sub = _make(db)
    svc.emit_invoice(db, subscription_id=sub["_id"])
    entries = _audit_entries(db, action="invoice.emitted")
    assert len(entries) == 1
    assert entries[0]["prop_id"] == 1


# ── submit_payment / choose ────────────────────────────────────────────


async def test_submit_payment_audited_with_owner_actor(db):
    sub = _make(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
        changed_by="owner_test",
    )
    entries = _audit_entries(db, action="payment.submitted")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "owner_test"


async def test_choose_subscription_audited(db):
    sub = _make(db)
    svc.choose_subscription(
        db,
        subscription_id=sub["_id"],
        band=3,
        billing_cycle="annual",
        payment_method="bank_transfer",
        changed_by="owner_test",
    )
    entries = _audit_entries(db, action="plan.chosen")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "owner_test"


# ── verify / reject ────────────────────────────────────────────────────


async def test_verify_payment_audited_with_verifier(db):
    sub = _make(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db, subscription_id=sub["_id"], invoice_id=inv["_id"],
        method="bank_transfer", amount=149, changed_by="owner_test",
    )
    svc.verify_payment(db, payment_id=pay["_id"], verified_by="admin_test")
    entries = _audit_entries(db, action="payment.verified")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "admin_test"


async def test_reject_payment_audited_with_reason(db):
    sub = _make(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db, subscription_id=sub["_id"], invoice_id=inv["_id"],
        method="bank_transfer", amount=149, changed_by="owner_test",
    )
    svc.reject_payment(
        db, payment_id=pay["_id"], reason="Comprobante ilegible", rejected_by="admin_test"
    )
    entries = _audit_entries(db, action="payment.rejected")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "admin_test"
    assert "Comprobante ilegible" in entries[0].get("diff", {}).get("reason", "")


# ── overdue / suspend (sweep) ──────────────────────────────────────────


async def test_mark_overdue_audited(db):
    sub = _make(db)
    _advance_to_overdue(db, sub["_id"])
    entries = _audit_entries(db, action="overdue")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "system"


async def test_suspend_audited(db):
    sub = _make(db)
    _advance_to_overdue(db, sub["_id"])
    svc.suspend(db, subscription_id=sub["_id"])
    entries = _audit_entries(db, action="suspended")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "system"


# ── cancel / override ──────────────────────────────────────────────────


async def test_cancel_audited_with_actor(db):
    sub = _make(db)
    svc.cancel(db, subscription_id=sub["_id"], reason="Cierre", changed_by="admin_test")
    entries = _audit_entries(db, action="subscription.cancelled")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "admin_test"
    assert entries[0].get("diff", {}).get("reason") == "Cierre"


async def test_override_audited_with_actor(db):
    _make(db)
    svc.override_subscription(
        db, prop_id=1, price_band=4, price_usd=229, notes="Negociado", changed_by="admin_test"
    )
    entries = _audit_entries(db, action="price.override")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "admin_test"
    assert entries[0].get("diff", {}).get("price_band", {}).get("new") == 4


async def test_override_scheduled_audited(db):
    """Override sobre suscripción active se audita como programado (preaviso)."""
    sub = _make(db)
    _advance_to_active(db, sub["_id"])
    svc.override_subscription(
        db, prop_id=1, price_band=4, price_usd=229, notes="Negociado", changed_by="admin_test"
    )
    entries = _audit_entries(db, action="price.override.scheduled")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "admin_test"
    assert entries[0].get("diff", {}).get("price_band", {}).get("new") == 4
    assert entries[0].get("diff", {}).get("price_usd", {}).get("new") == 229


async def test_override_applied_audited_on_emit_invoice(db):
    """Al emitir la factura del ciclo siguiente, la aplicación se audita como system."""
    sub = _make(db)
    _advance_to_active(db, sub["_id"])
    svc.override_subscription(
        db, prop_id=1, price_band=4, price_usd=229, changed_by="admin_test"
    )
    svc.emit_invoice(db, subscription_id=sub["_id"])

    entries = _audit_entries(db, action="price.override.applied")
    assert len(entries) == 1
    assert entries[0]["changed_by"] == "system"
    assert entries[0].get("diff", {}).get("price_band", {}).get("old") == 3
    assert entries[0].get("diff", {}).get("price_band", {}).get("new") == 4
