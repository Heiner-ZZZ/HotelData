"""Cobertura de tarifas vs inventario en Tarifas (banner del overview).

``GET /api/management/rates`` debe exponer ``rate_coverage``: el hueco entre
el horizonte de tarifas ABIERTAS y el de inventario — las noches con
habitaciones disponibles que NO se pueden vender en el search público porque
no hay tarifa abierta. El banner del overview lo muestra y pre-carga el rango
faltante en "Generar calendario".
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


def _seed_inventory(db, prop_id: int, days: list[int], month: int = 9) -> None:
    for day in days:
        db.room_inventory_calendar.insert_one(
            {
                "prop_id": prop_id,
                "room_type_id": "RT-STD",
                "date": f"2026-{month:02d}-{day:02d}",
                "total_rooms": 5,
                "available_rooms": 3,
                "blocked_rooms": 0,
            }
        )


def _seed_rate(db, prop_id: int, day: int, *, is_closed: bool = False, month: int = 9) -> None:
    db.hotel_rate_calendar.insert_one(
        {
            "prop_id": prop_id,
            "rate_plan_id": "RP-FLEX",
            "date": f"2026-{month:02d}-{day:02d}",
            "rate_amount": 100.0,
            "is_closed": is_closed,
        }
    )


async def test_rate_coverage_exposes_gap(client: AsyncClient, db, admin_user):
    """Tarifas abiertas hasta 09-01, inventario disponible 09-02..09-10 → 9 noches sin tarifa."""
    prop_id = 9001
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_rate(db, prop_id, 1)
    _seed_inventory(db, prop_id, list(range(2, 11)))

    resp = await client.get("/api/management/rates", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    cov = resp.json()["rate_coverage"]
    assert cov == {
        "rate_last_date": "2026-09-01",
        "inventory_last_date": "2026-09-10",
        "gap_nights": 9,
        "gap_start": "2026-09-02",
        "gap_end": "2026-09-10",
    }


async def test_rate_coverage_null_when_rates_cover_inventory(client: AsyncClient, db, admin_user):
    """Si las tarifas cubren todo el horizonte de inventario, no hay hueco → null."""
    prop_id = 9002
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_inventory(db, prop_id, list(range(2, 11)))
    for day in range(2, 11):
        _seed_rate(db, prop_id, day)

    resp = await client.get("/api/management/rates", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["rate_coverage"] is None


async def test_rate_coverage_last_date_uses_open_rates_only(client: AsyncClient, db, admin_user):
    """Una tarifa CERRADA después del último día abierto no extiende el horizonte."""
    prop_id = 9003
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_inventory(db, prop_id, list(range(2, 11)))
    for day in range(2, 6):
        _seed_rate(db, prop_id, day)
    _seed_rate(db, prop_id, 10, is_closed=True)  # cerrada → no vendible

    resp = await client.get("/api/management/rates", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    cov = resp.json()["rate_coverage"]
    assert cov["rate_last_date"] == "2026-09-05"
    assert cov["gap_nights"] == 5  # 09-06 .. 09-10
    assert cov["gap_start"] == "2026-09-06"
    assert cov["gap_end"] == "2026-09-10"


async def test_rate_coverage_only_counts_available_nights(client: AsyncClient, db, admin_user):
    """Noches con inventario pero 0 disponibles no entran en el conteo del hueco."""
    prop_id = 9004
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_inventory(db, prop_id, [2, 3])
    # 09-04 existe pero con 0 disponibles
    db.room_inventory_calendar.insert_one(
        {
            "prop_id": prop_id,
            "room_type_id": "RT-STD",
            "date": "2026-09-04",
            "total_rooms": 5,
            "available_rooms": 0,
            "blocked_rooms": 5,
        }
    )
    _seed_rate(db, prop_id, 1)

    resp = await client.get("/api/management/rates", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    cov = resp.json()["rate_coverage"]
    assert cov["gap_nights"] == 2  # solo 09-02 y 09-03
    assert cov["gap_end"] == "2026-09-03"
