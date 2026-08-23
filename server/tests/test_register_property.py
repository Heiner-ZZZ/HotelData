"""Onboarding de propiedades: el hotel_partner auto-registrado debe quedar
acotado a su propio hotel.

Hallazgo de seguridad (2026-08): el usuario creado por
``register_property.confirm_code`` quedaba con ``assigned_prop_id`` pero SIN
``assigned_hotels``. Como ``hotel_filter`` filtra solo por ``assigned_hotels``
(vacío = sin restricción), un dueño auto-registrado veía TODOS los hoteles
del sistema. Este archivo verifica el fix: el onboarding escribe
``assigned_hotels: [prop_id]`` y el alcance resultante es de un solo hotel.

El flujo se ejercita de punta a punta contra Mongo real (hoteldata_hub_test):
send-code (con el envío de email parcheado para capturar el código) →
confirm-code → asserts sobre el usuario creado.
"""

from __future__ import annotations

import pytest

from src.app.modules.auth.routes import register_property as rp
from src.app.security.hotel_filter import hotel_filter_from_user, user_can_access_hotel

pytestmark = pytest.mark.asyncio


def _onboarding_payload(email: str, username: str) -> dict:
    return {
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
    }


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


async def _complete_onboarding(client, db, monkeypatch, *, email: str, username: str) -> dict:
    """Corre send-code + confirm-code y devuelve el usuario creado + prop_id."""
    _seed_catalogs(db)
    captured = _capture_code(monkeypatch)
    payload = _onboarding_payload(email, username)

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


async def test_onboarding_owner_gets_assigned_hotels(client, db, monkeypatch):
    """RED: el fix — el dueño auto-registrado debe quedar con assigned_hotels == [prop_id]."""
    result = await _complete_onboarding(
        client, db, monkeypatch, email="owner@nuevo.hotel", username="owner_nuevo"
    )
    user = result["user"]
    assert user["assigned_prop_id"] == result["prop_id"]
    assert user["assigned_hotels"] == [result["prop_id"]]


async def test_onboarding_owner_scoped_to_own_hotel(client, db, monkeypatch):
    """RED: el alcance resultante es de un solo hotel (user_can_access_hotel + hotel_filter)."""
    result = await _complete_onboarding(
        client, db, monkeypatch, email="owner2@nuevo.hotel", username="owner_dos"
    )
    user = result["user"]
    prop_id = result["prop_id"]

    # Accede a su propio hotel, y solo al suyo.
    assert user_can_access_hotel(user, prop_id) is True
    assert user_can_access_hotel(user, prop_id + 1000) is False

    # El filtro de datos restringe a su hotel (antes era {} = sin filtro).
    assert hotel_filter_from_user(user) == {"prop_id": {"$in": [prop_id]}}


async def _send_then_confirm(client, db, monkeypatch, payload) -> dict:
    _seed_catalogs(db)
    captured = _capture_code(monkeypatch)
    resp = await client.post("/api/auth/register-property/send-code", json=payload)
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/api/auth/register-property/confirm-code",
        json={"email": payload["email"], "code": captured["code"]},
    )
    assert resp.status_code == 200, resp.text
    user = db.users.find_one({"email": payload["email"]})
    return db.dim_hotels.find_one({"prop_id": user["assigned_prop_id"]})


async def test_onboarding_stores_address_and_coords(client, db, monkeypatch):
    """Nivel 2 geolocalización: el dueño aporta dirección + lat/lng reales y
    quedan en dim_hotels (para el radio de 5 km literal de IE-H02)."""
    payload = _onboarding_payload("geo1@nuevo.hotel", "geo_uno")
    payload["address"] = "Av. Amazonas N37-61"
    payload["latitude"] = -0.1807
    payload["longitude"] = -78.4678

    hotel = await _send_then_confirm(client, db, monkeypatch, payload)
    assert hotel["address"] == "Av. Amazonas N37-61"
    assert hotel["latitude"] == -0.1807
    assert hotel["longitude"] == -78.4678


async def test_onboarding_geocodes_address_when_no_coords(client, db, monkeypatch):
    """Sin coordenadas pero con DIRECCIÓN, se geocodifica (Nominatim, best-effort)
    y el resultado se persiste en dim_hotels."""
    monkeypatch.setattr(
        rp,
        "geocode",
        lambda address, *, city="", country="": {
            "latitude": -0.1807,
            "longitude": -78.4678,
            "display_name": "Quito",
        },
    )
    payload = _onboarding_payload("geo2@nuevo.hotel", "geo_dos")
    payload["address"] = "Av. Amazonas N37-61"

    hotel = await _send_then_confirm(client, db, monkeypatch, payload)
    assert hotel["latitude"] == -0.1807
    assert hotel["longitude"] == -78.4678


async def test_onboarding_city_only_does_not_geocode(client, db, monkeypatch):
    """Con solo ciudad (sin dirección) NO se geocodifica ni se inventa una
    coordenada por hotel: latitude/longitude quedan None y el ETL cae a
    geo_catalog (ciudad)."""
    called: dict = {}
    monkeypatch.setattr(
        rp,
        "geocode",
        lambda address, *, city="", country="": called.update(called=True)
        or {"latitude": 0.0, "longitude": 0.0, "display_name": ""},
    )
    payload = _onboarding_payload("geo3@nuevo.hotel", "geo_tres")

    hotel = await _send_then_confirm(client, db, monkeypatch, payload)
    assert hotel.get("latitude") is None
    assert hotel.get("longitude") is None
    assert "called" not in called  # geocode nunca se invocó


async def test_onboarding_rejects_lat_without_lng(client, db, monkeypatch):
    _seed_catalogs(db)
    _capture_code(monkeypatch)
    payload = _onboarding_payload("geo4@nuevo.hotel", "geo_cuatro")
    payload["latitude"] = -0.1807  # sin longitude → 400

    resp = await client.post("/api/auth/register-property/send-code", json=payload)
    assert resp.status_code == 400
