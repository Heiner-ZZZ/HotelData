"""Notificación al huésped cuando recepción declara una llegada tardía.

Spec: cuando la recepción declara una llegada tardía (``declared_late_arrival``
= True), el pipeline de notificaciones existente escribe una fila
``notification_type="guest_late_arrival"`` en ``notification_log`` (la campanita
del huésped vía ``GET /api/notifications/my``) y envía un email best-effort con
la fecha de check-in y la hora estimada de llegada.

Reglas:
- Solo al DECLARAR (declared=True); retirar la declaración no notifica.
- Solo si la reserva tiene ``guest_email`` y no es ``is_test``.
- La fila queda ``status="sent"`` (entregada a la campanita = no leída) y el
  resultado del correo se registra aparte en ``email_status``.
"""
from __future__ import annotations

import pytest

from src.app.modules.reservations.service.late_arrival import declare_late_arrival

pytestmark = pytest.mark.asyncio


def _seed_booking(db, booking_id: str = "BK-LA-NOTIF", **extra) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 991,
        "guest_name": "Late Arrival Guest",
        "guest_email": "late@test.com",
        "status": "confirmed",
        "check_in_date": "2026-08-14",
        "check_out_date": "2026-08-16",
        "total_nights": 2,
        "currency": "USD",
        "is_test": False,
    }
    doc.update(extra)
    db.booking_orders.insert_one(doc)


def _rows(db, booking_id: str = "BK-LA-NOTIF"):
    return list(
        db.notification_log.find(
            {"booking_id": booking_id, "notification_type": "guest_late_arrival"}
        )
    )


# ── Función unitaria: fila en notification_log + email ──────────────────


async def test_notify_writes_bell_row_and_sends_email(monkeypatch, db) -> None:
    """Declarar llegada tardía escribe la fila en la campanita y envía el email."""
    _seed_booking(db)
    db.dim_hotels.insert_one({"prop_id": 991, "display_name": "Hotel Test"})

    captured: dict = {}

    def _fake_send_email(to, subject, html):
        captured["to"] = to
        captured["subject"] = subject
        captured["html"] = html
        return True

    from src.app.modules.reservations.notifications import guest as guest_mod

    monkeypatch.setattr(guest_mod, "send_email", _fake_send_email)

    result = declare_late_arrival(
        db,
        "BK-LA-NOTIF",
        declared=True,
        estimated_arrival_time="01:30",
    )

    assert result["declared_late_arrival"] is True
    rows = _rows(db)
    assert len(rows) == 1
    row = rows[0]
    assert row["recipient_email"] == "late@test.com"
    assert row["recipient_name"] == "Late Arrival Guest"
    assert row["prop_id"] == 991
    assert row["status"] == "sent"
    assert row["email_status"] == "sent"
    assert "01:30" in row["message"]
    assert "2026-08-14" in row["message"]
    assert captured["to"] == "late@test.com"
    assert "Llegada tardía" in captured["subject"]
    assert "01:30" in captured["html"]


async def test_notify_survives_email_failure(monkeypatch, db) -> None:
    """Un fallo del correo no impide la fila de la campanita (best-effort)."""
    _seed_booking(db)

    def _boom(to, subject, html):
        raise RuntimeError("SMTP down")

    from src.app.modules.reservations.notifications import guest as guest_mod

    monkeypatch.setattr(guest_mod, "send_email", _boom)

    declare_late_arrival(db, "BK-LA-NOTIF", declared=True, estimated_arrival_time="02:00")

    rows = _rows(db)
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert rows[0]["email_status"] == "error"
    assert "SMTP down" in rows[0]["error_message"]


async def test_notify_skipped_without_guest_email(db) -> None:
    """Reserva sin guest_email → no se notifica ni se escribe fila."""
    _seed_booking(db, guest_email="")
    declare_late_arrival(db, "BK-LA-NOTIF", declared=True)
    assert _rows(db) == []


async def test_notify_skipped_for_test_booking(db) -> None:
    """Reserva is_test=True → no se notifica (protege datos de prueba)."""
    _seed_booking(db, is_test=True)
    declare_late_arrival(db, "BK-LA-NOTIF", declared=True)
    assert _rows(db) == []


# ── Integración con la declaración ──────────────────────────────────────


async def test_declare_triggers_notification_but_withdraw_does_not(db) -> None:
    """Declarar notifica; retirar la declaración no genera nueva notificación."""
    _seed_booking(db)
    db.dim_hotels.insert_one({"prop_id": 991, "display_name": "Hotel Test"})

    from src.app.modules.reservations.notifications import guest as guest_mod

    monkeypatch_sent = {"count": 0}

    def _fake_send_email(to, subject, html):
        monkeypatch_sent["count"] += 1
        return True

    import pytest as _pytest

    _pytest.MonkeyPatch().setattr(guest_mod, "send_email", _fake_send_email)

    # Declarar → notifica.
    declare_late_arrival(db, "BK-LA-NOTIF", declared=True)
    assert len(_rows(db)) == 1
    assert monkeypatch_sent["count"] == 1

    # Retirar → NO notifica (ni fila nueva ni email).
    declare_late_arrival(db, "BK-LA-NOTIF", declared=False)
    assert len(_rows(db)) == 1
    assert monkeypatch_sent["count"] == 1


async def test_declare_via_route_writes_guest_notification(client, admin_user, db) -> None:
    """La ruta HTTP de declaración dispara la notificación al huésped."""
    from tests.conftest import login

    _seed_booking(db)
    db.dim_hotels.insert_one({"prop_id": 991, "display_name": "Hotel Test"})
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.post(
        "/api/management/check-ins/BK-LA-NOTIF/declare-late-arrival?prop_id=991",
        json={"declared_late_arrival": True, "estimated_arrival_time": "01:45"},
    )

    assert response.status_code == 200
    rows = _rows(db)
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert "01:45" in rows[0]["message"]
