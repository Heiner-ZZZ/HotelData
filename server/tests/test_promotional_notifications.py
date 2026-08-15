"""Promotional notifications (marketing opt-in) — ``guest_promotional``.

Spec (Fase 2 del consentimiento de marketing — sección "Publicidad y
promociones" del perfil del huésped):

- El flag ``marketing_opt_in`` del perfil controla si el huésped recibe
  comunicaciones promocionales (publicidad, promociones, novedades, ofertas).
- ``send_promotion`` escribe filas ``notification_type="guest_promotional"``
  en ``notification_log`` SOLO para usuarios con rol ``cliente`` y
  ``marketing_opt_in=True``. Un huésped sin opt-in NUNCA recibe la fila.
- Las notificaciones transaccionales (``guest_*`` de reservations) NO se
  tocan: siguen saliendo siempre y con sus propios tipos.
- El endpoint ``POST /api/notifications/promotions`` exige
  ``promotions.manage`` y valida título + mensaje.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from passlib.context import CryptContext

from src.app.modules.notifications import promotions as promos
from src.app.modules.revenue.services.promotions import create_promotion_campaign
from tests.conftest import login

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_user(
    db,
    *,
    username: str,
    email: str,
    role: str = "cliente",
    marketing_opt_in: bool = False,
    role_id: ObjectId | None = None,
    assigned_hotels: list[int] | None = None,
) -> ObjectId:
    doc = {
        "username": username,
        "email": email,
        "display_name": username.replace("_", " ").title(),
        "password_hash": _pwd.hash("Pass123!"),
        "primary_role": role,
        "is_active": True,
        "marketing_opt_in": marketing_opt_in,
        "created_at": _now(),
    }
    if role_id is not None:
        doc["primary_role_id"] = role_id
    if assigned_hotels is not None:
        doc["assigned_hotels"] = assigned_hotels
    return db.users.insert_one(doc).inserted_id


def _seed_cliente_role(db, *, permissions: list[str] | None = None) -> ObjectId:
    return db.roles.insert_one(
        {
            "role_name": "cliente",
            "display_name": "Cliente",
            "permissions": permissions or ["account.read", "search.read"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id


def _seed_marketing_role(db) -> ObjectId:
    return db.roles.insert_one(
        {
            "role_name": "marketing_hotelero",
            "display_name": "Marketing Hotelero",
            "permissions": ["promotions.manage", "promotions.read", "dashboard.read"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id


def _seed_hotel(db, prop_id: int = 1) -> None:
    db.dim_hotels.insert_one(
        {"prop_id": prop_id, "display_name": f"Hotel Lima Centro {prop_id}"}
    )


def _promo_rows(db) -> list[dict]:
    return list(db.notification_log.find({"notification_type": "guest_promotional"}))


# ── send_promotion: solo huéspedes con opt-in ────────────────────────────


async def test_send_promotion_targets_only_opted_in_guests(db, monkeypatch):
    _seed_cliente_role(db)
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    _seed_user(db, username="huesped_sin_optin", email="nooptin@example.com", marketing_opt_in=False)
    # Staff con opt-in marcado NO es huésped — no debe recibir nada.
    _seed_user(db, username="gerente_marketing", email="gerente@example.com",
               role="gerente_hotel", marketing_opt_in=True)

    captured: list[tuple] = []
    monkeypatch.setattr(
        promos, "send_email", lambda to, subject, html: captured.append((to, subject, html)) or True
    )

    result = promos.send_promotion(title="Oferta de verano", message="20% off en tu próxima estadía.")

    rows = _promo_rows(db)
    assert result["sent"] == 1
    assert result["recipients"] == ["optin@example.com"]
    assert len(rows) == 1
    assert rows[0]["recipient_email"] == "optin@example.com"
    assert rows[0]["recipient_name"] == "Huesped Optin"
    assert rows[0]["notification_type"] == "guest_promotional"
    assert rows[0]["status"] == "sent"
    assert rows[0]["title"] == "Oferta de verano"
    assert rows[0]["message"] == "20% off en tu próxima estadía."
    # El gerente (staff) no recibe promoción aunque tenga opt-in.
    assert all(r["recipient_email"] != "gerente@example.com" for r in rows)


async def test_send_promotion_never_touches_transactional_types(db, monkeypatch):
    """Sin tocar guest_confirmed/guest_invoice_issued: el servicio solo escribe
    guest_promotional (el log transaccional se mantiene intacto)."""
    _seed_cliente_role(db)
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    # Fila transaccional preexistente (simula notificaciones de reserva).
    db.notification_log.insert_one(
        {
            "notification_type": "guest_confirmed",
            "recipient_email": "optin@example.com",
            "recipient_name": "Huesped Optin",
            "booking_id": "BK-0001",
            "prop_id": 1,
            "status": "sent",
            "created_at": _now(),
        }
    )

    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    promos.send_promotion(title="Novedades", message="Nuevo spa en el hotel.")

    types = {r["notification_type"] for r in db.notification_log.find({})}
    assert types == {"guest_confirmed", "guest_promotional"}
    # La fila transaccional no fue modificada ni re-enviada.
    assert db.notification_log.count_documents({"notification_type": "guest_confirmed"}) == 1


async def test_send_promotion_respects_prop_scope(db, monkeypatch):
    """Con prop_id, solo huéspedes con reserva en ese hotel (hoteles asociados)."""
    _seed_cliente_role(db)
    optin_prop1 = _seed_user(db, username="optin_p1", email="p1@example.com", marketing_opt_in=True)
    _seed_user(db, username="optin_p2", email="p2@example.com", marketing_opt_in=True)
    _seed_user(db, username="optin_sin_booking", email="sin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-P1-0001",
            "prop_id": 1,
            "guest_email": "p1@example.com",
            "status": "confirmed",
            "created_at": _now(),
        }
    )
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-P2-0001",
            "prop_id": 2,
            "guest_email": "p2@example.com",
            "status": "confirmed",
            "created_at": _now(),
        }
    )

    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    result = promos.send_promotion(
        title="Solo hotel 1", message="Promo exclusiva Hotel Lima Centro.", prop_id=1
    )

    assert result["recipients"] == ["p1@example.com"]
    rows = _promo_rows(db)
    assert len(rows) == 1
    assert rows[0]["recipient_email"] == "p1@example.com"
    assert rows[0]["prop_id"] == 1


async def test_send_promotion_handles_fk_role_users(db, monkeypatch):
    """Usuarios con rol por FK (primary_role_id) también se detectan."""
    role_id = _seed_cliente_role(db)
    _seed_user(db, username="optin_fk", email="fk@example.com", marketing_opt_in=True, role_id=role_id)

    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    result = promos.send_promotion(title="Novedades", message="Un mensaje promocional.")

    assert result["recipients"] == ["fk@example.com"]


async def test_send_promotion_skips_users_without_email(db, monkeypatch):
    _seed_cliente_role(db)
    _seed_user(db, username="con_email", email="con@example.com", marketing_opt_in=True)
    db.users.insert_one(
        {
            "username": "sin_email",
            "email": "",
            "display_name": "Sin Email",
            "primary_role": "cliente",
            "marketing_opt_in": True,
            "is_active": True,
            "created_at": _now(),
        }
    )

    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    result = promos.send_promotion(title="Novedades", message="Un mensaje promocional.")

    assert result["recipients"] == ["con@example.com"]
    assert all(r["recipient_email"] == "con@example.com" for r in _promo_rows(db))


# ── Endpoint POST /api/notifications/promotions ─────────────────────────


async def test_endpoint_requires_promotions_manage(client, db, admin_user, cliente_user):
    # El huésped NO tiene promotions.manage → 403.
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.post(
        "/api/notifications/promotions",
        json={"title": "Oferta", "message": "20% off en tu próxima estadía."},
    )
    assert resp.status_code == 403, resp.text
    assert _promo_rows(db) == []


async def test_endpoint_sends_promotion_as_marketing(client, db, monkeypatch):
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    # El scope por hotel (prop_id) exige una reserva del huésped en ese hotel.
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-P1-0002",
            "prop_id": 1,
            "guest_email": "optin@example.com",
            "status": "confirmed",
            "created_at": _now(),
        }
    )
    marketing_id = _seed_user(
        db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero"
    )
    db.users.update_one({"_id": marketing_id}, {"$set": {"password_hash": _pwd.hash("Pass123!")}})

    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.post(
        "/api/notifications/promotions",
        json={"title": "Oferta de verano", "message": "20% off en tu próxima estadía.", "prop_id": 1},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["notification_type"] == "guest_promotional"
    assert body["sent"] == 1
    assert body["recipients"] == ["optin@example.com"]

    rows = _promo_rows(db)
    assert len(rows) == 1
    assert rows[0]["recipient_email"] == "optin@example.com"


async def test_endpoint_validates_title_and_message(client, db, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json={"title": "", "message": "x"},
    )
    assert resp.status_code == 422, resp.text
    assert _promo_rows(db) == []


# ── Estimación de destinatarios (GET /api/notifications/promotions/estimate) ──


async def test_estimate_endpoint_requires_promotions_manage(client, db, cliente_user):
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.get("/api/notifications/promotions/estimate")
    assert resp.status_code == 403, resp.text


async def test_estimate_counts_opted_in_guests_for_prop(client, db, monkeypatch):
    """Con prop_id cuenta solo huéspedes con opt-in Y reserva en ese hotel."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero")
    _seed_user(db, username="optin_p1", email="p1@example.com", marketing_opt_in=True)
    _seed_user(db, username="optin_p2", email="p2@example.com", marketing_opt_in=True)
    _seed_user(db, username="sin_optin_p1", email="no@example.com", marketing_opt_in=False)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "p1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 1, "guest_email": "no@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-3", "prop_id": 2, "guest_email": "p2@example.com"})

    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.get("/api/notifications/promotions/estimate?prop_id=1")
    assert resp.status_code == 200, resp.text
    assert resp.json()["count"] == 1  # solo p1 (opt-in + reserva en prop 1)


async def test_estimate_total_without_prop(client, db, monkeypatch):
    """Sin prop_id cuenta todos los huéspedes con opt-in del sistema."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero")
    _seed_user(db, username="optin_a", email="a@example.com", marketing_opt_in=True)
    _seed_user(db, username="optin_b", email="b@example.com", marketing_opt_in=True)
    _seed_user(db, username="no_optin", email="c@example.com", marketing_opt_in=False)

    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.get("/api/notifications/promotions/estimate")
    assert resp.status_code == 200, resp.text
    assert resp.json()["count"] == 2


# ── Historial de envíos (campaign_id + GET /api/notifications/promotions/history) ──


async def test_send_promotion_stamps_distinct_campaign_id_per_batch(db, monkeypatch):
    """Cada envío tiene su propio campaign_id; dos envíos no comparten."""
    _seed_cliente_role(db)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    promos.send_promotion(title="Promo A", message="Mensaje A de prueba para el historial.")
    promos.send_promotion(title="Promo B", message="Mensaje B de prueba para el historial.")

    rows = _promo_rows(db)
    assert len(rows) == 4  # 2 envíos × 2 destinatarios
    ids = {r["campaign_id"] for r in rows}
    assert len(ids) == 2  # un campaign_id distinto por envío
    assert all(cid.startswith("PROMO-") for cid in ids)


async def test_send_promotion_shares_campaign_id_across_recipients(db, monkeypatch):
    """Todos los destinatarios de un mismo envío comparten el campaign_id
    (permite agrupar el historial por envío)."""
    _seed_cliente_role(db)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    promos.send_promotion(title="Promo", message="Mensaje compartido para el historial.")

    rows = _promo_rows(db)
    assert len(rows) == 2
    assert len({r["campaign_id"] for r in rows}) == 1


async def test_history_requires_promotions_manage(client, db, cliente_user):
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.get("/api/notifications/promotions/history")
    assert resp.status_code == 403, resp.text


async def test_history_groups_by_send_with_hotel_and_recipients(client, db, monkeypatch):
    """El historial agrupa los destinatarios por envío y enriquece hotel + count."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    _seed_hotel(db, 1)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 1, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Oferta verano", message="20% de descuento en tu próxima estadía.", prop_id=1)
    promos.send_promotion(title="Novedades spa", message="Nuevo spa con piscina climatizada en el hotel.", prop_id=1)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get("/api/notifications/promotions/history")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    item = body["items"][0]  # más reciente primero
    assert item["title"] == "Novedades spa"
    assert item["hotel_name"] == "Hotel Lima Centro 1"
    assert item["recipient_count"] == 2
    assert item["prop_id"] == 1
    assert item["campaign_id"].startswith("PROMO-")
    assert "sent_at_iso" in item


async def test_history_filters_by_prop_and_handles_legacy_rows(db, monkeypatch):
    """Filtro por prop_id + filas sin campaign_id (pre-migración) no rompen."""
    _seed_cliente_role(db)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    # El scope por hotel exige reserva del huésped en ese hotel.
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 2, "guest_email": "h2@example.com"})
    promos.send_promotion(title="Prop 1", message="Promoción para el hotel uno.", prop_id=1)
    promos.send_promotion(title="Prop 2", message="Promoción para el hotel dos.", prop_id=2)
    # Fila legacy sin campaign_id (escrita antes de esta feature).
    db.notification_log.insert_one({
        "notification_type": "guest_promotional",
        "recipient_email": "legacy@example.com",
        "recipient_name": "Legacy",
        "prop_id": 1,
        "status": "sent",
        "title": "Promo legacy",
        "message": "Mensaje legacy.",
        "created_at": _now(),
    })

    result = promos.list_promotion_history(db, prop_id=1)
    assert result["total"] == 2  # Prop 1 + legacy
    titles = {it["title"] for it in result["items"]}
    assert "Promo legacy" in titles
    assert "Prop 2" not in titles

    result_all = promos.list_promotion_history(db)
    assert result_all["total"] == 3


async def test_guest_sees_promotion_in_own_bell(client, db, monkeypatch):
    """La fila guest_promotional llega a /api/notifications/my del huésped con
    type_label humano ('Promoción') y el message."""
    _seed_cliente_role(db, permissions=["account.read", "search.read"])
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    db.users.update_one(
        {"username": "huesped_optin"}, {"$set": {"password_hash": _pwd.hash("Pass123!")}}
    )

    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Oferta de verano", message="20% off en tu próxima estadía.")

    assert await login(client, "huesped_optin", "Pass123!") == 200
    resp = await client.get("/api/notifications/my")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["notification_type"] == "guest_promotional"
    assert item["type_label"] == "Promoción"
    assert item["message"] == "20% off en tu próxima estadía."
    assert item["is_unread"] is True


# ── /api/notifications/my: filtro por tipo + paginación ───────────────────


def _seed_bell_row(db, *, ntype: str, email: str, created_at: datetime) -> None:
    db.notification_log.insert_one(
        {
            "notification_type": ntype,
            "recipient_email": email,
            "recipient_name": "Huesped",
            "booking_id": "",
            "prop_id": 1,
            "status": "sent",
            "title": f"Titulo {ntype} {created_at}",
            "message": f"Mensaje {ntype} {created_at.isoformat()}",
            "created_at": created_at,
        }
    )


async def test_my_notifications_filters_by_type(client, db, monkeypatch):
    """?notification_type= filtra la campanita por tipo (paginación limpia de
    promocionales sin traer las transaccionales del huésped)."""
    _seed_cliente_role(db, permissions=["account.read", "search.read"])
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    db.users.update_one(
        {"username": "huesped_optin"}, {"$set": {"password_hash": _pwd.hash("Pass123!")}}
    )
    now = _now()
    _seed_bell_row(db, ntype="guest_promotional", email="optin@example.com", created_at=now)
    _seed_bell_row(
        db, ntype="guest_confirmed", email="optin@example.com",
        created_at=now - timedelta(minutes=1),
    )
    _seed_bell_row(
        db, ntype="guest_invoice_issued", email="optin@example.com",
        created_at=now - timedelta(minutes=2),
    )

    assert await login(client, "huesped_optin", "Pass123!") == 200

    resp = await client.get("/api/notifications/my?notification_type=guest_promotional")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    assert body["items"][0]["notification_type"] == "guest_promotional"

    resp2 = await client.get("/api/notifications/my?notification_type=guest_confirmed")
    body2 = resp2.json()
    assert body2["total"] == 1
    assert body2["items"][0]["notification_type"] == "guest_confirmed"


async def test_my_notifications_type_filter_paginates(client, db, monkeypatch):
    """El filtro por tipo respeta page/page_size: 3 promos con page_size=2 →
    página 1 trae 2 y la 2 trae la restante."""
    _seed_cliente_role(db, permissions=["account.read", "search.read"])
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    db.users.update_one(
        {"username": "huesped_optin"}, {"$set": {"password_hash": _pwd.hash("Pass123!")}}
    )
    now = _now()
    for i in range(3):
        _seed_bell_row(
            db, ntype="guest_promotional", email="optin@example.com",
            created_at=now - timedelta(minutes=i),
        )

    assert await login(client, "huesped_optin", "Pass123!") == 200

    resp1 = await client.get(
        "/api/notifications/my?notification_type=guest_promotional&page=1&page_size=2"
    )
    body1 = resp1.json()
    assert resp1.status_code == 200, resp1.text
    assert body1["total"] == 3
    assert body1["total_pages"] == 2
    assert len(body1["items"]) == 2

    resp2 = await client.get(
        "/api/notifications/my?notification_type=guest_promotional&page=2&page_size=2"
    )
    body2 = resp2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["created_at_iso"] != body1["items"][0]["created_at_iso"]


# ── Marcar como leída (POST /api/notifications/{id}/read) ───────────────


async def test_my_notifications_includes_id_for_mark_read(client, db, monkeypatch):
    """El item de /my trae _id (string) para poder marcar como leída."""
    _seed_cliente_role(db, permissions=["account.read", "search.read"])
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    db.users.update_one(
        {"username": "huesped_optin"}, {"$set": {"password_hash": _pwd.hash("Pass123!")}}
    )
    _seed_bell_row(db, ntype="guest_promotional", email="optin@example.com", created_at=_now())

    assert await login(client, "huesped_optin", "Pass123!") == 200
    resp = await client.get("/api/notifications/my")
    item = resp.json()["items"][0]
    assert "_id" in item
    assert item["is_unread"] is True
    # El id viaja serializado (string), listo para POST /read.
    assert isinstance(item["_id"], str)


async def test_mark_notification_read_marks_only_own_row(client, db, monkeypatch):
    """POST /read marca solo la fila del usuario autenticado (404 para ajenas)."""
    _seed_cliente_role(db, permissions=["account.read", "search.read"])
    _seed_user(db, username="huesped_optin", email="optin@example.com", marketing_opt_in=True)
    _seed_user(db, username="otro_huesped", email="otro@example.com", marketing_opt_in=True)
    db.users.update_one(
        {"username": "huesped_optin"}, {"$set": {"password_hash": _pwd.hash("Pass123!")}}
    )
    now = _now()
    _seed_bell_row(db, ntype="guest_promotional", email="optin@example.com", created_at=now)
    _seed_bell_row(
        db, ntype="guest_promotional", email="optin@example.com",
        created_at=now - timedelta(minutes=1),
    )
    _seed_bell_row(db, ntype="guest_promotional", email="otro@example.com", created_at=now)

    assert await login(client, "huesped_optin", "Pass123!") == 200
    mine = list(db.notification_log.find({"recipient_email": "optin@example.com"}))
    theirs = db.notification_log.find_one({"recipient_email": "otro@example.com"})

    resp = await client.post(f"/api/notifications/{mine[0]['_id']}/read")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["read"] is True
    assert body["id"] == str(mine[0]["_id"])
    assert db.notification_log.find_one({"_id": mine[0]["_id"]})["status"] == "read"
    # La otra fila del mismo usuario sigue sin leer.
    assert db.notification_log.find_one({"_id": mine[1]["_id"]})["status"] == "sent"
    # Marcar de nuevo es idempotente.
    resp2 = await client.post(f"/api/notifications/{mine[0]['_id']}/read")
    assert resp2.status_code == 200, resp2.text

    # Una fila de OTRO usuario → 404 (nunca se marca lo ajeno).
    resp3 = await client.post(f"/api/notifications/{theirs['_id']}/read")
    assert resp3.status_code == 404, resp3.text
    assert db.notification_log.find_one({"_id": theirs["_id"]})["status"] == "sent"

    # El dot desaparece de /my para la fila marcada.
    body = (await client.get("/api/notifications/my")).json()
    by_id = {str(it["_id"]): it for it in body["items"]}
    assert by_id[str(mine[0]["_id"])]["is_unread"] is False
    assert by_id[str(mine[1]["_id"])]["is_unread"] is True


async def test_mark_read_rejects_invalid_id(client, db, admin_user):
    """Un id malformado da 422; el huésped no puede tocar ids ajenos."""
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.post("/api/notifications/not-an-id/read")
    assert resp.status_code == 422, resp.text


# ── Programación de envíos (send_at + cola scheduled_promotions) ─────────


async def test_schedule_promotion_queues_future_send(client, db):
    """POST con send_at futuro: NO envía; guarda en la cola con status pending."""
    _seed_marketing_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero")
    assert await login(client, "marketing_test", "Pass123!") == 200

    send_at = _now() + timedelta(hours=2)
    resp = await client.post(
        "/api/notifications/promotions",
        json={
            "title": "Oferta de verano",
            "message": "20% off en tu próxima estadía.",
            "prop_id": 1,
            "send_at": send_at.isoformat(),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scheduled"] is True
    assert body["sent"] == 0
    assert body["recipients"] == []
    assert body["campaign_id"].startswith("PROMO-")
    assert body["send_at_iso"]

    # Nada se envió todavía.
    assert _promo_rows(db) == []
    sched = db.scheduled_promotions.find_one({"campaign_id": body["campaign_id"]})
    assert sched is not None
    assert sched["status"] == "pending"
    assert sched["title"] == "Oferta de verano"
    assert sched["created_by"] == "marketing@example.com"
    assert sched["estimated_recipients"] == 0


async def test_schedule_past_send_at_falls_back_to_immediate(client, db, monkeypatch):
    """send_at en el pasado → envío inmediato (fallback amable, no 422)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero")
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json={
            "title": "Ya vencida",
            "message": "Mensaje de prueba con hora pasada.",
            "send_at": (_now() - timedelta(minutes=5)).isoformat(),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scheduled"] is False
    assert body["sent"] == 1
    assert len(_promo_rows(db)) == 1
    assert db.scheduled_promotions.count_documents({}) == 0


async def test_process_due_sends_only_due_pending(db, monkeypatch):
    """El worker envía solo campañas pendientes cuya send_at ya venció."""
    _seed_cliente_role(db)
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    future = promos.schedule_promotion(
        title="Futura", message="Promo futura de prueba para la cola.",
        prop_id=None, send_at=_now() + timedelta(hours=1), created_by="m@x.com",
    )
    due = promos.schedule_promotion(
        title="Debida", message="Promo que ya venció en la cola.",
        prop_id=None, send_at=_now() - timedelta(minutes=1), created_by="m@x.com",
    )

    processed = promos.process_due_scheduled_promotions(db, now=_now())

    assert processed == 1
    rows = _promo_rows(db)
    assert len(rows) == 1
    assert rows[0]["title"] == "Debida"
    assert rows[0]["campaign_id"] == due["campaign_id"]
    doc_due = db.scheduled_promotions.find_one({"campaign_id": due["campaign_id"]})
    assert doc_due["status"] == "sent"
    assert doc_due["sent_at"] is not None
    doc_future = db.scheduled_promotions.find_one({"campaign_id": future["campaign_id"]})
    assert doc_future["status"] == "pending"


async def test_process_due_skips_canceled(db, monkeypatch):
    """Las campañas canceladas nunca se envían."""
    _seed_cliente_role(db)
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    sched = promos.schedule_promotion(
        title="Cancelada", message="Esta promoción fue cancelada.",
        prop_id=None, send_at=_now() - timedelta(minutes=1), created_by="m@x.com",
    )
    assert promos.cancel_scheduled_promotion(db, sched["campaign_id"]) is True

    processed = promos.process_due_scheduled_promotions(db, now=_now())

    assert processed == 0
    assert _promo_rows(db) == []
    assert db.scheduled_promotions.find_one({"campaign_id": sched["campaign_id"]})["status"] == "canceled"


async def test_cancel_endpoint_cancels_pending_only(client, db, monkeypatch):
    """POST cancel: cancela solo pendientes; repetir da 404."""
    _seed_marketing_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero")
    assert await login(client, "marketing_test", "Pass123!") == 200

    sched = promos.schedule_promotion(
        title="A cancelar", message="Promoción que se va a cancelar.",
        prop_id=None, send_at=_now() + timedelta(hours=3), created_by="marketing@example.com",
    )
    cid = sched["campaign_id"]

    resp = await client.post(f"/api/notifications/promotions/{cid}/cancel")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"campaign_id": cid, "canceled": True}
    assert db.scheduled_promotions.find_one({"campaign_id": cid})["status"] == "canceled"

    # Cancelar de nuevo: ya no está pendiente → 404.
    resp2 = await client.post(f"/api/notifications/promotions/{cid}/cancel")
    assert resp2.status_code == 404, resp2.text


async def test_cancel_endpoint_requires_promotions_manage(client, db, cliente_user):
    """Un huésped no puede cancelar promociones (403)."""
    sched = promos.schedule_promotion(
        title="Protegida", message="Solo staff con promotions.manage cancela.",
        prop_id=None, send_at=_now() + timedelta(hours=1), created_by="staff@x.com",
    )
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.post(f"/api/notifications/promotions/{sched['campaign_id']}/cancel")
    assert resp.status_code == 403, resp.text


async def test_history_includes_scheduled_and_canceled(client, db, monkeypatch):
    """El historial mezcla enviadas (status sent) con programadas/canceladas."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200

    promos.send_promotion(title="Ya enviada", message="Promoción que ya salió a los huéspedes.", prop_id=1)
    sched = promos.schedule_promotion(
        title="Programada", message="Promoción futura agendada para mañana.",
        prop_id=1, send_at=_now() + timedelta(days=1), created_by="marketing@example.com",
    )
    canceled = promos.schedule_promotion(
        title="Cancelada", message="Esta se canceló antes de enviarse.",
        prop_id=1, send_at=_now() + timedelta(hours=5), created_by="marketing@example.com",
    )
    promos.cancel_scheduled_promotion(db, canceled["campaign_id"])

    resp = await client.get("/api/notifications/promotions/history")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    by_title = {it["title"]: it for it in body["items"]}
    assert by_title["Ya enviada"]["status"] == "sent"
    assert "sent_at_iso" in by_title["Ya enviada"]
    assert by_title["Programada"]["status"] == "pending"
    assert by_title["Programada"]["send_at_iso"]
    # Estimado tomado en el momento de agendar (el huésped con opt-in cuenta).
    assert by_title["Programada"]["recipient_count"] == 1
    assert by_title["Cancelada"]["status"] == "canceled"


async def test_history_excludes_scheduled_already_sent(client, db, monkeypatch):
    """Una campaña agendada que ya se envió aparece UNA sola vez (desde
    notification_log), no duplicada por el doc de la cola."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200

    sched = promos.schedule_promotion(
        title="Agendada y enviada", message="Agendada que el worker ya envió.",
        prop_id=1, send_at=_now() - timedelta(minutes=1), created_by="marketing@example.com",
    )
    promos.process_due_scheduled_promotions(db, now=_now())

    resp = await client.get("/api/notifications/promotions/history")
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["campaign_id"] == sched["campaign_id"]
    assert item["status"] == "sent"


async def test_history_shows_sent_campaign_with_zero_recipients(db, monkeypatch):
    """Una campaña enviada a 0 destinatarios no escribe filas de notification_log;
    el historial la muestra igual (status sent, recipient_count 0) en vez de
    hacerla desaparecer (no hay filas con las que deduplicar)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    sched = promos.schedule_promotion(
        title="Sin destinatarios", message="Promoción enviada sin huéspedes con opt-in.",
        prop_id=None, send_at=_now() - timedelta(minutes=1), created_by="m@x.com",
    )
    promos.process_due_scheduled_promotions(db, now=_now())
    assert _promo_rows(db) == []  # 0 destinatarios → 0 filas

    body = promos.list_promotion_history(db)
    assert body["total"] == 1
    item = body["items"][0]
    assert item["campaign_id"] == sched["campaign_id"]
    assert item["status"] == "sent"
    assert item["recipient_count"] == 0
    assert "sent_at_iso" in item


# ── Detalle de campaña (GET /promotions/{campaign_id}/recipients) ────────


async def test_recipients_endpoint_lists_guests_with_read_status(client, db, monkeypatch):
    """GET recipients devuelve el mensaje completo y cada destinatario con su
    nombre, email y si leyó la promoción (dot de la campanita)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    _seed_hotel(db, 1)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 1, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)

    result = promos.send_promotion(
        title="Oferta de verano", message="20% off en tu próxima estadía.", prop_id=1
    )
    cid = result["campaign_id"]
    # h1 leyó la promo (dot de la campanita); h2 sigue sin leer.
    row_h1 = db.notification_log.find_one({"campaign_id": cid, "recipient_email": "h1@example.com"})
    db.notification_log.update_one(
        {"_id": row_h1["_id"]}, {"$set": {"status": "read", "read_at": _now()}}
    )

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get(f"/api/notifications/promotions/{cid}/recipients")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Oferta de verano"
    assert body["message"] == "20% off en tu próxima estadía."
    assert body["hotel_name"] == "Hotel Lima Centro 1"
    assert body["status"] == "sent"
    assert body["recipient_count"] == 2
    by_email = {r["email"]: r for r in body["recipients"]}
    assert by_email["h1@example.com"]["name"] == "H1"
    assert by_email["h1@example.com"]["is_read"] is True
    assert by_email["h1@example.com"]["read_at_iso"]
    assert by_email["h2@example.com"]["name"] == "H2"
    assert by_email["h2@example.com"]["is_read"] is False
    assert by_email["h2@example.com"]["read_at_iso"] is None


async def test_recipients_endpoint_for_pending_campaign(client, db):
    """Una campaña aún pendiente en la cola no tiene destinatarios reales;
    devuelve el estimado tomado al agendar y el status pending."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    sched = promos.schedule_promotion(
        title="Programada", message="Promoción futura agendada para mañana.",
        prop_id=1, send_at=_now() + timedelta(days=1), created_by="marketing@example.com",
    )

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get(f"/api/notifications/promotions/{sched['campaign_id']}/recipients")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["recipients"] == []
    assert body["recipient_count"] == 1  # estimado al agendar (optin tiene opt-in)
    assert body["send_at_iso"]


async def test_recipients_endpoint_for_sent_zero_recipients(client, db, monkeypatch, admin_user):
    """Campaña enviada a 0 destinatarios: status sent y lista vacía (la data
    vive en el doc de la cola, no hay filas de notification_log)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    sched = promos.schedule_promotion(
        title="Sin destinatarios", message="Promoción enviada sin huéspedes con opt-in.",
        prop_id=None, send_at=_now() - timedelta(minutes=1), created_by="m@x.com",
    )
    promos.process_due_scheduled_promotions(db, now=_now())
    assert _promo_rows(db) == []

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.get(f"/api/notifications/promotions/{sched['campaign_id']}/recipients")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sent"
    assert body["recipients"] == []
    assert body["recipient_count"] == 0
    assert body["sent_at_iso"]


async def test_recipients_endpoint_404_for_unknown_campaign(client, db, admin_user):
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.get("/api/notifications/promotions/PROMO-1-UNKNOWN/recipients")
    assert resp.status_code == 404, resp.text


async def test_recipients_endpoint_requires_promotions_manage(client, db, cliente_user):
    """El huésped no tiene promotions.manage → 403 (no ve la lista de quién
    recibió promociones)."""
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.get("/api/notifications/promotions/PROMO-1-XYZ/recipients")
    assert resp.status_code == 403, resp.text


# ── Scope por hotel del marketing (assigned_hotels) ──────────────────────


async def test_history_scopes_to_marketing_users_assigned_hotels(client, db, monkeypatch):
    """marketing_hotelero ve SOLO las campañas de sus hoteles asignados."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 2, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Prop 1", message="Campaña del hotel uno.", prop_id=1)
    promos.send_promotion(title="Prop 2", message="Campaña del hotel dos.", prop_id=2)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get("/api/notifications/promotions/history")
    assert resp.status_code == 200, resp.text
    titles = {it["title"] for it in resp.json()["items"]}
    assert titles == {"Prop 1"}


async def test_history_client_prop_id_cannot_expand_scope(client, db, monkeypatch):
    """?prop_id de otro hotel NO amplía el alcance del marketing hotelero."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 2, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Prop 1", message="Campaña del hotel uno.", prop_id=1)
    promos.send_promotion(title="Prop 2", message="Campaña del hotel dos.", prop_id=2)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get("/api/notifications/promotions/history?prop_id=2")
    titles = {it["title"] for it in resp.json()["items"]}
    assert titles == {"Prop 1"}  # el prop_id=2 se ignora: no está en su alcance


async def test_history_restricted_user_without_hotels_sees_nothing(client, db, monkeypatch):
    """marketing_hotelero sin assigned_hotels → historial vacío (deny-by-default)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com", role="marketing_hotelero")
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Sola", message="Única campaña del sistema.", prop_id=1)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get("/api/notifications/promotions/history")
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


async def test_history_superadmin_sees_all_and_filters_by_prop(client, db, admin_user, monkeypatch):
    """El superadmin (sin restricción) ve todo y filtra por ?prop_id si quiere."""
    _seed_cliente_role(db)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 2, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Prop 1", message="Campaña del hotel uno.", prop_id=1)
    promos.send_promotion(title="Prop 2", message="Campaña del hotel dos.", prop_id=2)

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    all_resp = await client.get("/api/notifications/promotions/history")
    all_titles = {it["title"] for it in all_resp.json()["items"]}
    assert all_titles == {"Prop 1", "Prop 2"}

    filtered = await client.get("/api/notifications/promotions/history?prop_id=1")
    filtered_titles = {it["title"] for it in filtered.json()["items"]}
    assert filtered_titles == {"Prop 1"}


# ── Ofertas públicas del hotel (GET /api/hotels/{prop_id}/promotions) ────


async def test_public_offers_lists_sent_campaigns_grouped_by_send(client, db, monkeypatch):
    """GET /api/hotels/1/promotions es público y lista las campañas enviadas
    agrupadas por envío, más reciente primero, SIN el message (PII: puede
    contener el nombre del huésped, p.ej. «¡Hola Horuz!»)."""
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 1, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Oferta verano", message="20% de descuento.", prop_id=1)
    promos.send_promotion(title="Novedades spa", message="Nuevo spa.", prop_id=1)

    # Sin login: endpoint público (como /api/hotels/{id} y /similar).
    resp = await client.get("/api/hotels/1/promotions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["prop_id"] == 1
    assert body["hotel_name"] == "Hotel Lima Centro 1"
    assert [it["title"] for it in body["items"]] == ["Novedades spa", "Oferta verano"]
    first = body["items"][0]
    assert first["campaign_id"].startswith("PROMO-")
    assert "sent_at_iso" in first
    # Guard PII: el message (puede incluir el nombre del huésped) NUNCA sale.
    assert "message" not in first


async def test_public_offers_group_recipients_into_one_offer(client, db, monkeypatch):
    """Varios destinatarios de un mismo envío = UNA oferta (agrupada por
    campaign_id), como el historial de marketing."""
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "h1@example.com"})
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 1, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    promos.send_promotion(title="Para todos", message="Promo para dos huéspedes.", prop_id=1)

    resp = await client.get("/api/hotels/1/promotions")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Para todos"


async def test_public_offers_excludes_pending_and_canceled(client, db):
    """Las campañas programadas/canceladas NO son ofertas activas todavía:
    solo las enviadas (con filas en notification_log) se anuncian."""
    _seed_hotel(db, 1)
    promos.schedule_promotion(
        title="Programada", message="Promo futura agendada para mañana.",
        prop_id=1, send_at=_now() + timedelta(days=1), created_by="m@x.com",
    )
    canceled = promos.schedule_promotion(
        title="Cancelada", message="Se canceló antes de enviarse.",
        prop_id=1, send_at=_now() + timedelta(hours=5), created_by="m@x.com",
    )
    promos.cancel_scheduled_promotion(db, canceled["campaign_id"])

    resp = await client.get("/api/hotels/1/promotions")
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


async def test_public_offers_empty_for_hotel_without_campaigns(client, db):
    """Hotel sin promociones → lista vacía (200, no error)."""
    _seed_hotel(db, 1)
    resp = await client.get("/api/hotels/1/promotions")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"prop_id": 1, "hotel_name": "Hotel Lima Centro 1", "items": []}


async def test_public_offers_404_for_unknown_hotel(client, db):
    """Hotel inexistente → 404 (consistente con GET /api/hotels/{id})."""
    resp = await client.get("/api/hotels/999/promotions")
    assert resp.status_code == 404, resp.text


async def test_recipients_endpoint_scoped_to_assigned_hotels(client, db, monkeypatch):
    """El marketing hotelero no puede abrir el detalle de una campaña ajena
    (404 — el alcance se impone en el servidor, no en el cliente)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 2, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    result = promos.send_promotion(title="Ajeno", message="Campaña de otro hotel.", prop_id=2)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get(f"/api/notifications/promotions/{result['campaign_id']}/recipients")
    assert resp.status_code == 404, resp.text


# ── Fase 2: entidad promotions (applies_to tarifas + cupones de Tarifas) ──


def _seed_rate_plan(db, prop_id: int, name: str) -> str:
    rate_plan_id = f"RP-{prop_id}-{name.lower().replace(' ', '-')}"
    db.rate_plans.insert_one(
        {
            "rate_plan_id": rate_plan_id,
            "prop_id": prop_id,
            "name": name,
            "base_rate": 120.0,
            "currency": "USD",
            "applicable_room_types": [],
            "is_active": True,
            "updated_at": _now(),
        }
    )
    return rate_plan_id


def _offer_payload(**overrides) -> dict:
    payload = {
        "title": "Oferta de verano",
        "message": "20% off en tu próxima estadía reservando directo.",
        "prop_id": 1,
        "public_message": "20% de descuento en tarifas seleccionadas reservando directo en el sitio.",
        "validity_start": "2026-08-01",
        "validity_end": "2026-09-30",
        "segment": "families",
        "applies_to_scope": "property",
        "promo_code": "VERANO20",
        "discount_percent": 20,
    }
    payload.update(overrides)
    return payload


async def test_send_with_offer_creates_offer_and_coupon_campaign(client, db, monkeypatch):
    """Fase 2: el POST con detalles de oferta crea la entidad ``promotions``,
    la campaña de cupones de Tarifas (promotion_campaigns + coupon_codes —
    la sección «Promociones» que ya existía) y estampa ``promotion_id`` en
    las filas de notification_log."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post("/api/notifications/promotions", json=_offer_payload())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sent"] == 1
    assert body["promotion_id"].startswith("OFFER-")

    offer = db.promotions.find_one({"promotion_id": body["promotion_id"]})
    assert offer is not None
    assert offer["prop_id"] == 1
    assert offer["status"] == "active"
    assert offer["public_message"].startswith("20% de descuento")
    assert offer["validity"] == {"start_date": "2026-08-01", "end_date": "2026-09-30"}
    assert offer["segment"] == {"audience": "families"}
    assert offer["applies_to"] == {"scope": "property", "rate_plan_ids": []}
    assert offer["promo_code"] == "VERANO20"
    assert offer["discount_percent"] == 20
    assert offer["campaign_id"] == body["campaign_id"]
    assert offer["sent_at"] is not None

    # La sección «Promociones» de Tarifas comparte la campaña de cupones.
    campaign = db.promotion_campaigns.find_one({"campaign_id": offer["coupon_campaign_id"]})
    assert campaign is not None
    assert campaign["discount_percent"] == 20
    assert campaign["prop_id"] == 1
    coupon = db.coupon_codes.find_one({"coupon_code": "VERANO20"})
    assert coupon is not None
    assert coupon["campaign_id"] == offer["coupon_campaign_id"]

    # La fila de la campanita referencia la oferta.
    row = db.notification_log.find_one({"campaign_id": body["campaign_id"]})
    assert row["promotion_id"] == body["promotion_id"]


async def test_send_with_offer_schedules_entity(client, db, monkeypatch):
    """send_at futuro + oferta → entidad status ``scheduled``, campaña de
    cupones creada al componer, y sin filas en notification_log todavía."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(send_at=(_now() + timedelta(hours=3)).isoformat()),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scheduled"] is True
    assert body["promotion_id"].startswith("OFFER-")

    offer = db.promotions.find_one({"promotion_id": body["promotion_id"]})
    assert offer["status"] == "scheduled"
    assert offer["campaign_id"] == body["campaign_id"]
    assert offer["send_at"] is not None
    assert offer["sent_at"] is None
    assert _promo_rows(db) == []
    assert db.scheduled_promotions.count_documents({"campaign_id": body["campaign_id"]}) == 1
    # Los cupones se crean al componer la oferta (no al enviarla).
    assert db.promotion_campaigns.count_documents({"prop_id": 1}) == 1


async def test_cancel_scheduled_offer_marks_entity_canceled(client, db, monkeypatch):
    """Cancelar una oferta programada también marca la entidad como canceled."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(send_at=(_now() + timedelta(hours=3)).isoformat()),
    )
    cid = resp.json()["campaign_id"]

    cancel = await client.post(f"/api/notifications/promotions/{cid}/cancel")
    assert cancel.status_code == 200, cancel.text
    offer = db.promotions.find_one({"campaign_id": cid})
    assert offer is not None
    assert offer["status"] == "canceled"
    assert offer["canceled_at"] is not None


async def test_send_with_foreign_rate_plan_rejected(client, db):
    """Un rate_plan de OTRA propiedad no puede aplicarse a la oferta (400) —
    el plan debe pertenecer al hotel de la promoción."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_rate_plan(db, 2, "Deluxe")
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(applies_to_scope="rate_plans", rate_plan_ids=["RP-2-deluxe"]),
    )
    assert resp.status_code == 400, resp.text
    assert db.promotions.count_documents({}) == 0


async def test_send_with_invalid_segment_rejected(client, db):
    """Un segmento desconocido se rechaza (400) antes de escribir nada."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post("/api/notifications/promotions", json=_offer_payload(segment="aliens"))
    assert resp.status_code == 400, resp.text
    assert db.promotions.count_documents({}) == 0


async def test_public_offers_entity_first_with_public_fields(client, db, monkeypatch):
    """Cuando el hotel tiene entidad ``promotions``, el endpoint público sirve
    la entidad (public_message, código, ventana, aplica-a) — nunca el message."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    rp = _seed_rate_plan(db, 1, "Deluxe")
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200
    await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(applies_to_scope="rate_plans", rate_plan_ids=[rp],
                            promo_code="DELUXE20"),
    )

    resp = await client.get("/api/hotels/1/promotions")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 1
    it = body["items"][0]
    assert it["title"] == "Oferta de verano"
    assert it["public_message"].startswith("20% de descuento")
    assert it["promo_code"] == "DELUXE20"
    assert it["discount_percent"] == 20
    assert it["validity"] == {"start_date": "2026-08-01", "end_date": "2026-09-30"}
    assert it["applies_to_label"] == "Deluxe"
    assert it["segment_label"] == "Familias"
    assert "sent_at_iso" in it
    assert "message" not in it  # guard PII intacto


async def test_public_offers_entity_hides_expired_and_pending(client, db, monkeypatch):
    """Entidad con validez vencida o aún no enviada NO se anuncia; con solo
    entidades inactivas la lista es vacía (no cae al fallback legacy)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200

    # Enviada pero vencida.
    await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(title="Vencida", validity_start="2020-01-01", validity_end="2020-01-31"),
    )
    # Programada (aún no enviada). Código DISTINTO: el guard anti-duplicado
    # impide que dos campañas compartan el mismo cupón (una sola fuente).
    await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(title="Futura", promo_code="FUTURA10", discount_percent=10,
                            send_at=(_now() + timedelta(days=2)).isoformat()),
    )
    assert db.promotions.count_documents({}) == 2

    resp = await client.get("/api/hotels/1/promotions")
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


async def test_options_endpoint_requires_promotions_manage(client, db, cliente_user):
    """GET /promotions/options exige promotions.manage (huésped → 403)."""
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200
    resp = await client.get("/api/notifications/promotions/options?prop_id=1")
    assert resp.status_code == 403, resp.text


async def test_options_endpoint_lists_rate_plans_with_room_labels(client, db):
    """El endpoint de opciones devuelve los planes tarifarios del hotel con
    las etiquetas de sus room types (selector «Aplica a» del composer)."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    rp = _seed_rate_plan(db, 1, "Deluxe")
    db.rate_plans.update_one({"rate_plan_id": rp}, {"$set": {"applicable_room_types": ["RT-1"]}})
    db.room_types.insert_one({"prop_id": 1, "room_type_id": "RT-1", "name": "Deluxe King"})

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get("/api/notifications/promotions/options?prop_id=1")
    assert resp.status_code == 200, resp.text
    plans = resp.json()["rate_plans"]
    assert len(plans) == 1
    assert plans[0]["name"] == "Deluxe"
    assert plans[0]["room_type_labels"] == ["Deluxe King"]


# ── Edición de la entidad (PUT /promotions/{id}/offer) ────────────────────


async def _seed_offer_and_send(client, db, monkeypatch, **payload_overrides) -> str:
    """Envía una oferta completa y devuelve su campaign_id (para editar/pausar)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200
    payload = _offer_payload(**payload_overrides)
    resp = await client.post("/api/notifications/promotions", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["campaign_id"]


async def test_edit_offer_updates_entity_without_resending(client, db, monkeypatch):
    """PUT /promotions/{id}/offer edita la entidad (mensaje público, validez,
    aplica-a) SIN re-enviar: las filas de notification_log quedan intactas y
    la página pública refleja la nueva descripción."""
    cid = await _seed_offer_and_send(client, db, monkeypatch)
    rp2 = _seed_rate_plan(db, 1, "King")
    before_rows = list(db.notification_log.find({"campaign_id": cid}))

    resp = await client.put(
        f"/api/notifications/promotions/{cid}/offer",
        json={
            "public_message": "Nueva descripción pública de la oferta editada.",
            "validity_start": "2026-09-01",
            "validity_end": "2026-09-30",
            "segment": "business",
            "applies_to_scope": "rate_plans",
            "rate_plan_ids": [rp2],
        },
    )
    assert resp.status_code == 200, resp.text

    offer = db.promotions.find_one({"campaign_id": cid})
    assert offer["public_message"] == "Nueva descripción pública de la oferta editada."
    assert offer["validity"] == {"start_date": "2026-09-01", "end_date": "2026-09-30"}
    assert offer["segment"] == {"audience": "business"}
    assert offer["applies_to"] == {"scope": "rate_plans", "rate_plan_ids": [rp2]}
    assert offer["status"] == "active"

    # Sin re-envío: las filas de la campanita no cambian (ni se duplican).
    after_rows = list(db.notification_log.find({"campaign_id": cid}))
    assert len(after_rows) == len(before_rows) == 1
    assert after_rows[0]["message"] == before_rows[0]["message"]

    # La página pública refleja la edición.
    public = await client.get("/api/hotels/1/promotions")
    item = public.json()["items"][0]
    assert item["public_message"] == "Nueva descripción pública de la oferta editada."
    assert item["applies_to_label"] == "King"


async def test_edit_offer_rejects_foreign_rate_plan(client, db, monkeypatch):
    """Un rate_plan de otra propiedad no puede aplicarse al editar (400)."""
    cid = await _seed_offer_and_send(client, db, monkeypatch)
    _seed_rate_plan(db, 2, "Deluxe")

    resp = await client.put(
        f"/api/notifications/promotions/{cid}/offer",
        json={"applies_to_scope": "rate_plans", "rate_plan_ids": ["RP-2-deluxe"]},
    )
    assert resp.status_code == 400, resp.text


async def test_edit_offer_404_without_entity(client, db, monkeypatch):
    """Una campaña legacy (sin entidad promotions) no se puede editar → 404."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    result = promos.send_promotion(title="Legacy", message="Promo anterior a Fase 2.", prop_id=1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])

    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.put(
        f"/api/notifications/promotions/{result['campaign_id']}/offer",
        json={"public_message": "Editar legacy."},
    )
    assert resp.status_code == 404, resp.text


async def test_edit_offer_scoped_to_assigned_hotels(client, db, monkeypatch):
    """Un marketing de [1] no puede editar la oferta de otro hotel (404)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 2)
    _seed_user(db, username="h2", email="h2@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-2", "prop_id": 2, "guest_email": "h2@example.com"})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    result = promos.send_promotion(
        title="Ajeno", message="Oferta de otro hotel.", prop_id=2
    )
    # La oferta ajena necesita su entidad promotions.
    db.promotions.insert_one(
        {
            "promotion_id": "OFFER-2-AJENA",
            "prop_id": 2,
            "title": "Ajeno",
            "message": "Oferta de otro hotel.",
            "public_message": "Oferta ajena.",
            "status": "active",
            "campaign_id": result["campaign_id"],
            "created_at": _now(),
        }
    )
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.put(
        f"/api/notifications/promotions/{result['campaign_id']}/offer",
        json={"public_message": "Intento de edición ajena."},
    )
    assert resp.status_code == 404, resp.text


# ── Pausa / reactivación de la oferta pública (POST …/offer/toggle-public) ──


async def test_pause_offer_hides_from_public_but_keeps_rows(client, db, monkeypatch):
    """Pausar la oferta la quita de la página pública SIN tocar lo ya enviado
    (la campanita del huésped conserva la notificación)."""
    cid = await _seed_offer_and_send(client, db, monkeypatch)
    assert len(list(db.notification_log.find({"campaign_id": cid}))) == 1

    resp = await client.post(
        f"/api/notifications/promotions/{cid}/offer/toggle-public",
        json={"active": False},
    )
    assert resp.status_code == 200, resp.text
    assert db.promotions.find_one({"campaign_id": cid})["status"] == "paused"

    # Fuera de la página pública.
    public = await client.get("/api/hotels/1/promotions")
    assert public.json()["items"] == []

    # El envío ya hecho NO cambia: la fila de la campanita sigue ahí.
    rows = list(db.notification_log.find({"campaign_id": cid}))
    assert len(rows) == 1
    assert rows[0]["status"] == "sent"

    # El historial marca la oferta como pausada.
    history = await client.get("/api/notifications/promotions/history")
    item = history.json()["items"][0]
    assert item["offer_status"] == "paused"


async def test_resume_offer_restores_public(client, db, monkeypatch):
    """Reactivar la oferta la vuelve a la página pública (status active)."""
    cid = await _seed_offer_and_send(client, db, monkeypatch)
    await client.post(
        f"/api/notifications/promotions/{cid}/offer/toggle-public", json={"active": False}
    )

    resp = await client.post(
        f"/api/notifications/promotions/{cid}/offer/toggle-public", json={"active": True}
    )
    assert resp.status_code == 200, resp.text
    assert db.promotions.find_one({"campaign_id": cid})["status"] == "active"

    public = await client.get("/api/hotels/1/promotions")
    assert len(public.json()["items"]) == 1


async def test_resume_expired_offer_rejected(client, db, monkeypatch):
    """Reactivar una oferta cuya validez ya venció se rechaza (400) — no se
    puede anunciar algo vencido."""
    cid = await _seed_offer_and_send(
        client, db, monkeypatch,
        validity_start="2020-01-01", validity_end="2020-01-31",
    )
    await client.post(
        f"/api/notifications/promotions/{cid}/offer/toggle-public", json={"active": False}
    )

    resp = await client.post(
        f"/api/notifications/promotions/{cid}/offer/toggle-public", json={"active": True}
    )
    assert resp.status_code == 400, resp.text
    assert db.promotions.find_one({"campaign_id": cid})["status"] == "paused"


async def test_toggle_public_404_without_entity(client, db, monkeypatch):
    """Sin entidad promotions no hay oferta que pausar → 404."""
    _seed_cliente_role(db)
    _seed_user(db, username="h1", email="h1@example.com", marketing_opt_in=True)
    _seed_hotel(db, 1)
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    result = promos.send_promotion(title="Legacy", message="Promo vieja.", prop_id=1)
    _seed_marketing_role(db)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        f"/api/notifications/promotions/{result['campaign_id']}/offer/toggle-public",
        json={"active": False},
    )
    assert resp.status_code == 404, resp.text


async def test_history_and_detail_include_offer_status(client, db, monkeypatch):
    """El historial y el detalle exponen offer_status + los campos editables
    de la entidad (para pre-llenar el modal sin un fetch extra)."""
    cid = await _seed_offer_and_send(client, db, monkeypatch)

    history = await client.get("/api/notifications/promotions/history")
    item = history.json()["items"][0]
    assert item["offer_status"] == "active"
    assert item["public_message"]
    assert item["validity"] == {"start_date": "2026-08-01", "end_date": "2026-09-30"}
    assert item["applies_to"] == {"scope": "property", "rate_plan_ids": []}
    assert item["segment"] == {"audience": "families"}
    assert item["promo_code"] == "VERANO20"
    assert item["coupon_campaign_id"]

    detail = await client.get(f"/api/notifications/promotions/{cid}/recipients")
    assert detail.json()["offer_status"] == "active"


# ── Vínculo de campaña de cupones existente de Tarifas (Opción A) ────────


def _seed_coupon_campaign(
    db, *, prop_id: int = 1, name: str = "Luna de miel", code: str = "LUNA15",
    discount: int = 15,
) -> str:
    """Crea una campaña de cupones de Tarifas (la sección «Promociones» que
    ya existía) tal como lo hace el gestor de Tarifas — única fuente de
    verdad de cupones. Devuelve su ``campaign_id``."""
    return create_promotion_campaign(
        prop_id=prop_id,
        name=name,
        description="Campaña de prueba.",
        discount_percent=discount,
        start_date="",
        end_date="",
        coupon_count=1,
        coupon_code=code,
        is_active=True,
    )["campaign_id"]


async def test_options_endpoint_lists_coupon_campaigns(client, db):
    """GET /promotions/options devuelve las campañas de cupones del hotel
    (código + descuento) para que el marketing VINCULE una existente en vez
    de crear una duplicada."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    cid = _seed_coupon_campaign(db, prop_id=1)

    assert await login(client, "marketing_test", "Pass123!") == 200
    resp = await client.get("/api/notifications/promotions/options?prop_id=1")
    assert resp.status_code == 200, resp.text
    campaigns = resp.json()["campaigns"]
    assert len(campaigns) == 1
    camp = campaigns[0]
    assert camp["campaign_id"] == cid
    assert camp["name"] == "Luna de miel"
    assert camp["discount_percent"] == 15
    assert camp["coupon_code"] == "LUNA15"


async def test_send_links_existing_campaign_without_creating(client, db, monkeypatch):
    """Vincular una campaña existente de Tarifas NO crea cupones nuevos: la
    entidad referencia la campaña vía coupon_campaign_id y deriva código y
    descuento de ella."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    cid = _seed_coupon_campaign(db, prop_id=1)
    campaigns_before = db.promotion_campaigns.count_documents({"prop_id": 1})
    coupons_before = db.coupon_codes.count_documents({"campaign_id": cid})
    monkeypatch.setattr(promos, "send_email", lambda to, subject, html: True)
    assert await login(client, "marketing_test", "Pass123!") == 200

    payload = _offer_payload(promo_code=None, discount_percent=None, coupon_campaign_id=cid)
    resp = await client.post("/api/notifications/promotions", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    offer = db.promotions.find_one({"promotion_id": body["promotion_id"]})
    assert offer is not None
    assert offer["coupon_campaign_id"] == cid
    assert offer["promo_code"] == "LUNA15"
    assert offer["discount_percent"] == 15
    # Nada se duplicó: misma campaña, mismos cupones.
    assert db.promotion_campaigns.count_documents({"prop_id": 1}) == campaigns_before
    assert db.coupon_codes.count_documents({"campaign_id": cid}) == coupons_before


async def test_send_link_rejects_foreign_campaign(client, db):
    """Una campaña de cupones de OTRO hotel no se puede vincular (400) y no
    se escribe nada."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_hotel(db, 2)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    cid = _seed_coupon_campaign(db, prop_id=2, code="OTRA20", name="Otra promo")
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(promo_code=None, discount_percent=None, coupon_campaign_id=cid),
    )
    assert resp.status_code == 400, resp.text
    assert db.promotions.count_documents({}) == 0


async def test_send_link_rejects_unknown_campaign(client, db):
    """Una campaña inexistente no se puede vincular (400)."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(promo_code=None, discount_percent=None, coupon_campaign_id="PC-1-no-existe"),
    )
    assert resp.status_code == 400, resp.text
    assert db.promotions.count_documents({}) == 0


async def test_send_link_and_create_both_rejected(client, db):
    """Vincular Y crear a la vez no tiene sentido: 400 (una sola fuente)."""
    _seed_marketing_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    cid = _seed_coupon_campaign(db, prop_id=1)
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(coupon_campaign_id=cid),  # mantiene promo_code VERANO20
    )
    assert resp.status_code == 400, resp.text
    assert db.promotions.count_documents({}) == 0


async def test_create_with_existing_code_does_not_steal(client, db):
    """Crear con un código que YA pertenece a otra campaña de Tarifas no lo
    roba: 400 y el cupón sigue en su campaña original (sin duplicar)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    cid = _seed_coupon_campaign(db, prop_id=1, code="LUNA15")
    coupons_before = db.coupon_codes.count_documents({"campaign_id": cid})
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(promo_code="LUNA15", discount_percent=15),
    )
    assert resp.status_code == 400, resp.text
    assert db.promotions.count_documents({}) == 0
    assert db.promotion_campaigns.count_documents({"prop_id": 1}) == 1
    coupon = db.coupon_codes.find_one({"coupon_code": "LUNA15"})
    assert coupon["campaign_id"] == cid
    assert db.coupon_codes.count_documents({"campaign_id": cid}) == coupons_before


async def test_rates_promotion_create_rejects_existing_code(client, db, admin_user):
    """POST /rates/promotions con un código que ya pertenece a otra campaña
    NO lo re-asigna: 400, el cupón sigue en su campaña original y no queda
    campaña parcial creada."""
    _seed_hotel(db, 1)
    cid = _seed_coupon_campaign(db, prop_id=1, code="LUNA15")
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post(
        "/api/management/rates/promotions",
        json={
            "prop_id": 1,
            "name": "Otra promo",
            "description": "",
            "discount_percent": 30,
            "start_date": "",
            "end_date": "",
            "coupon_code": "LUNA15",
            "is_active": True,
        },
    )
    assert resp.status_code == 400, resp.text
    assert db.promotion_campaigns.count_documents({"prop_id": 1}) == 1
    coupon = db.coupon_codes.find_one({"coupon_code": "LUNA15"})
    assert coupon["campaign_id"] == cid


async def test_create_with_existing_code_returns_structured_conflict(client, db):
    """El 400 del guard anti-robo es ESTRUCTURADO (code + campaign_id) para
    que el composer de marketing pueda ofrecer «Vincular esta campaña» sin
    parsear el texto del mensaje (los nombres de campaña no son únicos)."""
    _seed_marketing_role(db)
    _seed_cliente_role(db)
    _seed_hotel(db, 1)
    _seed_user(db, username="marketing_test", email="marketing@example.com",
               role="marketing_hotelero", assigned_hotels=[1])
    _seed_user(db, username="optin", email="optin@example.com", marketing_opt_in=True)
    db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1, "guest_email": "optin@example.com"})
    cid = _seed_coupon_campaign(db, prop_id=1, code="LUNA15", name="Luna de miel")
    assert await login(client, "marketing_test", "Pass123!") == 200

    resp = await client.post(
        "/api/notifications/promotions",
        json=_offer_payload(promo_code="LUNA15", discount_percent=15),
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict), detail
    assert detail.get("code") == "COUPON_CODE_EXISTS"
    assert detail.get("campaign_id") == cid
    assert detail.get("campaign_name") == "Luna de miel"
    assert "Luna de miel" in detail.get("message", "")
    assert db.promotions.count_documents({}) == 0


async def test_rates_promotion_create_returns_structured_conflict(client, db, admin_user):
    """El 400 del POST /api/management/rates/promotions con un código que ya
    pertenece a otra campaña es ESTRUCTURADO (code + campaign_id + coupon_code),
    igual que el del marketing, para que el form de Tarifas lo muestre de
    forma destacada sin parsear el texto del mensaje."""
    _seed_hotel(db, 1)
    cid = _seed_coupon_campaign(db, prop_id=1, code="LUNA15", name="Luna de miel")
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.post(
        "/api/management/rates/promotions",
        json={
            "prop_id": 1,
            "name": "Otra promo",
            "description": "",
            "discount_percent": 30,
            "start_date": "",
            "end_date": "",
            "coupon_code": "LUNA15",
            "is_active": True,
        },
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict), detail
    assert detail.get("code") == "COUPON_CODE_EXISTS"
    assert detail.get("campaign_id") == cid
    assert detail.get("campaign_name") == "Luna de miel"
    assert detail.get("coupon_code") == "LUNA15"
    assert "Luna de miel" in detail.get("message", "")
    assert db.promotion_campaigns.count_documents({"prop_id": 1}) == 1
