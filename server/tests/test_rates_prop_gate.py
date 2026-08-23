"""Migración E (2026-08): tarifas gatea por hotel — tests de ruta.

Un usuario cuyo rol GLOBAL tiene ``rates.read`` pero SIN ``role_assignment``
para el hotel recibe 403 (el rol global ya no basta en contexto de hotel);
con el rol del hotel que otorga el código → 200. Sin ``prop_id`` → 400.
``rates.read`` NO abre escrituras (separación read/manage). El picker
multi-hotel ``GET /rates/options`` sigue global SIN prop_id.
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
    for code in ("rates.read", "rates.update", "rates.manage"):
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
            "name": "rol_hotel_rates",
            "display_name": "Rol Hotel Tarifas",
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
    """Rol GLOBAL con rates.read, SIN role_assignment (el hueco pre-E)."""
    _seed_catalog(db)
    _seed_hotel(db, 1)
    creds = _seed_user(db, username="analista_rates_global", role="rates_manager",
                       permissions=["rates.read"], assigned_hotels=[1])
    await _login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = _seed_hotel_role(db, permissions=["rates.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_gestor(client, db, global_analista):
    """Hotel role con SOLO rates.manage: no abre lecturas (separación)."""
    role_id = _seed_hotel_role(db, permissions=["rates.manage"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_editor(client, db, global_analista):
    """Hotel role con rates.update: permite editar un plan propio del hotel."""
    role_id = _seed_hotel_role(db, permissions=["rates.update"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestRatesPropGate:
    """Operación de tarifas = por hotel (rol global sin asignación → 403)."""

    @pytest.mark.asyncio
    async def test_rates_detail_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/management/rates", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_rates_detail_400_without_prop_id(self, client, db, admin_user):
        await _login(client, admin_user)
        resp = await client.get("/api/management/rates")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_rates_detail_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/rates", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_seasonal_rules_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/rates/seasonal-rules", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_read_does_not_open_writes(self, client, hotel_analista):
        """rates.read NO abre escrituras: POST /rates/plans exige rates.manage."""
        resp = await client.post(
            "/api/management/rates/plans?prop_id=1",
            json={"prop_id": 1, "name": "Plan", "base_rate": 100.0,
                  "currency": "USD", "is_active": True},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_create_plan_passes_gate_with_manage(self, client, hotel_gestor):
        """El write con rates.manage en el rol del hotel pasa el GATE
        (nunca 403): el status downstream es negocio de tarifas."""
        resp = await client.post(
            "/api/management/rates/plans?prop_id=1",
            json={"prop_id": 1, "name": "Plan", "base_rate": 100.0,
                  "currency": "USD", "is_active": True},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_plan_update_404_of_another_hotel(self, client, db, hotel_editor):
        plan_id = "RP-2-otro-hotel"
        db.rate_plans.insert_one(
            {"prop_id": 2, "rate_plan_id": plan_id, "name": "Otro", "base_rate": 100.0}
        )
        resp = await client.put(
            f"/api/management/rates/plans/{plan_id}?prop_id=1",
            json={"name": "Otro", "base_rate": 120.0, "currency": "USD", "is_active": True},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_rates_options_global_exception_without_prop_id(self, client, global_analista):
        """Picker multi-hotel: rates.read GLOBAL basta SIN prop_id."""
        resp = await client.get("/api/management/rates/options")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_rates_options_200_with_hotel_role_and_prop_id(self, client, hotel_analista):
        """Con prop_id el picker devuelve los rate plans del hotel."""
        resp = await client.get("/api/management/rates/options", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text
