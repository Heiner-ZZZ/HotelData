"""El centro de notificaciones (campanita) del equipo ve las broadcasts.

Las notificaciones operativas sin destinatario (``recipient_email`` vacío:
``housekeeping_check_in``, ``late_checkout_approved``, ``late_checkout_courtesy``,
``early_checkin_approved``, ``early_checkin_courtesy``) se escriben en
``notification_log`` para el equipo (recepción/housekeeping). ``GET
/api/admin/notifications`` las devuelve a los roles STAFF (no clientes):

- super_admin/admin_sistema (``users.manage``) ya veían todo el log.
- El resto de staff (recepcionista, gerente_hotel, housekeeping…) ahora ve sus
  notificaciones personales (por email) MÁS las broadcasts operativas.
- Los clientes (``cliente``) solo ven sus personales — nunca las operativas.

Regresión: no filtrar ``recipient_email`` con ``$or`` rompe la visibilidad de
los emails con caracteres regex (se usa ``re.escape``).
"""
from __future__ import annotations

import pytest

from tests.conftest import _seed_user, login


def _seed_notification(db, *, notification_type: str, recipient_email: str, entity_id: str) -> None:
    db.notification_log.insert_one(
        {
            "notification_type": notification_type,
            "entity_type": "booking",
            "entity_id": entity_id,
            "prop_id": 1,
            "recipient_email": recipient_email,
            "message": f"test {notification_type}",
            "status": "sent",
            "created_at": None,
        }
    )


@pytest.fixture
def receptionist_user(db):
    """A recepcionista user (staff sin ``users.manage``)."""
    return _seed_user(
        db,
        username="recepcion_broadcast",
        email="recepcion.broadcast@hoteldata.local",
        password="RecepPass123!",
        role="recepcionista",
    )


@pytest.fixture
def guest_user(db):
    """A cliente user (no staff — nunca ve broadcasts)."""
    return _seed_user(
        db,
        username="cliente_broadcast",
        email="cliente.broadcast@hoteldata.local",
        password="ClientePass123!",
        role="cliente",
    )


@pytest.mark.asyncio
async def test_receptionist_sees_broadcast_late_checkout_notification(client, receptionist_user, db):
    """El equipo (recepcionista) ve la notificación ``late_checkout_approved``
    broadcast en el centro de notificaciones, no solo en el log de admin."""
    _seed_notification(
        db,
        notification_type="late_checkout_approved",
        recipient_email="",
        entity_id="BK-LC-BROADCAST",
    )
    _seed_notification(
        db,
        notification_type="shift_expired",
        recipient_email=receptionist_user["email"],
        entity_id="BK-PERSONAL",
    )

    assert await login(client, receptionist_user["username"], receptionist_user["password"]) == 200
    response = await client.get("/api/admin/notifications")
    assert response.status_code == 200

    payload = response.json()
    types = {item["notification_type"] for item in payload["items"]}
    # Personal (email) + broadcast operativa (sin destinatario).
    assert "shift_expired" in types
    assert "late_checkout_approved" in types


@pytest.mark.asyncio
async def test_courtesy_broadcast_also_reachable_by_staff(client, receptionist_user, db):
    """La cortesía (``late_checkout_courtesy``) también llega al equipo."""
    _seed_notification(
        db,
        notification_type="late_checkout_courtesy",
        recipient_email="",
        entity_id="BK-LC-COURTESY-BROADCAST",
    )

    assert await login(client, receptionist_user["username"], receptionist_user["password"]) == 200
    response = await client.get("/api/admin/notifications")
    assert response.status_code == 200

    payload = response.json()
    types = {item["notification_type"] for item in payload["items"]}
    assert "late_checkout_courtesy" in types


@pytest.mark.asyncio
async def test_guest_never_sees_broadcast_operational_notifications(client, guest_user, db):
    """Un cliente NO ve las broadcasts operativas — solo sus personales."""
    _seed_notification(
        db,
        notification_type="late_checkout_approved",
        recipient_email="",
        entity_id="BK-LC-GUEST-LOCKED",
    )
    _seed_notification(
        db,
        notification_type="guest_confirmed",
        recipient_email=guest_user["email"],
        entity_id="BK-GUEST-PERSONAL",
    )

    assert await login(client, guest_user["username"], guest_user["password"]) == 200
    response = await client.get("/api/admin/notifications")
    assert response.status_code == 200

    payload = response.json()
    types = {item["notification_type"] for item in payload["items"]}
    assert "guest_confirmed" in types
    assert "late_checkout_approved" not in types


@pytest.mark.asyncio
async def test_regex_special_chars_in_email_are_escaped(client, receptionist_user, db):
    """El email del staff se escapa en la regex (un punto no matchea todo)."""
    _seed_notification(
        db,
        notification_type="guest_other",
        recipient_email="recepción.broadcastX@hoteldata.local",
        entity_id="BK-NO-MATCH",
    )

    assert await login(client, receptionist_user["username"], receptionist_user["password"]) == 200
    response = await client.get("/api/admin/notifications")
    assert response.status_code == 200

    payload = response.json()
    ids = {item.get("entity_id") for item in payload["items"]}
    assert "BK-NO-MATCH" not in ids
