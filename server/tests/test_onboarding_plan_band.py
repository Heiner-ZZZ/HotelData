"""Validación total_rooms → banda en el onboarding (PLAN_SUSCRIPCION_Y_PAGOS.md §12).

El plan no es de libre elección: se deriva de las habitaciones declaradas. El
backend rechaza un ``plan_band`` declarado que no coincide con la banda derivada
de ``total_rooms`` (y rechaza valores de banda inválidos).
"""

from __future__ import annotations

import pytest

from src.app.modules.auth.routes import register_property as rp

pytestmark = pytest.mark.asyncio


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


def _payload(**overrides) -> dict:
    base = {
        "email": "plan@nuevo.hotel",
        "username": "plan_dueño",
        "password": "Pass123!",
        "user_display_name": "Dueño Plan",
        "property_name": "Hotel Plan",
        "property_type": "hotel",
        "contact_phone": "+593999999999",
        "country_id": 1,
        "city": "Quito",
        "currency": "USD",
        "total_rooms": 20,  # → banda 2 (Pequeño)
        "description": "Hotel de prueba",
    }
    base.update(overrides)
    return base


async def test_send_code_rejects_mismatched_plan_band(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload(plan_band=4)
    )
    assert resp.status_code == 400
    assert "no corresponde" in resp.json()["detail"]
    # No deja un registro pendiente con datos inconsistentes.
    assert db.pending_registrations.count_documents({"email": "plan@nuevo.hotel"}) == 0


async def test_send_code_accepts_matching_plan_band(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload(plan_band=2)
    )
    assert resp.status_code == 200, resp.text
    pending = db.pending_registrations.find_one({"email": "plan@nuevo.hotel"})
    assert pending["pending_property"]["suggested_band"]["band"] == 2
    assert pending["pending_property"]["suggested_band"]["label"] == "Pequeño"


async def test_send_code_without_plan_band_still_derives_band(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload()
    )
    assert resp.status_code == 200, resp.text
    pending = db.pending_registrations.find_one({"email": "plan@nuevo.hotel"})
    assert pending["pending_property"]["suggested_band"]["band"] == 2  # derivada


async def test_send_code_rejects_out_of_range_plan_band(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload(plan_band=7)
    )
    assert resp.status_code == 400
    assert "plan" in resp.json()["detail"].lower()


async def test_send_code_rejects_non_numeric_plan_band(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload(plan_band="grande")
    )
    assert resp.status_code == 400
    assert "plan" in resp.json()["detail"].lower()


# ── Ciclo de facturación + método de pago (Fase 6, §14.1) ─────────────


async def test_send_code_stores_billing_cycle_and_method(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code",
        json=_payload(billing_cycle="annual", payment_method="bank_transfer"),
    )
    assert resp.status_code == 200, resp.text
    pending = db.pending_registrations.find_one({"email": "plan@nuevo.hotel"})
    assert pending["pending_property"]["billing_cycle"] == "annual"
    assert pending["pending_property"]["payment_method"] == "bank_transfer"


async def test_send_code_defaults_billing_cycle_monthly(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload()
    )
    assert resp.status_code == 200, resp.text
    pending = db.pending_registrations.find_one({"email": "plan@nuevo.hotel"})
    assert pending["pending_property"]["billing_cycle"] == "monthly"
    assert pending["pending_property"]["payment_method"] is None


async def test_send_code_rejects_invalid_billing_cycle(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload(billing_cycle="weekly")
    )
    assert resp.status_code == 400
    assert "ciclo" in resp.json()["detail"].lower()


async def test_send_code_rejects_invalid_payment_method(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    resp = await client.post(
        "/api/auth/register-property/send-code", json=_payload(payment_method="credit_card")
    )
    assert resp.status_code == 400
    assert "método de pago" in resp.json()["detail"].lower()
