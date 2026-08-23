"""Migración E (2026-08): reception gatea por hotel — tests de ruta.

Un usuario cuyo rol GLOBAL tiene ``shifts.*`` pero SIN ``role_assignment``
para el hotel recibe 403 (el rol global ya no basta en contexto de hotel);
con el rol del hotel que otorga el código → 200. Sin ``prop_id`` → 400.
Cross-hotel: un turno de otro hotel no es legible. Las vistas de gerencia
multi-hotel (manager-control / open-overview) siguen globales (excepción).
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
    for code in ("shifts.read", "shifts.create", "shifts.update", "shifts.manage"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )


def _seed_global_staff(db) -> dict[str, str]:
    """Rol GLOBAL con shifts.* completo, SIN role_assignment (el hueco pre-E)."""
    db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepción",
            "permissions": ["shifts.read", "shifts.create", "shifts.update"],
            "is_system": True,
            "created_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": "recepcion_global",
            "email": "recepcion_global@hotel.local",
            "display_name": "Recepción Global",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "recepcionista",
            "role_ids": [],
            "assigned_hotels": [1],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": "recepcion_global", "password": "Pass123!"}


def _seed_hotel_role(db, *, prop_id: int = 1, permissions: list[str]) -> ObjectId:
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": "recepcionista_hotel",
            "display_name": "Recepción Hotel",
            "permissions": permissions,
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id


def _seed_global_manager(db) -> dict[str, str]:
    """Rol GLOBAL gerente_hotel con shifts.manage, SIN role_assignment —
    la excepción de gerencia multi-hotel debe seguir funcionando con el
    rol global (vistas que cruzan hoteles a propósito)."""
    db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente",
            "permissions": ["shifts.manage"],
            "is_system": True,
            "created_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": "gerente_global",
            "email": "gerente_global@hotel.local",
            "display_name": "Gerente Global",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "gerente_hotel",
            "role_ids": [],
            "assigned_hotels": [],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": "gerente_global", "password": "Pass123!"}


async def _login(client, creds: dict[str, str]) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text


@pytest_asyncio.fixture
async def global_staff(client, db):
    _seed_catalog(db)
    creds = _seed_global_staff(db)
    await _login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_staff(client, db, global_staff):
    role_id = _seed_hotel_role(db, permissions=["shifts.read", "shifts.create", "shifts.update"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_staff["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_staff


class TestReceptionPropGate:
    """Operación de turnos = por hotel (rol global sin asignación → 403)."""

    @pytest.mark.asyncio
    async def test_active_403_global_role_without_assignment(self, client, global_staff):
        resp = await client.get("/api/reception/shifts/active", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_active_400_without_prop_id(self, client, db, admin_user):
        await _login(client, admin_user)
        resp = await client.get("/api/reception/shifts/active")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_active_200_with_hotel_role(self, client, hotel_staff):
        resp = await client.get("/api/reception/shifts/active", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_open_requires_prop_id_query_even_with_body_prop_id(self, client, global_staff):
        resp = await client.post(
            "/api/reception/shifts/open",
            json={"prop_id": 1, "shift_type": "morning", "employee": "recepcion_global"},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_open_400_on_body_query_mismatch(self, client, hotel_staff):
        resp = await client.post(
            "/api/reception/shifts/open?prop_id=1",
            json={"prop_id": 2, "shift_type": "morning", "employee": "recepcion_global"},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_detail_404_shift_of_another_hotel(self, client, db, hotel_staff):
        shift_id = db.reception_shifts.insert_one(
            {
                "prop_id": 2,
                "status": "active",
                "opened_by": "otro",
                "shift_type": "morning",
                "created_at": _now(),
            }
        ).inserted_id
        resp = await client.get(f"/api/reception/shifts/{shift_id}", params={"prop_id": 1})
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_manager_control_stays_global_exception(self, client, db):
        """Vista de gerencia multi-hotel: el rol GLOBAL shifts.manage basta
        (excepción documentada — sin prop_id cruza hoteles a propósito)."""
        _seed_catalog(db)
        creds = _seed_global_manager(db)
        await _login(client, creds)
        resp = await client.get("/api/reception/shifts/manager-control")
        assert resp.status_code == 200, resp.text
        resp_ov = await client.get("/api/reception/shifts/open-overview")
        assert resp_ov.status_code == 200, resp_ov.text
