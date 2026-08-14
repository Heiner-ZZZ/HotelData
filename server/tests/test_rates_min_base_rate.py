"""Tarifa base mínima en planes tarifarios (system_config.min_base_rate).

``POST /api/management/rates/plans`` y ``PUT /api/management/rates/plans/{id}``
deben rechazar una ``base_rate`` por debajo del umbral configurable (default
$10, leído de ``system_config``) y aceptar el valor exacto del umbral. El
``GET /api/management/rates`` expone ``min_base_rate`` para que el form de
Tarifas valide con el mismo valor del backend.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login

pytestmark = pytest.mark.asyncio


def _seed_hotel(db, prop_id: int) -> None:
    db.dim_hotels.insert_one(
        {
            "prop_id": prop_id,
            "hotel_name": f"Hotel {prop_id}",
            "display_name": f"Hotel {prop_id}",
            "prop_starrating": 4.0,
            "prop_review_score": 8.0,
        }
    )


def _set_min_base_rate(db, value: float) -> None:
    db.system_config.update_one(
        {"_id": "global"},
        {"$set": {"min_base_rate": value}},
        upsert=True,
    )


async def test_create_rate_plan_rejects_base_rate_below_minimum(client: AsyncClient, db, admin_user):
    """9.99 < 10 → 400 con mensaje que menciona el mínimo."""
    prop_id = 9101
    _set_min_base_rate(db, 10.0)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)

    resp = await client.post(
        "/api/management/rates/plans",
        json={
            "prop_id": prop_id,
            "name": "Plan barato",
            "base_rate": 9.99,
            "currency": "USD",
            "is_active": True,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "10" in resp.json()["detail"]


async def test_create_rate_plan_accepts_base_rate_at_minimum(client: AsyncClient, db, admin_user):
    """10 == umbral → 201 y el plan guarda base_rate 10."""
    prop_id = 9102
    _set_min_base_rate(db, 10.0)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)

    resp = await client.post(
        "/api/management/rates/plans",
        json={
            "prop_id": prop_id,
            "name": "Plan mínimo",
            "base_rate": 10.0,
            "currency": "USD",
            "is_active": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["base_rate"] == 10.0


async def test_update_rate_plan_rejects_base_rate_below_minimum(client: AsyncClient, db, admin_user):
    """Un plan existente a $100 no se puede bajar a $9 (400)."""
    prop_id = 9103
    _set_min_base_rate(db, 10.0)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)

    created = await client.post(
        "/api/management/rates/plans",
        json={
            "prop_id": prop_id,
            "name": "Plan caro",
            "base_rate": 100.0,
            "currency": "USD",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["rate_plan_id"]

    resp = await client.put(
        f"/api/management/rates/plans/{plan_id}",
        json={
            "name": "Plan caro",
            "base_rate": 9.0,
            "currency": "USD",
            "is_active": True,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "10" in resp.json()["detail"]


async def test_minimum_is_configurable_via_system_config(client: AsyncClient, db, admin_user):
    """Subir el umbral a $20 en system_config → $15 rechazado, $20 aceptado."""
    prop_id = 9104
    _set_min_base_rate(db, 20.0)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)

    try:
        low = await client.post(
            "/api/management/rates/plans",
            json={
                "prop_id": prop_id,
                "name": "Plan quince",
                "base_rate": 15.0,
                "currency": "USD",
                "is_active": True,
            },
        )
        assert low.status_code == 400, low.text
        assert "20" in low.json()["detail"]

        ok = await client.post(
            "/api/management/rates/plans",
            json={
                "prop_id": prop_id,
                "name": "Plan veinte",
                "base_rate": 20.0,
                "currency": "USD",
                "is_active": True,
            },
        )
        assert ok.status_code == 201, ok.text
        assert ok.json()["base_rate"] == 20.0
    finally:
        _set_min_base_rate(db, 10.0)


async def test_rates_detail_exposes_min_base_rate(client: AsyncClient, db, admin_user):
    """GET /api/management/rates expone min_base_rate para el form de Tarifas."""
    prop_id = 9105
    _set_min_base_rate(db, 20.0)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)

    try:
        resp = await client.get("/api/management/rates", params={"prop_id": prop_id})
        assert resp.status_code == 200, resp.text
        assert resp.json()["min_base_rate"] == 20.0
    finally:
        _set_min_base_rate(db, 10.0)
