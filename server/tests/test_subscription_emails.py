"""Fase 7 — notificaciones de suscripción (docs/PLAN_SUSCRIPCION_Y_PAGOS.md §8).

Cubre el contrato best-effort de los 5 emails que faltaban tras las Fases 2–5
(el `subscription_first_invoice` ya viaja dentro de `registration_approved`
con el bloque de pago):

- `submit_payment`   → `subscription_payment_received`
- `verify_payment`   → `subscription_payment_verified`
- `reject_payment`   → `subscription_payment_rejected` (motivo, nunca genérico)
- `mark_overdue`     → `subscription_overdue`
- `suspend`          → `subscription_suspended`

Dos capas bajo prueba:

1. **Capa de servicio**: cada transición invoca la función `notify_*` correcta
   con el email del dueño, nombre del hotel y datos del período (monkeypatch de
   `svc.notify_*` — no se toca SMTP).
2. **Capa de notificación**: `notify_*` arma el asunto + HTML vía `send_email`,
   ignora emails vacíos y **nunca** propaga un fallo de SMTP (la transición ya
   ocurrió y no debe romperse).
"""

from __future__ import annotations

import pytest
from bson import ObjectId

from src.app.modules.subscriptions import notifications
from src.app.modules.subscriptions import service as svc

pytestmark = pytest.mark.asyncio


# ── Helpers ────────────────────────────────────────────────────────────


def _make_owner(db, email="owner@example.com") -> ObjectId:
    return db.users.insert_one(
        {"username": "owner_test", "email": email, "is_active": True}
    ).inserted_id


def _make_hotel(db, prop_id=1, name="Hotel Lima Centro") -> None:
    db.dim_hotels.insert_one({"prop_id": prop_id, "hotel_name": name})


def _make_sub(db, *, prop_id=1, band=3, price=149) -> dict:
    owner_id = _make_owner(db)
    _make_hotel(db, prop_id=prop_id, name="Hotel Lima Centro")
    return svc.create_subscription(
        db,
        prop_id=prop_id,
        owner_user_id=owner_id,
        band=band,
        price_usd=price,
    )


def _record_spy(calls: list):
    def spy(email, *, hotel_name, **kwargs):
        calls.append({"email": email, "hotel_name": hotel_name, **kwargs})

    return spy


# ── Capa de servicio: cada transición notifica ────────────────────────


async def test_submit_payment_notifies_payment_received(db, monkeypatch):
    calls: list = []
    monkeypatch.setattr(svc, "notify_payment_received", _record_spy(calls))
    sub = _make_sub(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    svc.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        reference="TX-9",
        amount=149,
    )
    assert calls == [
        {
            "email": "owner@example.com",
            "hotel_name": "Hotel Lima Centro",
            "amount": 149,
            "reference": "TX-9",
        }
    ]


async def test_verify_payment_notifies_payment_verified(db, monkeypatch):
    calls: list = []
    monkeypatch.setattr(svc, "notify_payment_verified", _record_spy(calls))
    sub = _make_sub(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db, subscription_id=sub["_id"], invoice_id=inv["_id"],
        method="bank_transfer", amount=149,
    )
    svc.verify_payment(db, payment_id=pay["_id"])
    assert calls == [{"email": "owner@example.com", "hotel_name": "Hotel Lima Centro"}]


async def test_reject_payment_notifies_payment_rejected_with_reason(db, monkeypatch):
    calls: list = []
    monkeypatch.setattr(svc, "notify_payment_rejected", _record_spy(calls))
    sub = _make_sub(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db, subscription_id=sub["_id"], invoice_id=inv["_id"],
        method="bank_transfer", amount=149,
    )
    svc.reject_payment(db, payment_id=pay["_id"], reason="Comprobante ilegible")
    assert calls == [
        {
            "email": "owner@example.com",
            "hotel_name": "Hotel Lima Centro",
            "reason": "Comprobante ilegible",
        }
    ]


async def test_mark_overdue_notifies_overdue(db, monkeypatch):
    calls: list = []
    monkeypatch.setattr(svc, "notify_overdue", _record_spy(calls))
    sub = _make_sub(db)
    # pending → payment_submitted → active, luego renovación impaga → overdue.
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db, subscription_id=sub["_id"], invoice_id=inv["_id"],
        method="bank_transfer", amount=149,
    )
    svc.verify_payment(db, payment_id=pay["_id"])
    svc.emit_invoice(db, subscription_id=sub["_id"])
    svc.mark_overdue(db, subscription_id=sub["_id"])

    assert len(calls) == 1
    assert calls[0]["email"] == "owner@example.com"
    assert calls[0]["hotel_name"] == "Hotel Lima Centro"
    assert calls[0]["amount"] == 149
    assert calls[0]["due_date"] is not None


async def test_suspend_notifies_suspended(db, monkeypatch):
    calls: list = []
    monkeypatch.setattr(svc, "notify_suspended", _record_spy(calls))
    sub = _make_sub(db)
    inv = svc.emit_invoice(db, subscription_id=sub["_id"])
    pay = svc.submit_payment(
        db, subscription_id=sub["_id"], invoice_id=inv["_id"],
        method="bank_transfer", amount=149,
    )
    svc.verify_payment(db, payment_id=pay["_id"])
    svc.emit_invoice(db, subscription_id=sub["_id"])
    svc.mark_overdue(db, subscription_id=sub["_id"])
    svc.suspend(db, subscription_id=sub["_id"])

    assert len(calls) == 1
    assert calls[0]["email"] == "owner@example.com"
    assert calls[0]["hotel_name"] == "Hotel Lima Centro"
    assert calls[0]["amount"] == 149


# ── Capa de notificación: asunto + HTML + best-effort ─────────────────


async def test_notify_payment_received_sends_email(db, monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        notifications, "send_email", lambda to, subject, html: sent.append((to, subject, html))
    )
    notifications.notify_payment_received(
        "owner@example.com", hotel_name="Hotel Lima Centro", amount=149, reference="TX-9"
    )
    assert len(sent) == 1
    to, subject, html = sent[0]
    assert to == "owner@example.com"
    assert subject == notifications.SUBJECT_PAYMENT_RECEIVED
    assert "Hotel Lima Centro" in html
    assert "149" in html


async def test_notify_payment_verified_sends_email(db, monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        notifications, "send_email", lambda to, subject, html: sent.append((to, subject, html))
    )
    notifications.notify_payment_verified("owner@example.com", hotel_name="Hotel Lima Centro")
    assert len(sent) == 1
    assert sent[0][1] == notifications.SUBJECT_PAYMENT_VERIFIED
    assert "Hotel Lima Centro" in sent[0][2]


async def test_notify_payment_rejected_includes_reason(db, monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        notifications, "send_email", lambda to, subject, html: sent.append((to, subject, html))
    )
    notifications.notify_payment_rejected(
        "owner@example.com", hotel_name="Hotel Lima Centro", reason="Monto no coincide"
    )
    assert len(sent) == 1
    assert sent[0][1] == notifications.SUBJECT_PAYMENT_REJECTED
    assert "Monto no coincide" in sent[0][2]


async def test_notify_overdue_includes_due_date(db, monkeypatch):
    from datetime import datetime, UTC

    sent: list = []
    monkeypatch.setattr(
        notifications, "send_email", lambda to, subject, html: sent.append((to, subject, html))
    )
    notifications.notify_overdue(
        "owner@example.com",
        hotel_name="Hotel Lima Centro",
        amount=149,
        due_date=datetime(2026, 9, 15, tzinfo=UTC),
    )
    assert len(sent) == 1
    assert sent[0][1] == notifications.SUBJECT_OVERDUE
    assert "15" in sent[0][2]


async def test_notify_suspended_sends_email(db, monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        notifications, "send_email", lambda to, subject, html: sent.append((to, subject, html))
    )
    notifications.notify_suspended("owner@example.com", hotel_name="Hotel Lima Centro", amount=149)
    assert len(sent) == 1
    assert sent[0][1] == notifications.SUBJECT_SUSPENDED
    assert "Hotel Lima Centro" in sent[0][2]


async def test_notify_swallows_send_email_failure(db, monkeypatch):
    """Un fallo de SMTP loguea y NO propaga — la transición ya ocurrió."""

    def boom(*args, **kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(notifications, "send_email", boom)
    # No debe levantar.
    notifications.notify_payment_received("owner@example.com", hotel_name="Hotel Lima Centro", amount=149)


async def test_notify_skips_empty_email(db, monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        notifications, "send_email", lambda *a, **k: sent.append(a)
    )
    notifications.notify_payment_received("", hotel_name="Hotel Lima Centro", amount=149)
    assert sent == []
