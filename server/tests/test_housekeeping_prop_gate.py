"""Migración E (2026-08): housekeeping gatea por hotel — tests de ruta.

Mismo contrato que reception: el rol GLOBAL con el código ya no basta (403
sin role_assignment del hotel); con el rol del hotel → 200; sin prop_id →
400; recurso de otro hotel → 404. La excepción multi-hotel
(cleanup-orphans) sigue global.
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
    for code in ("housekeeping.read", "housekeeping.update", "housekeeping.delete"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )


def _seed_global_staff(db) -> dict[str, str]:
    """Rol GLOBAL housekeeping con los códigos, SIN role_assignment."""
    db.roles.insert_one(
        {
            "role_name": "housekeeping",
            "display_name": "Housekeeping",
            "permissions": ["housekeeping.read", "housekeeping.update", "housekeeping.delete"],
            "is_system": True,
            "created_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": "hk_global",
            "email": "hk_global@hotel.local",
            "display_name": "HK Global",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "housekeeping",
            "role_ids": [],
            "assigned_hotels": [1],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": "hk_global", "password": "Pass123!"}


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
    role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "hk_hotel",
            "display_name": "HK Hotel",
            "permissions": ["housekeeping.read", "housekeeping.update", "housekeeping.delete", "housekeeping.create"],
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_staff["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_staff


class TestHousekeepingPropGate:
    """Operación de housekeeping = por hotel."""

    @pytest.mark.asyncio
    async def test_room_status_403_global_role_without_assignment(self, client, global_staff):
        resp = await client.get("/api/housekeeping/room-status", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_room_status_400_without_prop_id(self, client, db, admin_user):
        await _login(client, admin_user)
        resp = await client.get("/api/housekeeping/room-status")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_room_status_200_with_hotel_role(self, client, hotel_staff):
        resp = await client.get("/api/housekeeping/room-status", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_tasks_200_with_hotel_role(self, client, hotel_staff):
        resp = await client.get("/api/housekeeping/tasks", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_put_room_status_requires_query_prop_id(self, client, global_staff):
        resp = await client.put(
            "/api/housekeeping/room-status",
            json={"prop_id": 1, "room_label": "101", "status": "clean"},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_put_room_status_body_query_mismatch(self, client, hotel_staff):
        resp = await client.put(
            "/api/housekeeping/room-status?prop_id=1",
            json={"prop_id": 2, "room_label": "101", "room_type_id": "STD-1", "status": "clean"},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_task_resource_cross_hotel_404(self, client, db, hotel_staff):
        task_id = db.housekeeping_tasks.insert_one(
            {
                "prop_id": 2,
                "room_label": "201",
                "task_type": "cleaning",
                "status": "pending",
                "created_at": _now(),
            }
        ).inserted_id
        resp = await client.post(
            f"/api/housekeeping/tasks/{task_id}/complete",
            params={"prop_id": 1},
            json={},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_cleanup_orphans_stays_global_exception(self, client, db):
        """Mantenimiento multi-hotel: el rol GLOBAL housekeeping.delete basta."""
        _seed_catalog(db)
        creds = _seed_global_staff(db)
        await _login(client, creds)
        resp = await client.post("/api/housekeeping/room-status/cleanup-orphans", json={})
        assert resp.status_code == 200, resp.text
