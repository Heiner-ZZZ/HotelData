"""Migración E (2026-08): disponibilidad gatea por hotel — tests de ruta.

Un usuario cuyo rol GLOBAL tiene ``inventory.read`` pero SIN ``role_assignment``
para el hotel recibe 403; con el rol del hotel que otorga el código → 200.
Sin ``prop_id`` → 400. ``inventory.read`` NO abre escrituras. El picker
multi-hotel ``GET /availability/options`` sigue global SIN prop_id.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from bson import ObjectId
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_catalog(db) -> None:
    for code in ("inventory.read", "inventory.manage"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )


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


def _seed_user(db, *, username: str, role: str, permissions: list[str],
               assigned_hotels: list[int] | None = None) -> dict[str, str]:
    db.roles.insert_one(
        {
            "role_name": role,
            "display_name": role.replace("_", " ").title(),
            "permissions": permissions,
            "is_system": True,
            "created_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": role,
            "role_ids": [],
            "assigned_hotels": assigned_hotels if assigned_hotels is not None else [],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": username, "password": "Pass123!"}


def _seed_hotel_role(db, *, prop_id: int = 1, permissions: list[str]) -> ObjectId:
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": "rol_hotel_availability",
            "display_name": "Rol Hotel Disponibilidad",
            "permissions": permissions,
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id


async def _login(client, creds: dict[str, str]) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text


@pytest_asyncio.fixture
async def global_analista(client, db):
    """Rol GLOBAL con inventory.read, SIN role_assignment (el hueco pre-E)."""
    _seed_catalog(db)
    _seed_hotel(db, 1)
    creds = _seed_user(db, username="analista_avail_global", role="inventory_manager",
                       permissions=["inventory.read"], assigned_hotels=[1])
    await _login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = _seed_hotel_role(db, permissions=["inventory.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_gestor(client, db, global_analista):
    """Hotel role con SOLO inventory.manage: no abre lecturas (separación)."""
    role_id = _seed_hotel_role(db, permissions=["inventory.manage"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestAvailabilityPropGate:
    """Operación de disponibilidad = por hotel (rol global sin asignación → 403)."""

    @pytest.mark.asyncio
    async def test_availability_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/management/availability", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_availability_400_without_prop_id(self, client, db, admin_user):
        await _login(client, admin_user)
        resp = await client.get("/api/management/availability")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_availability_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/availability", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_blackouts_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/availability/blackouts", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_read_does_not_open_writes(self, client, hotel_analista):
        """inventory.read NO abre escrituras: POST /availability exige manage."""
        resp = await client.post(
            "/api/management/availability?prop_id=1",
            json={"prop_id": 1, "room_type_id": "RT-STD", "date": "2026-09-01",
                  "total_rooms": 5, "available_rooms": 5, "blocked_rooms": 0},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_create_inventory_passes_gate_with_manage(self, client, hotel_gestor):
        """El write con inventory.manage en el rol del hotel pasa el GATE."""
        resp = await client.post(
            "/api/management/availability?prop_id=1",
            json={"prop_id": 1, "room_type_id": "RT-STD", "date": "2026-09-01",
                  "total_rooms": 5, "available_rooms": 5, "blocked_rooms": 0},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_blackout_delete_404_of_another_hotel(self, client, db, hotel_gestor):
        blackout_id = ObjectId("6a5fc805a7ffc4ee07aebe99")
        db.blackout_dates.insert_one(
            {"_id": blackout_id, "prop_id": 2, "room_type_id": "RT-BLACKOUT",
             "start_date": "2026-09-10", "end_date": "2026-09-11", "reason": "Otro hotel"}
        )
        resp = await client.delete(f"/api/management/availability/blackouts/{blackout_id}?prop_id=1")
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_availability_options_global_exception_without_prop_id(self, client, global_analista):
        """Picker multi-hotel: inventory.read GLOBAL basta SIN prop_id."""
        resp = await client.get("/api/management/availability/options")
        assert resp.status_code == 200, resp.text
