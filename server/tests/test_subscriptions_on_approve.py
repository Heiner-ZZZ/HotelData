"""Fase 2 — suscripción al aprobar (docs/PLAN_SUSCRIPCION_Y_PAGOS.md §9.1/§13).

Cubre:
- ``approve_registration`` crea exactamente 1 suscripción (``pending_payment``)
  + 1 factura ``unpaid`` al aprobar, y pasa el bloque de pago al email.
- El fallo de creación de suscripción es **best-effort**: no revierte la
  aprobación (el hotel queda operativo, se audita el error).
- Migración idempotente ``scripts/migrate_backfill_subscriptions.py``: hoteles
  ya aprobados sin suscripción reciben una ``active`` con su ``price_band``
  (o la banda recomputada de ``total_rooms_declared``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId
from passlib.context import CryptContext

from src.app.modules.auth.routes import register_property as rp
from src.app.modules.property_approval import service as approval_service
from src.app.modules.subscriptions import service as subs

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

GERENTE_PERMS = ["dashboard.read", "reservations.manage", "hotel.manage_roles"]
CATALOG_CODES = [*GERENTE_PERMS, "properties.approve"]

_PENDING = "pending_approval"
_APPROVED = "approved"


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_permission_catalog(db) -> None:
    for code in CATALOG_CODES:
        db.permissions.insert_one(
            {
                "permission_code": code,
                "description": code,
                "is_system": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )


def _seed_gerente_template(db) -> ObjectId:
    return db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": list(GERENTE_PERMS),
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id


def _seed_onboarding_catalogs(db) -> None:
    db.dim_visitor_countries.insert_one(
        {"visitor_location_country_id": 1, "country_name": "Ecuador"}
    )
    db.system_currencies.insert_one({"code": "USD", "active": True})


def _capture_code(monkeypatch) -> dict:
    captured: dict = {}
    monkeypatch.setattr(
        rp,
        "_send_property_verification_code",
        lambda email, display_name, code: captured.update(code=code),
    )
    return captured


async def _complete_onboarding(
    client, db, monkeypatch, *, email: str, username: str, total_rooms: int = 20
) -> dict:
    _seed_onboarding_catalogs(db)
    captured = _capture_code(monkeypatch)
    payload = {
        "email": email,
        "username": username,
        "password": "Pass123!",
        "user_display_name": "Dueño Nuevo",
        "property_name": "Hotel Nuevo",
        "property_type": "hotel",
        "contact_phone": "+593999999999",
        "country_id": 1,
        "city": "Quito",
        "currency": "USD",
        "total_rooms": total_rooms,
        "description": "Hotel de prueba",
    }
    resp = await client.post("/api/auth/register-property/send-code", json=payload)
    assert resp.status_code == 200, resp.text
    assert "code" in captured, "el código de verificación no se capturó"
    resp = await client.post(
        "/api/auth/register-property/confirm-code",
        json={"email": payload["email"], "code": captured["code"]},
    )
    assert resp.status_code == 200, resp.text
    user = db.users.find_one({"email": payload["email"]})
    assert user is not None
    return {"user": user, "prop_id": user["assigned_prop_id"]}


async def _login_super_admin(client) -> None:
    resp = await client.post(
        "/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, resp.text


def _capture_notification(monkeypatch) -> dict:
    captured: dict = {}

    def _fake(
        email,
        *,
        hotel_name,
        plan_label,
        monthly_usd,
        due_date=None,
        payment_methods=None,
    ):
        captured.update(
            email=email,
            hotel_name=hotel_name,
            plan_label=plan_label,
            monthly_usd=monthly_usd,
            due_date=due_date,
            payment_methods=payment_methods or [],
        )

    monkeypatch.setattr(approval_service, "notify_registration_approved", _fake)
    return captured


# ── Approve crea suscripción + primera factura ─────────────────────────


async def test_approve_creates_subscription_and_first_invoice(
    client, db, monkeypatch, admin_user
):
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    captured = _capture_notification(monkeypatch)

    result = await _complete_onboarding(
        client, db, monkeypatch, email="sub@nuevo.hotel", username="sub_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    sub = db.subscriptions.find_one({"prop_id": prop_id})
    assert sub is not None
    assert sub["status"] == subs.STATUS_PENDING_PAYMENT
    assert sub["band"] == 2  # 20 habitaciones → Pequeño
    assert sub["billing_cycle"] == "monthly"
    assert sub["price_usd"] == 89

    inv = db.subscription_invoices.find_one({"subscription_id": sub["_id"]})
    assert inv is not None
    assert inv["status"] == subs.INVOICE_UNPAID
    assert inv["amount_usd"] == 89
    assert inv["due_date"] is not None

    # El email de aprobación gana el bloque de pago (plan + vencimiento + métodos).
    assert captured["plan_label"] == "Pequeño"
    assert captured["monthly_usd"] == 89
    assert captured["due_date"] is not None
    assert captured["payment_methods"]


async def test_approve_creates_exactly_one_subscription_and_invoice(
    client, db, monkeypatch, admin_user
):
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    _capture_notification(monkeypatch)

    result = await _complete_onboarding(
        client, db, monkeypatch, email="uno@nuevo.hotel", username="uno_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    assert db.subscriptions.count_documents({"prop_id": prop_id}) == 1
    assert db.subscription_invoices.count_documents({"prop_id": prop_id}) == 1


async def test_approve_subscription_failure_does_not_block_approval(
    client, db, monkeypatch, admin_user
):
    """Best-effort: si la suscripción falla, la aprobación NO se revierte."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)

    def _boom(**kwargs):
        raise RuntimeError("mongo roto (simulado)")

    monkeypatch.setattr(approval_service, "_ensure_subscription_on_approve", _boom)

    result = await _complete_onboarding(
        client, db, monkeypatch, email="falla@nuevo.hotel", username="falla_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["approval_status"] == _APPROVED
    assert hotel["is_operational"] is True
    assert db.subscriptions.count_documents({"prop_id": prop_id}) == 0


# ── Migración backfill (scripts/migrate_backfill_subscriptions.py) ─────


async def test_backfill_creates_active_subscription_from_price_band(db):
    from scripts.migrate_backfill_subscriptions import backfill_subscriptions

    owner_id = ObjectId()
    db.dim_hotels.insert_one(
        {
            "prop_id": 7,
            "hotel_name": "Hotel Legado",
            "approval_status": _APPROVED,
            "is_operational": True,
            "price_band": 4,
            "total_rooms_declared": 60,
            "owner_user_id": owner_id,
            "currency": "USD",
        }
    )
    result = backfill_subscriptions(db)
    assert result["created"] == 1

    sub = db.subscriptions.find_one({"prop_id": 7})
    assert sub is not None
    assert sub["status"] == subs.STATUS_ACTIVE
    assert sub["band"] == 4
    assert sub["price_usd"] == 229  # Grande 51–100 (fallback del catálogo)


async def test_backfill_is_idempotent(db):
    from scripts.migrate_backfill_subscriptions import backfill_subscriptions

    db.dim_hotels.insert_one(
        {
            "prop_id": 8,
            "hotel_name": "Hotel Repetido",
            "approval_status": _APPROVED,
            "price_band": 3,
            "total_rooms_declared": 40,
            "owner_user_id": ObjectId(),
            "currency": "USD",
        }
    )
    first = backfill_subscriptions(db)
    assert first["created"] == 1
    second = backfill_subscriptions(db)
    assert second["created"] == 0
    assert db.subscriptions.count_documents({"prop_id": 8}) == 1


async def test_backfill_recomputes_band_when_price_band_missing(db):
    from scripts.migrate_backfill_subscriptions import backfill_subscriptions

    db.dim_hotels.insert_one(
        {
            "prop_id": 9,
            "hotel_name": "Hotel Sin Banda",
            "approval_status": _APPROVED,
            "total_rooms_declared": 20,
            "owner_user_id": ObjectId(),
            "currency": "USD",
        }
    )
    backfill_subscriptions(db)
    sub = db.subscriptions.find_one({"prop_id": 9})
    assert sub["band"] == 2  # 20 habitaciones → Pequeño
    assert sub["price_usd"] == 89


async def test_backfill_skips_pending_and_already_backfilled(db):
    from scripts.migrate_backfill_subscriptions import backfill_subscriptions

    db.dim_hotels.insert_one(
        {
            "prop_id": 10,
            "hotel_name": "Hotel Pendiente",
            "approval_status": _PENDING,
            "total_rooms_declared": 30,
            "owner_user_id": ObjectId(),
        }
    )
    result = backfill_subscriptions(db)
    assert result["created"] == 0
    assert db.subscriptions.count_documents({"prop_id": 10}) == 0


async def test_backfill_dry_run_does_not_write(db):
    from scripts.migrate_backfill_subscriptions import backfill_subscriptions

    db.dim_hotels.insert_one(
        {
            "prop_id": 11,
            "hotel_name": "Hotel DryRun",
            "approval_status": _APPROVED,
            "price_band": 2,
            "total_rooms_declared": 15,
            "owner_user_id": ObjectId(),
            "currency": "USD",
        }
    )
    result = backfill_subscriptions(db, dry_run=True)
    assert result["created"] == 1
    assert db.subscriptions.count_documents({"prop_id": 11}) == 0
