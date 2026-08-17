"""Fase 1 — máquina de estados de suscripciones (docs/PLAN_SUSCRIPCION_Y_PAGOS.md §4/§5).

Cubre el servicio de dominio ``src.app.modules.subscriptions.service`` SIN rutas:

- ``create_subscription`` — nace en ``pending_payment``, precio derivado del
  catálogo ``pricing_plans`` o explícito.
- ``emit_invoice`` — factura ``unpaid`` por período (mensual/anual).
- ``submit_payment`` — comprobante ``pending_verification`` + transición de estado.
- ``verify_payment`` / ``reject_payment`` — conciliación (idempotente, motivo
  obligatorio en el rechazo).
- ``mark_overdue`` / ``suspend`` / ``cancel`` — ciclo de impago.
- ``plan_price`` — resolución de precio por banda + ciclo de facturación.
- ``scripts.seed_payment_methods`` — catálogo de métodos de pago manuales.

La máquina de estados (docs/PLAN_SUSCRIPCION_Y_PAGOS.md §4):

    pending_payment → payment_submitted → active
    active → overdue → suspended
    overdue/suspended --pago--> payment_submitted --verify--> active
    cualquiera (no terminal) → cancelled
"""

from __future__ import annotations

import pytest
from bson import ObjectId

from src.app.modules.subscriptions import service as svc

pytestmark = pytest.mark.asyncio


# ── Helpers ────────────────────────────────────────────────────────────


def _make(db, *, prop_id=1, band=3, cycle="monthly", price=None):
    """Crea una suscripción de prueba (banda 3 = Mediano, $149/mes)."""
    return svc.create_subscription(
        db,
        prop_id=prop_id,
        owner_user_id=ObjectId(),
        band=band,
        billing_cycle=cycle,
        price_usd=price,
    )


def _sub_id(db, prop_id=1):
    return db.subscriptions.find_one({"prop_id": prop_id})["_id"]


def _advance_to_active(db, sub_id):
    """pending_payment → payment_submitted → active (con factura pagada)."""
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


def _advance_to_overdue(db, sub_id):
    """active + factura de renovación impaga → overdue."""
    _advance_to_active(db, sub_id)
    renewal = svc.emit_invoice(db, subscription_id=sub_id)
    svc.mark_overdue(db, subscription_id=sub_id)
    return renewal


def _advance_to_suspended(db, sub_id):
    """overdue → suspended."""
    renewal = _advance_to_overdue(db, sub_id)
    svc.suspend(db, subscription_id=sub_id)
    return renewal


# ── create_subscription ────────────────────────────────────────────────


async def test_create_subscription_starts_pending_payment(db):
    sub = _make(db, price=149)
    assert sub["status"] == svc.STATUS_PENDING_PAYMENT
    assert sub["prop_id"] == 1
    assert sub["band"] == 3
    assert sub["billing_cycle"] == "monthly"
    assert sub["price_usd"] == 149
    assert sub["price_band_override"] is False


async def test_create_subscription_duplicate_prop_raises(db):
    _make(db)
    with pytest.raises(svc.SubscriptionConflictError):
        _make(db)


async def test_create_subscription_resolves_price_from_catalog(db):
    db.pricing_plans.insert_one(
        {
            "band": 3,
            "label": "Mediano",
            "min_rooms": 26,
            "max_rooms": 50,
            "monthly_usd": 149,
            "annual_monthly_usd": 109,
            "is_active": True,
        }
    )
    sub = _make(db, price=None)
    assert sub["price_usd"] == 149


async def test_create_subscription_annual_uses_annual_price(db):
    db.pricing_plans.insert_one(
        {
            "band": 3,
            "label": "Mediano",
            "min_rooms": 26,
            "max_rooms": 50,
            "monthly_usd": 149,
            "annual_monthly_usd": 109,
            "is_active": True,
        }
    )
    sub = _make(db, cycle="annual", price=None)
    assert sub["billing_cycle"] == "annual"
    assert sub["price_usd"] == 109


async def test_create_subscription_invalid_band_raises(db):
    with pytest.raises(ValueError):
        _make(db, band=7)


async def test_create_subscription_invalid_cycle_raises(db):
    with pytest.raises(ValueError):
        _make(db, cycle="weekly")


async def test_create_subscription_initial_status_active_for_backfill(db):
    """Escape hatch documentado: el backfill crea suscripciones ya ``active``."""
    sub = svc.create_subscription(
        db,
        prop_id=2,
        owner_user_id=ObjectId(),
        band=3,
        price_usd=149,
        initial_status=svc.STATUS_ACTIVE,
    )
    assert sub["status"] == svc.STATUS_ACTIVE


async def test_create_subscription_invalid_initial_status_raises(db):
    with pytest.raises(ValueError):
        svc.create_subscription(
            db,
            prop_id=3,
            owner_user_id=ObjectId(),
            band=3,
            price_usd=149,
            initial_status="suspended",
        )


# ── plan_price ─────────────────────────────────────────────────────────


async def test_plan_price_reads_catalog(db):
    db.pricing_plans.insert_many(
        [
            {
                "band": 3,
                "label": "Mediano",
                "min_rooms": 26,
                "max_rooms": 50,
                "monthly_usd": 149,
                "annual_monthly_usd": 109,
                "is_active": True,
            },
        ]
    )
    assert svc.plan_price(db, 3, "monthly") == 149
    assert svc.plan_price(db, 3, "annual") == 109


async def test_plan_price_unknown_band_returns_zero(db):
    assert svc.plan_price(db, 99, "monthly") == 0.0


# ── emit_invoice ───────────────────────────────────────────────────────


async def test_emit_invoice_creates_unpaid_invoice(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    assert inv["status"] == svc.INVOICE_UNPAID
    assert inv["prop_id"] == 1
    assert inv["amount_usd"] == 149
    assert inv["invoice_number"].startswith("SUB-1-")
    assert db.subscriptions.find_one({"prop_id": 1})["renews_at"] is not None


async def test_emit_invoice_respects_cycle_length(db):
    from datetime import timedelta

    sub = _make(db, cycle="annual", price=109)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    delta = inv["period_end"] - inv["period_start"]
    assert delta >= timedelta(days=364)


async def test_emit_invoice_rejects_payment_submitted(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
    )
    with pytest.raises(svc.SubscriptionTransitionError):
        svc.emit_invoice(db, subscription_id=sub["_id"])


# ── submit_payment ─────────────────────────────────────────────────────


async def test_submit_payment_moves_to_payment_submitted(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        reference="TX-123",
        amount=149,
    )
    assert pay["status"] == svc.PAYMENT_PENDING_VERIFICATION
    assert pay["method"] == "bank_transfer"
    assert pay["reference"] == "TX-123"
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_PAYMENT_SUBMITTED


async def test_submit_payment_idempotent_per_invoice(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
    )
    with pytest.raises(svc.SubscriptionConflictError):
        svc.submit_payment(
            db,
            subscription_id=sub["_id"],
            invoice_id=inv["_id"],
            method="cash_deposit",
            amount=149,
        )


async def test_submit_payment_invalid_method_raises(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    with pytest.raises(ValueError):
        svc.submit_payment(
            db,
            subscription_id=sub["_id"],
            invoice_id=inv["_id"],
            method="credit_card",
            amount=149,
        )


async def test_submit_payment_requires_positive_amount(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    with pytest.raises(ValueError):
        svc.submit_payment(
            db,
            subscription_id=sub["_id"],
            invoice_id=inv["_id"],
            method="bank_transfer",
            amount=0,
        )


# ── verify_payment / reject_payment ────────────────────────────────────


async def test_verify_payment_marks_invoice_paid_and_activates(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
    )
    verified = svc.verify_payment(db, payment_id=pay["_id"], verified_by="admin_test")
    assert verified["status"] == svc.PAYMENT_VERIFIED
    assert verified["verified_by"] == "admin_test"
    assert db.subscription_invoices.find_one({"_id": inv["_id"]})["status"] == svc.INVOICE_PAID
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_ACTIVE


async def test_verify_payment_already_verified_raises(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
    )
    svc.verify_payment(db, payment_id=pay["_id"])
    with pytest.raises(svc.SubscriptionConflictError):
        svc.verify_payment(db, payment_id=pay["_id"])


async def test_reject_payment_requires_reason(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
    )
    with pytest.raises(ValueError):
        svc.reject_payment(db, payment_id=pay["_id"], reason="   ")


async def test_reject_payment_returns_to_pending_payment(db):
    sub = _make(db, price=149)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        amount=149,
    )
    rejected = svc.reject_payment(
        db, payment_id=pay["_id"], reason="Comprobante ilegible", rejected_by="admin_test"
    )
    assert rejected["status"] == svc.PAYMENT_REJECTED
    assert rejected["rejection_reason"] == "Comprobante ilegible"
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_PENDING_PAYMENT


# ── mark_overdue / suspend / cancel ────────────────────────────────────


async def test_mark_overdue_requires_active(db):
    sub = _make(db, price=149)
    with pytest.raises(svc.SubscriptionTransitionError):
        svc.mark_overdue(db, subscription_id=sub["_id"])


async def test_mark_overdue_flips_latest_unpaid_invoice(db):
    sub = _make(db, price=149)
    renewal = _advance_to_overdue(db, sub["_id"])
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_OVERDUE
    assert db.subscription_invoices.find_one({"_id": renewal["_id"]})["status"] == svc.INVOICE_OVERDUE


async def test_suspend_requires_overdue(db):
    sub = _make(db, price=149)
    with pytest.raises(svc.SubscriptionTransitionError):
        svc.suspend(db, subscription_id=sub["_id"])


async def test_suspend_marks_suspended(db):
    sub = _make(db, price=149)
    _advance_to_suspended(db, sub["_id"])
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_SUSPENDED


async def test_cancel_is_terminal(db):
    sub = _make(db, price=149)
    svc.cancel(db, subscription_id=sub["_id"], reason="Cierre del hotel")
    doc = db.subscriptions.find_one({"prop_id": 1})
    assert doc["status"] == svc.STATUS_CANCELLED
    assert doc["cancelled_reason"] == "Cierre del hotel"
    with pytest.raises(svc.SubscriptionConflictError):
        svc.cancel(db, subscription_id=sub["_id"], reason="otra vez")


async def test_verify_reactivates_suspended(db):
    sub = _make(db, price=149)
    overdue_inv = _advance_to_suspended(db, sub["_id"])
    pay = svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=overdue_inv["_id"],
        method="bank_transfer",
        amount=overdue_inv["amount_usd"],
    )
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_PAYMENT_SUBMITTED
    svc.verify_payment(db, payment_id=pay["_id"])
    assert db.subscriptions.find_one({"prop_id": 1})["status"] == svc.STATUS_ACTIVE


async def test_get_subscription_returns_none_when_missing(db):
    assert svc.get_subscription(db, prop_id=999) is None


# ── Catálogo de métodos de pago (scripts/seed_payment_methods.py) ──────


async def test_seed_payment_methods_upserts_idempotently(db):
    from scripts.seed_payment_methods import seed_payment_methods

    first = seed_payment_methods(db)
    assert first["total"] == 3
    assert first["inserted"] == 3

    second = seed_payment_methods(db)
    assert second["total"] == 3
    assert second["inserted"] == 0
    assert second["updated"] == 3

    method = db.payment_methods.find_one({"code": "bank_transfer"})
    assert method["label"]
    assert method["is_active"] is True


async def test_seed_payment_methods_dry_run_does_not_write(db):
    from scripts.seed_payment_methods import seed_payment_methods

    result = seed_payment_methods(db, dry_run=True)
    assert result["inserted"] == 3
    assert db.payment_methods.count_documents({}) == 0


# ── Override programado (preaviso, PLAN §12 edge 6 / §6.4) ────────────


async def test_override_active_schedules_for_next_cycle(db):
    """En ``active`` el override no se aplica a mitad de ciclo: se programa."""
    sub = _make(db, prop_id=9, band=3, price=149)
    _advance_to_active(db, sub["_id"])

    svc.override_subscription(
        db, prop_id=9, price_band=4, price_usd=229, notes="Sube a Grande", changed_by="admin_test"
    )

    fresh = db.subscriptions.find_one({"prop_id": 9})
    # Banda y precio actuales intactos (nunca se cambia a mitad de ciclo sin aviso).
    assert fresh["band"] == 3
    assert fresh["price_usd"] == 149
    # Programado para el siguiente ciclo.
    assert fresh["pending_price_band"] == 4
    assert fresh["pending_price_usd"] == 229
    assert fresh["price_band_override"] is True
    assert fresh["approval_notes"] == "Sube a Grande"


async def test_override_active_applies_on_next_emit_invoice(db):
    """El override programado se aplica al emitir la factura del ciclo siguiente."""
    sub = _make(db, prop_id=10, band=3, price=149)
    _advance_to_active(db, sub["_id"])
    db.pricing_plans.insert_one(
        {
            "band": 4,
            "label": "Grande",
            "min_rooms": 51,
            "max_rooms": 300,
            "monthly_usd": 229,
            "annual_monthly_usd": 169,
            "is_active": True,
        }
    )
    svc.override_subscription(db, prop_id=10, price_band=4, price_usd=229, changed_by="admin_test")

    # A mitad de ciclo la banda/precio actuales no cambian todavía.
    intermediate = db.subscriptions.find_one({"prop_id": 10})
    assert intermediate["band"] == 3
    assert intermediate["price_usd"] == 149
    assert intermediate["pending_price_band"] == 4
    assert intermediate["pending_price_usd"] == 229

    inv = svc.emit_invoice(db, subscription_id=sub["_id"])

    fresh = db.subscriptions.find_one({"prop_id": 10})
    assert fresh["band"] == 4
    assert fresh["band_label"] == "Grande"
    assert fresh["price_usd"] == 229
    # Los campos pendientes quedan consumidos tras aplicarse.
    assert fresh.get("pending_price_band") is None
    assert fresh.get("pending_price_usd") is None
    # La factura del nuevo ciclo ya factura el precio programado.
    assert inv["amount_usd"] == 229


async def test_override_active_band_only_keeps_negotiated_price(db):
    """Override de solo banda programa la banda y conserva el precio negociado."""
    sub = _make(db, prop_id=11, band=3, price=149)
    _advance_to_active(db, sub["_id"])

    svc.override_subscription(db, prop_id=11, price_band=4, changed_by="admin_test")

    intermediate = db.subscriptions.find_one({"prop_id": 11})
    assert intermediate["band"] == 3
    assert intermediate["pending_price_band"] == 4

    inv = svc.emit_invoice(db, subscription_id=sub["_id"])

    fresh = db.subscriptions.find_one({"prop_id": 11})
    assert fresh["band"] == 4
    # Sin price_usd en el override, el precio actual se conserva.
    assert fresh["price_usd"] == 149
    assert inv["amount_usd"] == 149


async def test_override_non_active_applies_immediately(db):
    """Antes del primer ciclo (``pending_payment``) el override sigue siendo inmediato."""
    _make(db, prop_id=12, band=3, price=149)

    svc.override_subscription(db, prop_id=12, price_band=4, price_usd=229, changed_by="admin_test")

    fresh = db.subscriptions.find_one({"prop_id": 12})
    assert fresh["band"] == 4
    assert fresh["price_usd"] == 229
    assert fresh.get("pending_price_band") is None
    assert fresh.get("pending_price_usd") is None
