"""TDD RED: /hotels/1 sin fechas debe mostrar disponibilidad próxima por habitación.

El huésped entra a /hotels/1 sin check_in/out y ve cajas con "Disponible" genérico
y "Consultar" sin saber qué día de esta semana está realmente disponible.
Este test exige un endpoint público que devuelva por cada room_type los próximos
7 días con is_available, available_rooms y rate válido, para que la UI pueda
mostrar chips de días sin que el usuario adivine en el calendario.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta

from src.app.core.timezone import local_today

pytestmark = pytest.mark.asyncio


def _seed_room_with_inventory(db, prop_id: int, room_type_id: str, name: str, dates_available: list[str]):
    db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {"$set": {"prop_id": prop_id, "hotel_name": f"Hotel {prop_id}", "display_name": f"Hotel {prop_id}", "prop_starrating": 4.0}},
        upsert=True,
    )
    db.room_types.update_one(
        {"room_type_id": room_type_id},
        {"$set": {"room_type_id": room_type_id, "prop_id": prop_id, "name": name, "base_capacity": 2, "max_adults": 2, "max_children": 1, "is_active": True}},
        upsert=True,
    )
    plan_id = f"RP-{prop_id}-{room_type_id}"
    db.rate_plans.update_one(
        {"rate_plan_id": plan_id},
        {"$set": {"rate_plan_id": plan_id, "prop_id": prop_id, "name": "Test", "base_rate": 100.0, "is_active": True, "applicable_room_types": [room_type_id]}},
        upsert=True,
    )
    for d in dates_available:
        db.room_inventory_calendar.update_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "date": d},
            {"$set": {"prop_id": prop_id, "room_type_id": room_type_id, "date": d, "total_rooms": 5, "available_rooms": 3, "blocked_rooms": 0}},
            upsert=True,
        )
        db.hotel_rate_calendar.update_one(
            {"prop_id": prop_id, "rate_plan_id": plan_id, "date": d},
            {"$set": {"prop_id": prop_id, "rate_plan_id": plan_id, "date": d, "rate_amount": 135.0, "is_closed": False}},
            upsert=True,
        )


async def test_room_next7_snapshot_returns_per_room_per_day_availability(client, db):
    """GET /api/hotels/{prop_id}/availability/snapshot?days=7 debe existir y devolver por habitación el detalle diario."""
    prop_id = 91001
    today = local_today()
    # Crear room_type con disponibilidad solo en 3 de los próximos 7 días
    all_dates = [(date.fromisoformat(today) + timedelta(days=i)).isoformat() for i in range(7)]
    available_dates = all_dates[:3]  # solo primeros 3 días disponibles
    _seed_room_with_inventory(db, prop_id, "RT-91001-A", "Habitacion Doble Premiun", available_dates)
    # Segundo room_type con disponibilidad en todos los 7 días
    _seed_room_with_inventory(db, prop_id, "RT-91001-B", "Habitacion sola VIP", all_dates)

    resp = await client.get(f"/api/hotels/{prop_id}/availability/snapshot", params={"days": 7})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["prop_id"] == prop_id
    assert data["start_date"] == today
    # end_date = start + 6 días (7 noches)
    expected_end = (date.fromisoformat(today) + timedelta(days=6)).isoformat()
    assert data["end_date"] == expected_end
    assert "rooms" in data
    by_id = {r["room_type_id"]: r for r in data["rooms"]}
    assert "RT-91001-A" in by_id
    assert "RT-91001-B" in by_id

    # Room A: primeros 3 días is_available True, resto False
    avail_a = by_id["RT-91001-A"]["availability"]
    assert len(avail_a) == 7
    for i, day in enumerate(avail_a):
        assert day["date"] == all_dates[i]
        if i < 3:
            assert day["is_available"] is True, f"dia {i} debe estar disponible"
            assert day["available_rooms"] == 3
            assert day["min_rate"] == 135.0
        else:
            assert day["is_available"] is False
            # sin inventario ni tarifa, available_rooms 0 y min_rate None
            assert day["available_rooms"] == 0 or day["min_rate"] is None

    # Room B: todos disponibles
    avail_b = by_id["RT-91001-B"]["availability"]
    assert all(d["is_available"] is True for d in avail_b)
    assert all(d["min_rate"] == 135.0 for d in avail_b)


async def test_snapshot_without_dates_uses_today_and_respects_is_closed_and_orphan(client, db):
    """Si no se pasa start_date, usa local_today. Debe respetar is_closed y plan huérfano."""
    prop_id = 91002
    today = local_today()
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    # Crear plan huérfano (sin applicable_room_types) -> no debe contar como disponible
    db.dim_hotels.update_one({"prop_id": prop_id}, {"$set": {"prop_id": prop_id, "hotel_name": f"Hotel {prop_id}"}}, upsert=True)
    db.room_types.update_one({"room_type_id": "RT-91002-A"}, {"$set": {"room_type_id": "RT-91002-A", "prop_id": prop_id, "name": "Habitación Deluxe", "base_capacity": 2, "max_adults": 2, "is_active": True}}, upsert=True)
    db.rate_plans.update_one({"rate_plan_id": f"RP-{prop_id}-orphan"}, {"$set": {"rate_plan_id": f"RP-{prop_id}-orphan", "prop_id": prop_id, "name": "Orphan", "base_rate": 50.0, "is_active": True, "applicable_room_types": [], "room_type_id": ""}}, upsert=True)
    db.room_inventory_calendar.update_one({"prop_id": prop_id, "room_type_id": "RT-91002-A", "date": today}, {"$set": {"prop_id": prop_id, "room_type_id": "RT-91002-A", "date": today, "available_rooms": 2}}, upsert=True)
    db.hotel_rate_calendar.update_one({"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-orphan", "date": today}, {"$set": {"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-orphan", "date": today, "rate_amount": 2.0, "is_closed": False}}, upsert=True)
    # También crear un plan válido pero con is_closed True para tomorrow -> no disponible
    db.rate_plans.update_one({"rate_plan_id": f"RP-{prop_id}-valid"}, {"$set": {"rate_plan_id": f"RP-{prop_id}-valid", "prop_id": prop_id, "name": "Valid", "base_rate": 100.0, "is_active": True, "applicable_room_types": ["RT-91002-A"]}}, upsert=True)
    db.room_inventory_calendar.update_one({"prop_id": prop_id, "room_type_id": "RT-91002-A", "date": tomorrow}, {"$set": {"prop_id": prop_id, "room_type_id": "RT-91002-A", "date": tomorrow, "available_rooms": 2}}, upsert=True)
    db.hotel_rate_calendar.update_one({"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-valid", "date": tomorrow}, {"$set": {"prop_id": prop_id, "rate_plan_id": f"RP-{prop_id}-valid", "date": tomorrow, "rate_amount": 120.0, "is_closed": True}}, upsert=True)

    resp = await client.get(f"/api/hotels/{prop_id}/availability/snapshot", params={"days": 2})
    assert resp.status_code == 200
    data = resp.json()
    room = next(r for r in data["rooms"] if r["room_type_id"] == "RT-91002-A")
    # Hoy con plan huérfano -> no disponible (rate no cuenta)
    assert room["availability"][0]["is_available"] is False
    # Mañana con is_closed True -> no disponible
    assert room["availability"][1]["is_available"] is False
