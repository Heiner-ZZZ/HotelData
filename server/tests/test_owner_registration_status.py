"""UX-1 + UX-2 (backend) — experiencia del dueño pendiente de aprobación.

Spec: `docs/EXPERIENCIA_DUENO_PENDIENTE.md` (UX-1 backend de estado, UX-2
emails) sobre `docs/APROBACION_HOTELES_Y_PRICING.md` (§3 activación diferida,
§4 cola, §5 integración Fase 2, §6 bandas).

Cubre:
1. ``/api/auth/me`` expone ``approval_status`` + ``home_href`` condicional.
2. Middleware: dueño pendiente → 403 ``approval_pending`` en rutas de negocio,
   pero allowlist (``/me``, ``/registration-status``, ``/status``, logout,
   PATCH de edición) responde 200.
3. ``GET /api/auth/registration-status``: contrato completo (estado, datos
   declarados, banda sugerida, timeline desde audit_log).
4. ``PATCH /api/auth/register-property/me``: editar datos en pending y
   reenviar en changes_requested (vuelve a pending + banda recalculada).
5. ``POST .../reject`` con motivo obligatorio + gracia perezosa de 7 días
   (is_active=false + invalidación de sesiones al expirar).
6. ``POST .../request-changes`` con feedback obligatorio.
7. Emails: approve/reject/request-changes disparan las 3 plantillas.
8. Approve fija ``price_band`` desde la banda sugerida.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from src.app.modules.auth.routes import register_property as rp

pytestmark = pytest.mark.asyncio

GERENTE_PERMS = ["dashboard.read", "reservations.manage", "hotel.manage_roles"]
CATALOG_CODES = [*GERENTE_PERMS, "properties.approve"]

_PENDING = "pending_approval"
_APPROVED = "approved"
_REJECTED = "rejected"
_CHANGES = "changes_requested"

PENDING_HREF = "/alojamiento-en-revision"

# Banda B (11-25 habitaciones) → $89/mes ($69/mes pagando anual) según
# docs/APROBACION §6.2 (valores de adopción amigable recalibrados).
BAND_B = {
    "band": 2,
    "label": "Pequeño",
    "monthly_usd": 89,
    "annual_monthly_usd": 69,
    "min_rooms": 11,
    "max_rooms": 25,
}


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


async def _complete_onboarding(client, db, monkeypatch, *, email: str, username: str, rooms: int = 20) -> dict:
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
        "total_rooms": rooms,
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
    return {"user": user, "prop_id": user["assigned_prop_id"], "payload": payload}


async def _login(client, identifier: str, password: str = "Pass123!"):
    resp = await client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200, resp.text
    return resp


async def _login_super_admin(client) -> None:
    resp = await client.post(
        "/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, resp.text


def _sent_emails(monkeypatch) -> list[tuple[str, str, str]]:
    """Captura (to, subject, html) de send_email para assert de dispatch."""
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        "src.app.modules.property_approval.notifications.send_email",
        lambda to, subject, html: sent.append((to, subject, html)) or True,
    )
    return sent


async def _reject(client, prop_id: int, reason: str = "Datos no verificables"):
    resp = await client.post(
        f"/api/admin/property-registrations/{prop_id}/reject", json={"reason": reason}
    )
    return resp


# ── 1. /me payload ────────────────────────────────────────────────────────


async def test_me_exposes_approval_status_and_pending_home_href(client, db, monkeypatch):
    await _complete_onboarding(
        client, db, monkeypatch, email="me@nuevo.hotel", username="me_dueño"
    )
    await _login(client, "me_dueño")

    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["authenticated"] is True
    assert body["user"]["approval_status"] == _PENDING
    assert body["home_href"] == PENDING_HREF


async def test_me_approved_returns_normal_home_href(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    # Rol global hotel_partner (en producción lo siembra init_security_model);
    # get_role_name lo necesita para resolver el home_href del dueño aprobado.
    db.roles.insert_one(
        {
            "role_name": "hotel_partner",
            "display_name": "Dueño",
            "permissions": ["dashboard.read"],
            "is_system": True,
            "created_at": _now(),
        }
    )
    result = await _complete_onboarding(
        client, db, monkeypatch, email="meok@nuevo.hotel", username="meok_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)
    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    await _login(client, "meok_dueño")
    resp = await client.get("/api/auth/me")
    body = resp.json()
    assert body["user"]["approval_status"] == _APPROVED
    assert body["home_href"] == "/management"


# ── 2. Middleware: allowlist ──────────────────────────────────────────────


async def test_pending_owner_blocked_on_business_routes(client, db, monkeypatch):
    await _complete_onboarding(
        client, db, monkeypatch, email="blk@nuevo.hotel", username="blk_dueño"
    )
    await _login(client, "blk_dueño")

    resp = await client.get("/api/management/products")
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body.get("code") == "approval_pending"
    assert body.get("approval_status") == _PENDING
    assert body.get("redirect") == PENDING_HREF


async def test_pending_owner_allowlist_paths_ok(client, db, monkeypatch):
    await _complete_onboarding(
        client, db, monkeypatch, email="alw@nuevo.hotel", username="alw_dueño"
    )
    await _login(client, "alw_dueño")

    assert (await client.get("/api/auth/me")).status_code == 200
    assert (await client.get("/api/auth/status")).status_code == 200
    resp = await client.get("/api/auth/registration-status")
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval_status"] == _PENDING


async def test_rejected_owner_gets_approval_rejected_code(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="rej@nuevo.hotel", username="rej_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)
    resp = await _reject(client, prop_id, reason="Duplicado con otro registro")
    assert resp.status_code == 200, resp.text

    await _login(client, "rej_dueño")
    resp = await client.get("/api/management/products")
    assert resp.status_code == 403
    assert resp.json().get("code") == "approval_rejected"


# ── 3. GET /api/auth/registration-status ─────────────────────────────────


async def test_registration_status_full_contract(client, db, monkeypatch):
    await _complete_onboarding(
        client, db, monkeypatch, email="status@nuevo.hotel", username="status_dueño"
    )
    await _login(client, "status_dueño")

    resp = await client.get("/api/auth/registration-status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["approval_status"] == _PENDING
    assert body["rejected_reason"] is None
    assert body["feedback"] is None
    assert body["submitted_at"] is not None
    assert body["status_changed_at"] is not None

    prop = body["property"]
    assert prop["name"] == "Hotel Nuevo"
    assert prop["type"] == "hotel"
    assert prop["city"] == "Quito"
    assert prop["country"] == "Ecuador"
    assert prop["total_rooms"] == 20
    assert prop["currency"] == "USD"
    assert prop["contact_phone"] == "+593999999999"
    # Geolocalización (Nivel 2): sin dirección/coords en el onboarding base.
    assert prop["address"] == ""
    assert prop["latitude"] is None
    assert prop["longitude"] is None

    band = body["suggested_band"]
    assert band["band"] == BAND_B["band"]
    assert band["label"] == BAND_B["label"]
    assert band["monthly_usd"] == BAND_B["monthly_usd"]
    assert band["annual_monthly_usd"] == BAND_B["annual_monthly_usd"]

    assert isinstance(body["timeline"], list)
    assert body["timeline"][0]["event"] == "submitted"
    assert body["timeline"][0]["detail"] == "Registro recibido"


async def test_registration_status_uses_pricing_plans_catalog(client, db, monkeypatch):
    """Si pricing_plans está sembrado, la banda sugerida viene del catálogo
    (incluido el precio anual del catálogo)."""
    db.pricing_plans.insert_one(
        {
            "band": 2,
            "label": "Boutique",
            "min_rooms": 11,
            "max_rooms": 25,
            "monthly_usd": 149,
            "annual_monthly_usd": 109,
            "is_active": True,
        }
    )
    await _complete_onboarding(
        client, db, monkeypatch, email="cat@nuevo.hotel", username="cat_dueño"
    )
    await _login(client, "cat_dueño")

    resp = await client.get("/api/auth/registration-status")
    assert resp.status_code == 200, resp.text
    band = resp.json()["suggested_band"]
    assert band["label"] == "Boutique"
    assert band["monthly_usd"] == 149
    assert band["annual_monthly_usd"] == 109


async def test_registration_status_rejected_includes_reason(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="rz@nuevo.hotel", username="rz_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)
    await _reject(client, prop_id, reason="Teléfono no verificable")

    await _login(client, "rz_dueño")
    resp = await client.get("/api/auth/registration-status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["approval_status"] == _REJECTED
    assert body["rejected_reason"] == "Teléfono no verificable"
    assert body["timeline"][-1]["event"] == "rejected"


# ── 4. PATCH /api/auth/register-property/me ───────────────────────────────


async def test_patch_edits_pending_data_in_place(client, db, monkeypatch):
    result = await _complete_onboarding(
        client, db, monkeypatch, email="edit@nuevo.hotel", username="edit_dueño"
    )
    prop_id = result["prop_id"]
    await _login(client, "edit_dueño")

    resp = await client.patch(
        "/api/auth/register-property/me",
        json={
            "property_name": "Hotel Renombrado",
            "property_type": "boutique",
            "contact_phone": "+593911111111",
            "city": "Cuenca",
            "total_rooms": 30,
            "description": "Editado en pending",
        },
    )
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["hotel_name"] == "Hotel Renombrado"
    assert hotel["property_type"] == "boutique"
    assert hotel["total_rooms_declared"] == 30
    assert hotel["approval_status"] == _PENDING  # el estado NO cambia en pending


async def test_patch_stores_address_and_coords(client, db, monkeypatch):
    result = await _complete_onboarding(
        client, db, monkeypatch, email="geo@nuevo.hotel", username="geo_dueño"
    )
    prop_id = result["prop_id"]
    await _login(client, "geo_dueño")

    resp = await client.patch(
        "/api/auth/register-property/me",
        json={
            "property_name": "Hotel con mapa",
            "property_type": "hotel",
            "contact_phone": "+593999999999",
            "city": "Quito",
            "total_rooms": 20,
            "description": "",
            "address": "Av. Amazonas N37-61",
            "latitude": -0.1807,
            "longitude": -78.4678,
        },
    )
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["address"] == "Av. Amazonas N37-61"
    assert hotel["latitude"] == -0.1807
    assert hotel["longitude"] == -78.4678

    status = (await client.get("/api/auth/registration-status")).json()
    assert status["property"]["address"] == "Av. Amazonas N37-61"
    assert status["property"]["latitude"] == -0.1807
    assert status["property"]["longitude"] == -78.4678


async def test_patch_from_changes_requested_resubmits(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="rs@nuevo.hotel", username="rs_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)
    resp = await client.post(
        f"/api/admin/property-registrations/{prop_id}/request-changes",
        json={"feedback": "El teléfono no parece válido"},
    )
    assert resp.status_code == 200, resp.text
    assert db.dim_hotels.find_one({"prop_id": prop_id})["approval_status"] == _CHANGES

    await _login(client, "rs_dueño")
    resp = await client.patch(
        "/api/auth/register-property/me",
        json={
            "property_name": "Hotel Nuevo",
            "property_type": "hotel",
            "contact_phone": "+593912345678",
            "city": "Quito",
            "total_rooms": 35,
            "description": "Corregido",
        },
    )
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["contact_phone"] == "+593912345678"
    assert hotel["total_rooms_declared"] == 35
    assert hotel["approval_status"] == _PENDING  # resubmitted → vuelve a pendiente
    owner = db.users.find_one({"email": "rs@nuevo.hotel"})
    assert owner["approval_status"] == _PENDING

    # La banda sugerida se recalcula al vuelo (35 hab → banda C $149/mes).
    await _login(client, "rs_dueño")
    status = (await client.get("/api/auth/registration-status")).json()
    assert status["suggested_band"]["monthly_usd"] == 149
    # El timeline gana el evento resubmitted.
    assert any(e["event"] == "resubmitted" for e in status["timeline"])


async def test_patch_approved_conflict(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="pa@nuevo.hotel", username="pa_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)
    assert (await client.post(f"/api/admin/property-registrations/{prop_id}/approve")).status_code == 200

    await _login(client, "pa_dueño")
    resp = await client.patch(
        "/api/auth/register-property/me",
        json={
            "property_name": "Hotel Nuevo",
            "property_type": "hotel",
            "contact_phone": "+593999999999",
            "city": "Quito",
            "total_rooms": 20,
            "description": "",
        },
    )
    assert resp.status_code == 409


async def test_patch_invalid_payload_rejected(client, db, monkeypatch):
    await _complete_onboarding(
        client, db, monkeypatch, email="bad@nuevo.hotel", username="bad_dueño"
    )
    await _login(client, "bad_dueño")

    resp = await client.patch(
        "/api/auth/register-property/me",
        json={
            "property_name": "X",
            "property_type": "nave-espacial",
            "contact_phone": "123",
            "city": "Q",
            "total_rooms": 0,
            "description": "",
        },
    )
    assert resp.status_code == 400


async def test_patch_requires_auth(client):
    resp = await client.patch(
        "/api/auth/register-property/me",
        json={
            "property_name": "Hotel Nuevo",
            "property_type": "hotel",
            "contact_phone": "+593999999999",
            "city": "Quito",
            "total_rooms": 20,
            "description": "",
        },
    )
    assert resp.status_code in (401, 303)


# ── 5. Reject: motivo + gracia perezosa de 7 días ─────────────────────────


async def test_reject_requires_reason(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="rr@nuevo.hotel", username="rr_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)

    resp = await _reject(client, prop_id, reason="   ")
    assert resp.status_code == 400
    assert db.dim_hotels.find_one({"prop_id": prop_id})["approval_status"] == _PENDING


async def test_reject_sets_state_but_keeps_active_during_grace(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="grac@nuevo.hotel", username="grac_dueño"
    )
    prop_id = result["prop_id"]
    owner = result["user"]
    await _login_super_admin(client)

    resp = await _reject(client, prop_id, reason="Datos falsos")
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["approval_status"] == _REJECTED
    assert hotel["rejected_reason"] == "Datos falsos"
    owner_after = db.users.find_one({"_id": owner["_id"]})
    assert owner_after["approval_status"] == _REJECTED
    assert owner_after["rejected_reason"] == "Datos falsos"
    # La gracia: is_active permanece true (el dueño puede ver el motivo).
    assert owner_after["is_active"] is True

    # Sesión restringida pero viva: registration-status sigue respondiendo.
    await _login(client, "grac_dueño")
    status = (await client.get("/api/auth/registration-status")).json()
    assert status["approval_status"] == _REJECTED
    assert status["rejected_reason"] == "Datos falsos"


async def test_rejection_grace_expires_and_deactivates(client, db, monkeypatch, admin_user):
    """Gracia perezosa: a los 7 días, la primera interacción desactiva la
    cuenta e invalida las sesiones (sin job background)."""
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="exp@nuevo.hotel", username="exp_dueño"
    )
    prop_id = result["prop_id"]
    owner = result["user"]
    await _login_super_admin(client)
    await _reject(client, prop_id, reason="Política de duplicados")

    await _login(client, "exp_dueño")
    # Backdatear rejected_at más allá de la gracia (8 días).
    db.users.update_one(
        {"_id": owner["_id"]},
        {"$set": {"rejected_at": _now() - timedelta(days=8)}},
    )
    db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {"$set": {"rejected_at": _now() - timedelta(days=8)}},
    )

    resp = await client.get("/api/auth/registration-status")
    assert resp.status_code == 401, resp.text

    owner_after = db.users.find_one({"_id": owner["_id"]})
    assert owner_after["is_active"] is False
    assert db.user_sessions.count_documents(
        {"user_id": owner["_id"], "is_active": True}
    ) == 0


async def test_reject_approved_conflict(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="ra@nuevo.hotel", username="ra_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)
    assert (await client.post(f"/api/admin/property-registrations/{prop_id}/approve")).status_code == 200
    resp = await _reject(client, prop_id)
    assert resp.status_code == 409


# ── 6. Request-changes ────────────────────────────────────────────────────


async def test_request_changes_requires_feedback(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="rc@nuevo.hotel", username="rc_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)

    resp = await client.post(
        f"/api/admin/property-registrations/{prop_id}/request-changes", json={"feedback": ""}
    )
    assert resp.status_code == 400
    assert db.dim_hotels.find_one({"prop_id": prop_id})["approval_status"] == _PENDING


async def test_request_changes_sets_state_and_feedback(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="chg@nuevo.hotel", username="chg_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)

    resp = await client.post(
        f"/api/admin/property-registrations/{prop_id}/request-changes",
        json={"feedback": "Declara el número real de habitaciones"},
    )
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["approval_status"] == _CHANGES
    assert hotel["feedback"] == "Declara el número real de habitaciones"
    owner = db.users.find_one({"email": "chg@nuevo.hotel"})
    assert owner["approval_status"] == _CHANGES

    await _login(client, "chg_dueño")
    status = (await client.get("/api/auth/registration-status")).json()
    assert status["approval_status"] == _CHANGES
    assert status["feedback"] == "Declara el número real de habitaciones"


# ── 7. Emails (dispatch + contenido) ──────────────────────────────────────


async def test_approve_sends_approved_email_with_plan(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    sent = _sent_emails(monkeypatch)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="mail@nuevo.hotel", username="mail_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)

    resp = await client.post(f"/api/admin/property-registrations/{prop_id}/approve")
    assert resp.status_code == 200, resp.text

    email = next((e for e in sent if "aprobado" in e[1].lower()), None)
    assert email is not None, f"no se envió email de aprobación: {sent}"
    to, subject, html = email
    assert to == "mail@nuevo.hotel"
    assert "Tu alojamiento fue aprobado" in subject
    assert "Hotel Nuevo" in html
    assert "Pequeño" in html  # banda B → plan sugerido

    # Approve fija price_band desde la banda sugerida.
    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    assert hotel["price_band"] == BAND_B["band"]
    assert hotel["price_band_monthly_usd"] == BAND_B["monthly_usd"]


async def test_reject_sends_rejected_email_with_reason(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    sent = _sent_emails(monkeypatch)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="mailr@nuevo.hotel", username="mailr_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)

    await _reject(client, prop_id, reason="Datos no verificables")

    email = next((e for e in sent if "no fue aprobado" in e[1].lower()), None)
    assert email is not None, f"no se envió email de rechazo: {sent}"
    to, subject, html = email
    assert to == "mailr@nuevo.hotel"
    assert "Tu registro de alojamiento no fue aprobado" in subject
    assert "Datos no verificables" in html


async def test_request_changes_sends_feedback_email(client, db, monkeypatch, admin_user):
    _seed_permission_catalog(db)
    _seed_gerente_template(db)
    sent = _sent_emails(monkeypatch)
    result = await _complete_onboarding(
        client, db, monkeypatch, email="mailc@nuevo.hotel", username="mailc_dueño"
    )
    prop_id = result["prop_id"]
    await _login_super_admin(client)

    resp = await client.post(
        f"/api/admin/property-registrations/{prop_id}/request-changes",
        json={"feedback": "El teléfono no parece válido"},
    )
    assert resp.status_code == 200, resp.text

    email = next((e for e in sent if "revisa tu registro" in e[1].lower()), None)
    assert email is not None, f"no se envió email de cambios: {sent}"
    to, subject, html = email
    assert to == "mailc@nuevo.hotel"
    assert "Revisa tu registro" in subject
    assert "El teléfono no parece válido" in html
