"""Cobertura de tarifas en el calendario de Disponibilidad.

El endpoint ``GET /api/management/availability`` debe exponer por cada item
de inventario si la fecha tiene al menos una tarifa ABIERTA
(``is_closed != True``). Sin tarifa abierta, la disponibilidad no es vendible
en el search público (``/api/hotels/availability`` exige inventario Y tarifa
por noche) — el marcador visual "disponible sin tarifa" del calendario se
alimenta de este flag.
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


def _seed_room_type(db, prop_id: int) -> None:
    db.room_types.insert_one(
        {
            "room_type_id": "RT-STD",
            "prop_id": prop_id,
            "name": "Habitación Standard",
            "base_capacity": 2,
            "max_adults": 2,
            "max_children": 1,
            "is_active": True,
        }
    )


async def test_inventory_items_expose_rate_coverage(client: AsyncClient, db, admin_user):
    prop_id = 9001
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_room_type(db, prop_id)

    for date in ("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"):
        db.room_inventory_calendar.insert_one(
            {
                "prop_id": prop_id,
                "room_type_id": "RT-STD",
                "date": date,
                "total_rooms": 10,
                "available_rooms": 5,
                "blocked_rooms": 0,
            }
        )
    # Tarifa abierta el 01 y el 03; tarifa CERRADA el 02; nada el 04.
    db.hotel_rate_calendar.insert_one(
        {
            "prop_id": prop_id,
            "rate_plan_id": "RP-FLEX",
            "date": "2026-09-01",
            "rate_amount": 100.0,
            "is_closed": False,
        }
    )
    db.hotel_rate_calendar.insert_one(
        {
            "prop_id": prop_id,
            "rate_plan_id": "RP-FLEX",
            "date": "2026-09-02",
            "rate_amount": 100.0,
            "is_closed": True,
        }
    )
    db.hotel_rate_calendar.insert_one(
        {
            "prop_id": prop_id,
            "rate_plan_id": "RP-FLEX",
            "date": "2026-09-03",
            "rate_amount": 110.0,
            "is_closed": False,
        }
    )

    resp = await client.get(
        "/api/management/availability",
        params={"prop_id": prop_id, "start_date": "2026-09-01", "end_date": "2026-09-04"},
    )
    assert resp.status_code == 200, resp.text
    by_date = {item["date"]: item for item in resp.json()["inventory_items"]}
    assert set(by_date) == {"2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"}
    assert by_date["2026-09-01"]["has_rate"] is True
    assert by_date["2026-09-02"]["has_rate"] is False  # cerrada → no vendible
    assert by_date["2026-09-03"]["has_rate"] is True
    assert by_date["2026-09-04"]["has_rate"] is False  # sin tarifa


async def test_inventory_items_without_rates_default_to_false(client: AsyncClient, db, admin_user):
    """Sin ninguna tarifa en el rango, todos los items son has_rate=False."""
    prop_id = 9002
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_room_type(db, prop_id)
    db.room_inventory_calendar.insert_one(
        {
            "prop_id": prop_id,
            "room_type_id": "RT-STD",
            "date": "2026-09-10",
            "total_rooms": 5,
            "available_rooms": 2,
            "blocked_rooms": 0,
        }
    )

    resp = await client.get(
        "/api/management/availability",
        params={"prop_id": prop_id, "start_date": "2026-09-10", "end_date": "2026-09-10"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["inventory_items"]
    assert len(items) == 1
    assert items[0]["has_rate"] is False
