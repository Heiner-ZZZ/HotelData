"""Reservation email notifications — the "Total" row must never show "—"
when the booking price is derivable.

Spec: las notificaciones de correo al huésped (confirmada, rechazada,
cancelada, modificada, check-in, check-out, no-show) muestran un resumen con
``Total``. Cuando una reserva se creó sin precio (p. ej. el
``hotel_rate_calendar`` no tenía filas para sus fechas), los llamadores pasan
``total_price=None`` y el email renderiza "—".

El resolver ``_resolve_booking_total`` prioriza fuentes autoritativas:
  1. el total ya pasado por el llamador,
  2. ``booking_orders.total_price``,
  3. ``booking_orders.original_total_price``,
  4. el ``base_rate`` del rate plan que la reserva referencia explícitamente
     (``rate_plan_id``) × noches × habitaciones,
  5. ``None`` → el email muestra "—" (nunca se inventa un precio).

Tests del contrato completo + render del HTML vía ``notify_guest_status_change``.
"""
from __future__ import annotations

import pytest

from src.app.modules.reservations.notifications.guest import (
    _resolve_booking_total,
    notify_guest_status_change,
)

pytestmark = pytest.mark.asyncio


def _seed_booking(db, **overrides) -> str:
    doc = {
        "booking_id": "BK-NOTIF-0001",
        "prop_id": 1,
        "guest_name": "Horuz",
        "guest_email": "horuz@example.com",
        "status": "pending",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-08",
        "total_nights": 7,
        "rooms": 1,
        "currency": "USD",
        "rate_plan_id": "",
        "total_price": None,
        "original_total_price": None,
    }
    doc.update(overrides)
    db.booking_orders.insert_one(doc)
    return doc["booking_id"]


# ── Resolver: prioridad de fuentes ──────────────────────────────────────


async def test_resolver_prefers_passed_total(db):
    """Un total válido pasado por el llamador manda sobre la BD."""
    _seed_booking(db, total_price=None)
    assert _resolve_booking_total(db, "BK-NOTIF-0001", 450.0) == 450.0


async def test_resolver_uses_booking_total_price_when_passed_none(db):
    """Llamador pasa None pero la reserva SÍ tiene total_price → lo usa."""
    _seed_booking(db, total_price=763.0)
    assert _resolve_booking_total(db, "BK-NOTIF-0001", None) == 763.0


async def test_resolver_falls_back_to_original_total_price(db):
    """Sin total_price, usa original_total_price (pre-descuento)."""
    _seed_booking(db, total_price=None, original_total_price=900.0)
    assert _resolve_booking_total(db, "BK-NOTIF-0001", None) == 900.0


async def test_resolver_computes_from_rate_plan_base_rate(db):
    """Sin precio almacenado, deriva del rate plan que la reserva referencia:
    base_rate × noches × habitaciones."""
    db.rate_plans.insert_one({"rate_plan_id": "RP-1-flex", "base_rate": 109.0})
    _seed_booking(db, rate_plan_id="RP-1-flex", total_nights=7, rooms=2)
    assert _resolve_booking_total(db, "BK-NOTIF-0001", None) == 109.0 * 7 * 2


async def test_resolver_ignores_zero_and_negative_totals(db):
    """Totales 0/negativos no cuentan como precio real."""
    _seed_booking(db, total_price=0.0, original_total_price=-1.0)
    assert _resolve_booking_total(db, "BK-NOTIF-0001", None) is None


async def test_resolver_returns_none_when_no_price_anywhere(db):
    """Sin precio ni rate plan → None (el email renderiza '—', no inventa)."""
    _seed_booking(db)
    assert _resolve_booking_total(db, "BK-NOTIF-0001", None) is None


# ── Render del email: el HTML lleva el Total ─────────────────────────────


async def test_notify_guest_status_change_renders_total(monkeypatch, db):
    """Un email de confirmación con reserva con precio muestra el total y NO '—'."""
    _seed_booking(db, total_price=763.0)
    db.dim_hotels.insert_one({"prop_id": 1, "display_name": "Hotel Lima Centro"})

    captured: dict = {}
    from src.app.modules.reservations.notifications import guest as guest_mod

    def _fake_send_email(to, subject, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["html"] = html
        return True

    monkeypatch.setattr(guest_mod, "send_email", _fake_send_email)

    notify_guest_status_change(
        booking_id="BK-NOTIF-0001",
        guest_name="Horuz",
        guest_email="horuz@example.com",
        new_status="confirmed",
        prop_id=1,
        check_in_date="2026-08-01",
        check_out_date="2026-08-08",
        total_price=None,  # el llamador no lo pasa → el resolver lo recupera
        currency="USD",
        total_nights=7,
    )

    assert captured["subject"] == "Reserva confirmada — BK-NOTIF-0001"
    assert "Total" in captured["html"]
    # El formato del Total es "763.00 USD" (sin $) — consistente con el diseño actual.
    assert "763.00 USD" in captured["html"]
    assert ">—<" not in captured["html"]


async def test_notify_guest_status_change_renders_dash_only_without_price(monkeypatch, db):
    """Sin ningún dato de precio, el email muestra '—' (honesto, no fabrica)."""
    _seed_booking(db)
    db.dim_hotels.insert_one({"prop_id": 1, "display_name": "Hotel Lima Centro"})

    captured: dict = {}
    from src.app.modules.reservations.notifications import guest as guest_mod

    def _fake_send_email(to, subject, html):
        captured["html"] = html
        return True

    monkeypatch.setattr(guest_mod, "send_email", _fake_send_email)

    notify_guest_status_change(
        booking_id="BK-NOTIF-0001",
        guest_name="Horuz",
        guest_email="horuz@example.com",
        new_status="no_show",
        prop_id=1,
        check_in_date="2026-08-01",
        check_out_date="2026-08-08",
        total_price=None,
        currency="USD",
        total_nights=7,
    )
    assert ">—<" in captured["html"]


async def test_notify_staff_new_booking_renders_recipient_name(monkeypatch, db):
    """El correo al staff debe saludar al nombre real, nunca al placeholder."""
    db.users.insert_one({
        "username": "socio.gta6",
        "display_name": "Socio GTA6",
        "email": "socio@example.com",
        "primary_role": "gerente_hotel",
        "is_active": True,
        "assigned_hotels": [1],
    })
    db.dim_hotels.insert_one({"prop_id": 1, "display_name": "Hotel Lima Centro"})

    captured: dict = {}
    from src.app.modules.reservations.notifications import staff as staff_mod

    def _fake_send_email(to, subject, html):
        captured.update(to=to, subject=subject, html=html)
        return True

    monkeypatch.setattr(staff_mod, "send_email", _fake_send_email)

    staff_mod.notify_staff_new_booking(
        prop_id=1,
        booking_id="BK-NOTIF-STAFF-0001",
        guest_name="Prueba Llegada Tarde",
        guest_email="late@test.com",
        check_in_date="2026-08-09",
        check_out_date="2026-08-11",
        adults=2,
        children=0,
        rooms=1,
        total_price=218.0,
        currency="USD",
        total_nights=2,
        comment="E2E late checkin",
    )

    assert captured["to"] == "socio@example.com"
    assert "Socio GTA6" in captured["html"]
    assert "{STAFF_NAME}" not in captured["html"]
