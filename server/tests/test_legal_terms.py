"""Términos y Condiciones versionados (colección ``legal_documents``).

Verifica el modelo completo de aceptación de términos:

1. ``GET /api/public/legal`` sirve la versión ACTIVA de un doc_type (sin auth).
2. ``POST /api/admin/legal/publish`` publica una versión nueva y desactiva la
   anterior (el histórico conserva las versiones viejas).
3. El registro de huésped exige la versión vigente: la aceptación queda
   estampada en el usuario (``terms_guest_version`` + ``terms_accepted_at``),
   y una versión vencida se rechaza con 409.
4. El onboarding de anfitrión (send-code → confirm-code) hace lo mismo para
   ``terms_hotel_partner``: validación en send-code, estampado en el usuario y
   en ``dim_hotels`` al confirmar.
5. Back-compat: un payload SIN ``accepted_terms_version`` sigue funcionando
   (no rompe tests/seeds legacy).
"""

from __future__ import annotations

import pytest

from src.app.modules.legal.service import ensure_legal_collections, publish_document
from src.app.modules.auth.routes import register_property as rp
from src.database.connection import get_database

pytestmark = pytest.mark.asyncio

# Idempotente; el conftest limpia la colección por test pero los índices
# necesarios se aseguran una sola vez por proceso.
ensure_legal_collections()


def _publish(db, doc_type: str, version: int | None = None) -> dict:
    """Publica una versión de prueba del documento indicado."""
    return publish_document(
        db,
        doc_type=doc_type,
        title=f"{doc_type} v{version if version is not None else 'auto'}",
        sections=[{"heading": "1. Aceptación", "body": "Al usar la plataforma aceptas estos términos."}],
        version=version,
        updated_by="test",
    )


# ─── Public endpoint ────────────────────────────────────────────────────


async def test_public_legal_404_when_nothing_published(client):
    resp = await client.get("/api/public/legal?doc_type=terms_guest")
    assert resp.status_code == 404, resp.text


async def test_public_legal_invalid_doc_type(client, db):
    resp = await client.get("/api/public/legal?doc_type=no_existe")
    assert resp.status_code == 400, resp.text


async def test_public_legal_serves_active_version(client, db):
    _publish(db, "terms_guest", version=1)
    _publish(db, "terms_guest", version=2)

    resp = await client.get("/api/public/legal?doc_type=terms_guest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == 2
    assert body["doc_type"] == "terms_guest"
    assert body["sections"][0]["heading"] == "1. Aceptación"
    assert body["title"]


async def test_public_legal_no_auth_required(client, db):
    """El endpoint es público: sin login debe responder 200."""
    _publish(db, "terms_guest", version=1)
    resp = await client.get("/api/public/legal?doc_type=terms_guest")
    assert resp.status_code == 200, resp.text


# ─── Admin publish ──────────────────────────────────────────────────────


async def test_admin_publish_requires_permission(client, db, admin_user):
    resp = await client.post(
        "/api/admin/legal/publish",
        json={
            "doc_type": "terms_guest",
            "title": "Términos v1",
            "sections": [{"heading": "1", "body": "texto"}],
        },
    )
    # Sin sesión de admin → 401/403
    assert resp.status_code in (401, 403), resp.text


async def test_admin_publish_activates_and_keeps_history(client, db, admin_user):
    await client.post("/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"})
    _publish(db, "privacy_policy", version=1)

    resp = await client.post(
        "/api/admin/legal/publish",
        json={
            "doc_type": "privacy_policy",
            "title": "Política v2",
            "sections": [{"heading": "1", "body": "nuevo texto"}],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["document"]["version"] == 2

    # El histórico conserva ambas versiones; solo la v2 queda activa.
    hist = list(db.legal_documents.find({"doc_type": "privacy_policy"}))
    assert len(hist) == 2
    versions = {int(d["version"]): d["is_active"] for d in hist}
    assert versions == {1: False, 2: True}


# ─── Guest registration ─────────────────────────────────────────────────


async def test_register_guest_stamps_terms_version(client, db):
    _publish(db, "terms_guest", version=1)

    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "huesped_terms",
            "email": "huesped@terms.com",
            "password": "Secret123!",
            "display_name": "Huésped",
            "accepted_terms_version": 1,
        },
    )
    assert resp.status_code == 200, resp.text

    user = db.users.find_one({"username": "huesped_terms"})
    assert user is not None
    assert user["terms_guest_version"] == 1
    assert user["terms_accepted_at"] is not None


async def test_register_guest_rejects_stale_terms_version(client, db):
    _publish(db, "terms_guest", version=1)
    _publish(db, "terms_guest", version=2)

    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "huesped_stale",
            "email": "stale@terms.com",
            "password": "Secret123!",
            "accepted_terms_version": 1,
        },
    )
    assert resp.status_code == 409, resp.text
    assert "v2" in resp.json()["detail"]

    # El usuario NO debe existir tras el rechazo.
    assert db.users.find_one({"username": "huesped_stale"}) is None


async def test_register_guest_without_terms_backcompat(client, db):
    """Sin accepted_terms_version el registro sigue funcionando (back-compat)."""
    _publish(db, "terms_guest", version=1)

    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "huesped_sin_terms",
            "email": "sin@terms.com",
            "password": "Secret123!",
            "display_name": "Sin Términos",
        },
    )
    assert resp.status_code == 200, resp.text
    user = db.users.find_one({"username": "huesped_sin_terms"})
    assert user is not None
    assert "terms_guest_version" not in user


async def test_register_guest_email_first_flow_stamps_terms(client, db, monkeypatch):
    """Flujo send-code → confirm-code: la versión se valida en send-code y se
    estampa en el usuario al confirmar (sin re-enviarla en confirm-code)."""
    _publish(db, "terms_guest", version=1)

    captured: dict = {}

    def _fake_send(email: str, display_name: str, code: str) -> None:
        captured["code"] = code

    monkeypatch.setattr("src.app.modules.auth.routes.register._send_verification_code", _fake_send)

    resp = await client.post(
        "/api/auth/register",
        json={
            "username": "huesped_emailfirst",
            "email": "ef@terms.com",
            "password": "Secret123!",
            "send_verification": True,
            "accepted_terms_version": 1,
        },
    )
    assert resp.status_code == 200, resp.text
    assert "code" in captured

    resp = await client.post(
        "/api/auth/confirm-code",
        json={
            "email": "ef@terms.com",
            "code": captured["code"],
            "username": "huesped_emailfirst",
            "password": "Secret123!",
        },
    )
    assert resp.status_code == 200, resp.text

    user = db.users.find_one({"username": "huesped_emailfirst"})
    assert user is not None
    assert user["terms_guest_version"] == 1
    assert user["terms_accepted_at"] is not None


# ─── Property owner onboarding ──────────────────────────────────────────


def _owner_payload(email: str, username: str, **extra) -> dict:
    payload = {
        "email": email,
        "username": username,
        "password": "Pass123!",
        "user_display_name": "Dueño Terms",
        "property_name": "Hotel Términos",
        "property_type": "hotel",
        "contact_phone": "+593999999999",
        "country_id": 1,
        "city": "Quito",
        "currency": "USD",
        "total_rooms": 20,
        "description": "Hotel de prueba",
    }
    payload.update(extra)
    return payload


def _seed_catalogs(db) -> None:
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


async def test_owner_onboarding_stamps_terms_version(client, db, monkeypatch):
    _seed_catalogs(db)
    _publish(db, "terms_hotel_partner", version=1)
    captured = _capture_code(monkeypatch)

    payload = _owner_payload("owner_terms@hotel.com", "owner_terms", accepted_terms_version=1)
    resp = await client.post("/api/auth/register-property/send-code", json=payload)
    assert resp.status_code == 200, resp.text
    assert "code" in captured

    resp = await client.post(
        "/api/auth/register-property/confirm-code",
        json={"email": payload["email"], "code": captured["code"]},
    )
    assert resp.status_code == 200, resp.text

    user = db.users.find_one({"email": payload["email"]})
    assert user is not None
    assert user["terms_hotel_partner_version"] == 1
    assert user["terms_accepted_at"] is not None

    hotel = db.dim_hotels.find_one({"prop_id": user["assigned_prop_id"]})
    assert hotel is not None
    assert hotel["terms_hotel_partner_version"] == 1
    assert hotel["terms_accepted_at"] is not None


async def test_owner_onboarding_rejects_stale_terms_version(client, db, monkeypatch):
    _seed_catalogs(db)
    _publish(db, "terms_hotel_partner", version=1)
    _publish(db, "terms_hotel_partner", version=2)

    payload = _owner_payload("owner_stale@hotel.com", "owner_stale", accepted_terms_version=1)
    resp = await client.post("/api/auth/register-property/send-code", json=payload)
    assert resp.status_code == 409, resp.text
    assert "v2" in resp.json()["detail"]

    # Sin pendiente creado.
    assert db.pending_registrations.find_one({"email": payload["email"]}) is None


async def test_owner_onboarding_without_terms_backcompat(client, db, monkeypatch):
    """Sin accepted_terms_version el onboarding sigue funcionando (back-compat)."""
    _seed_catalogs(db)
    _publish(db, "terms_hotel_partner", version=1)
    captured = _capture_code(monkeypatch)

    payload = _owner_payload("owner_none@hotel.com", "owner_none")
    resp = await client.post("/api/auth/register-property/send-code", json=payload)
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/api/auth/register-property/confirm-code",
        json={"email": payload["email"], "code": captured["code"]},
    )
    assert resp.status_code == 200, resp.text

    user = db.users.find_one({"email": payload["email"]})
    assert user is not None
    assert "terms_hotel_partner_version" not in user
