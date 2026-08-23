"""Migración E (2026-08): lost & found gatea POR HOTEL — tests de ruta.

Rol GLOBAL con ``lost-found.read`` SIN role_assignment → 403; con el rol del
hotel (lost-found.read o housekeeping.read) → 200. Sin prop_id → 400.
Item de otro hotel → 404.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from bson import ObjectId

from tests._prop_gate_helpers import login, now, seed_catalog, seed_hotel, seed_hotel_role, seed_user

CATALOG = ["lost-found.read", "lost-found.create", "lost-found.update", "lost-found.delete",
           "housekeeping.read", "housekeeping.create"]


def _seed_item(db, *, item_id: ObjectId | None = None, prop_id: int = 1) -> ObjectId:
    oid = item_id or ObjectId()
    db.lost_and_found.insert_one(
        {"_id": oid, "prop_id": prop_id, "item_name": "Billetera",
         "status": "found", "created_at": now()}
    )
    return oid


@pytest_asyncio.fixture
async def global_analista(client, db):
    seed_catalog(db, CATALOG)
    seed_hotel(db, 1)
    creds = seed_user(db, username="analista_lf_global", role="housekeeping_manager",
                      permissions=["lost-found.read"], assigned_hotels=[1])
    await login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_lf", permissions=["lost-found.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_gestor(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_lf_manage",
                              permissions=["lost-found.create", "lost-found.update",
                                           "lost-found.delete"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestLostAndFoundPropGate:
    @pytest.mark.asyncio
    async def test_list_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/lost-and-found", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_400_without_prop_id(self, client, db, admin_user):
        await login(client, admin_user)
        resp = await client.get("/api/lost-and-found")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/lost-and-found", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_housekeeping_role_also_opens(self, client, db, global_analista):
        """El combo lost-found.X O housekeeping.X abre: rol con SOLO
        housekeeping.read (sin códigos lost-found) → 200."""
        creds_hk = seed_user(db, username="analista_hk_solo", role="housekeeping_solo",
                             permissions=[], assigned_hotels=[1])
        role_id = seed_hotel_role(db, name="rol_hk_lf", permissions=["housekeeping.read"])
        db.role_assignments.insert_one(
            {"user_id": ObjectId(creds_hk["user_id"]), "prop_id": 1, "role_id": role_id}
        )
        await login(client, creds_hk)
        resp = await client.get("/api/lost-and-found", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_read_does_not_open_writes(self, client, db, hotel_analista):
        item_id = _seed_item(db)
        resp = await client.post(f"/api/lost-and-found/{item_id}/claim?prop_id=1", json={})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_create_passes_gate_with_manage(self, client, hotel_gestor):
        resp = await client.post(
            "/api/lost-and-found?prop_id=1",
            json={"prop_id": 1, "item_name": "Llaves", "status": "found"},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_item_detail_404_of_another_hotel(self, client, db, hotel_analista):
        item_id = _seed_item(db, prop_id=2)
        resp = await client.get(f"/api/lost-and-found/{item_id}?prop_id=1")
        assert resp.status_code == 404, resp.text
