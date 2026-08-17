"""Fase 1 del gate de aprobación de hoteles (docs/APROBACION_HOTELES_Y_PRICING.md §3-§5).

Cubre:
- ``confirm-code`` crea al dueño y al hotel en estado ``pending_approval``
  (el hotel NO queda operativo: ``is_operational=false``, ``published=false``).
- Cola del admin bajo ``/api/admin/property-registrations`` (GET list, GET
  detail, POST approve) gateada con el permiso nuevo ``properties.approve``.
- ``approve`` activa el hotel + clona el ``hotel_role`` desde la plantilla
  ``gerente_hotel`` + crea la ``role_assignment`` del dueño (reutilizando la
  Fase 2 de hotel_permissions), satisfaciendo la invariante >= 1 admin.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId
from passlib.context import CryptContext

from src.app.modules.auth.routes import register_property as rp
from src.app.security.permissions import user_has_permission

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Catálogo mínimo que el approve necesita: los códigos de la plantilla
# gerente_hotel (heredados por el clon) + el permiso de la cola.
GERENTE_PERMS = ["dashboard.read", "reservations.manage", "hotel.manage_roles"]
CATALOG_CODES = [*GERENTE_PERMS, "properties.approve"]

_PENDING = "pending_approval"
_APPROVED = "approved"


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    client, db, monkeypatch, *,
    email: str,
    username: str,
    billing_cycle: str = "monthly",
    payment_method: str | None = None,
) -> dict:
    """send-code + confirm-code → devuelve el dueño creado y su prop_id."""
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
        "total_rooms": 20,
        "description": "Hotel de prueba",
        "billing_cycle": billing_cycle,
    }
    if payment_method:
        payload["payment_method"] = payment_method
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


# ── confirm-code → pending_approval ─────────────────────────────────────


async def test_confirm_code_creates_pending_owner_and_hotel(client, db, monkeypatch):
    """RED: el onboarding ya no activa — dueño y hotel nacen en pending_approval."""
    result = await _complete_onboarding(
        client, db, monkeypatch, email="dueño@nuevo.hotel", username="dueño_nuevo"
    )
    user = result["user"]
    prop_id = result["prop_id"]
    assert user["approval_status"] == _PENDING

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel is not None
    assert hotel["approval_status"] == _PENDING
    assert hotel["is_operational"] is False
    assert hotel["published"] is False


# ── Cola del admin: gates ───────────────────────────────────────────────


async def test_queue_requires_auth(client):
    resp = await client.get("/api/admin/property-registrations")
    assert resp.status_code == 401


async def test_queue_forbidden_without_properties_approve(client, db):
    """Un usuario sin properties.approve (recepcionista sin rol sembrado) → 403."""
    db.users.insert_one(
        {
            "username": "sin_permiso",
            "email": "sin_permiso@hotel.local",
            "display_name": "Sin Permiso",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "recepcionista",
            "role_ids": [],
            "assigned_hotels": [],
            "is_active": True,
            "created_at": _now(),
        }
    )
    resp = await client.post(
        "/api/auth/login", json={"identifier": "sin_permiso", "password": "Pass123!"}
    )
    assert resp.status_code == 200, resp.text
    resp = await client.get("/api/admin/property-registrations")
    assert resp.status_code == 403


# ── Cola del admin: list + detail ───────────────────────────────────────


async def test_queue_list_returns_pending_registration(
    client, db, monkeypatch, admin_user
):
    """RED: la cola lista el registro pendiente con los datos declarados."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="cola@nuevo.hotel", username="cola_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.get("/api/admin/property-registrations")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == _PENDING
    item = next(i for i in data["items"] if i["prop_id"] == prop_id)
    assert item["hotel_name"] == "Hotel Nuevo"
    assert item["total_rooms_declared"] == 20
    assert item["owner_username"] == "cola_dueño"
    assert item["approval_status"] == _PENDING


async def test_queue_detail_returns_full_registration(
    client, db, monkeypatch, admin_user
):
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="detalle@nuevo.hotel", username="detalle_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.get(f"/api/admin/property-registrations/{prop_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["prop_id"] == prop_id
    assert body["property_type"] == "hotel"
    assert body["city"] == "Quito"
    assert body["currency"] == "USD"
    assert body["contact_phone"] == "+593999999999"
    assert body["owner_username"] == "detalle_dueño"


# ── Approve ─────────────────────────────────────────────────────────────


async def test_approve_uses_onboarding_billing_cycle_and_method(
    client, db, monkeypatch, admin_user
):
    """Fase 6 (§14.1): el ciclo y método elegidos en el onboarding llegan a la suscripción."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch,
        email="ciclo@nuevo.hotel",
        username="ciclo_dueño",
        billing_cycle="annual",
        payment_method="bank_transfer",
    )
    prop_id = result["prop_id"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    sub = db.subscriptions.find_one({"prop_id": prop_id})
    assert sub is not None
    assert sub["billing_cycle"] == "annual"
    assert sub["payment_method"] == "bank_transfer"


async def test_approve_activates_hotel_and_owner(client, db, monkeypatch, admin_user):
    """RED: approve activa el hotel (operational/published) y al dueño."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="aprobar@nuevo.hotel", username="aprobar_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["approval_status"] == _APPROVED
    assert hotel["is_operational"] is True
    assert hotel["published"] is True

    owner = db.users.find_one({"email": "aprobar@nuevo.hotel"})
    assert owner["approval_status"] == _APPROVED


async def test_approve_clones_gerente_role_and_assigns_owner(
    client, db, monkeypatch, admin_user
):
    """RED: approve clona el hotel_role del gerente y asigna al dueño (Fase 2)."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    template_id = _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="rol@nuevo.hotel", username="rol_dueño"
    )
    prop_id = result["prop_id"]
    owner = result["user"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["prop_id"] == prop_id
    assert body["hotel_role_id"]
    assert body["assignment_id"]

    role = db.hotel_roles.find_one({"prop_id": prop_id, "name": "gerente_hotel"})
    assert role is not None
    assert role["based_on_role_id"] == template_id
    assert role["is_active"] is True
    assert "hotel.manage_roles" in role["permissions"]

    assignment = db.role_assignments.find_one(
        {"user_id": owner["_id"], "prop_id": prop_id}
    )
    assert assignment is not None
    assert assignment["role_id"] == role["_id"]

    # Invariante >= 1 admin: el dueño tiene hotel.manage_roles en su hotel.
    assert user_has_permission(db, owner, "hotel.manage_roles", prop_id=prop_id) is True


async def test_approve_twice_conflict(client, db, monkeypatch, admin_user):
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="doble@nuevo.hotel", username="doble_dueño"
    )
    prop_id = result["prop_id"]

    first = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert first.status_code == 200, first.text
    second = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert second.status_code == 409


async def test_approve_missing_template_rejected(client, db, monkeypatch, admin_user):
    """Sin plantilla gerente_hotel en el catálogo → 400 explícito, no 500."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="sinplantilla@nuevo.hotel", username="sp_dueño"
    )
    prop_id = result["prop_id"]

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 400
    assert "gerente_hotel" in resp.json()["detail"]
    # El hotel sigue pendiente (la falla no deja estado parcial).
    assert db.dim_hotels.find_one({"prop_id": prop_id})["approval_status"] == _PENDING
    assert db.hotel_roles.count_documents({"prop_id": prop_id}) == 0


async def test_approve_unknown_prop_404(client, db, monkeypatch, admin_user):
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    resp = await client.post("/api/admin/property-registrations/999999/approve")
    assert resp.status_code == 404


async def test_approve_owner_without_hotel_membership_rejected(
    client, db, monkeypatch, admin_user
):
    """Hardening de atomicidad: si el dueño pierde assigned_hotels, el approve
    falla 400 ANTES de clonar — sin rol huérfano y sin estado parcial."""
    await _login_super_admin(client)
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="sinhotel@nuevo.hotel", username="sinhotel_dueño"
    )
    prop_id = result["prop_id"]
    db.users.update_one(
        {"_id": result["user"]["_id"]}, {"$set": {"assigned_hotels": []}}
    )

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 400
    assert db.dim_hotels.find_one({"prop_id": prop_id})["approval_status"] == _PENDING
    assert db.hotel_roles.count_documents({"prop_id": prop_id}) == 0
    assert db.role_assignments.count_documents({"prop_id": prop_id}) == 0
