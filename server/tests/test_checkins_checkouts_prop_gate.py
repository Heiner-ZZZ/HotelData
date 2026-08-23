"""Migración E (2026-08): check-ins/outs gatean POR HOTEL — tests de ruta.

Rol GLOBAL con ``check-ins.read``/``check-outs.read`` SIN role_assignment →
403; con el rol del hotel → 200. Sin prop_id → 400. ``read`` no abre
escrituras. Booking de otro hotel → 404.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from bson import ObjectId

from tests._prop_gate_helpers import login, now, seed_catalog, seed_hotel, seed_hotel_role, seed_user

CATALOG = ["check-ins.read", "check-ins.manage", "check-outs.read", "check-outs.manage",
           "reservations.read", "reservations.update", "charges.manage", "lost-found.read"]


def _seed_booking(db, *, booking_id: str = "BK-1", prop_id: int = 1,
                  status: str = "pending", user_id: ObjectId | None = None) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": prop_id,
        "status": status,
        "guest_name": "Huésped",
        "check_in_date": "2026-09-01",
        "check_out_date": "2026-09-03",
        "total_nights": 2,
        "total_price": 200.0,
        "currency": "USD",
        "room_type_id": "RT-1-std",
        "created_at": now(),
    }
    if user_id is not None:
        doc["user_id"] = user_id
    db.booking_orders.insert_one(doc)


@pytest_asyncio.fixture
async def global_analista(client, db):
    seed_catalog(db, CATALOG)
    seed_hotel(db, 1)
    creds = seed_user(db, username="analista_ci_co_global", role="frontdesk_manager",
                      permissions=["check-ins.read", "check-outs.read"],
                      assigned_hotels=[1])
    await login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_ci_co",
                              permissions=["check-ins.read", "check-outs.read", "reservations.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_gestor(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_ci_co_manage",
                              permissions=["check-ins.manage", "check-outs.manage",
                                           "reservations.update", "charges.manage"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestCheckinsCheckoutsPropGate:
    @pytest.mark.asyncio
    async def test_checkins_list_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/management/check-ins", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_checkins_list_400_without_prop_id(self, client, db, admin_user):
        await login(client, admin_user)
        resp = await client.get("/api/management/check-ins")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_checkins_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/check-ins", params={"prop_id": 1, "date": "2026-09-01"})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_checkouts_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/check-outs", params={"prop_id": 1, "date": "2026-09-01"})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_read_does_not_open_writes(self, client, db, hotel_analista):
        """check-ins.read NO abre escrituras: POST /complete exige manage."""
        _seed_booking(db, booking_id="BK-READ")
        resp = await client.post(
            "/api/management/check-ins/BK-READ/complete?prop_id=1",
            json={"express": True},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_complete_passes_gate_with_manage(self, client, db, hotel_gestor):
        """El write con check-ins.manage pasa el GATE (nunca 403/404): el status
        downstream es negocio del check-in (tiene sus propios tests)."""
        _seed_booking(db, booking_id="BK-MANAGE")
        resp = await client.post(
            "/api/management/check-ins/BK-MANAGE/complete?prop_id=1",
            json={"express": True},
        )
        assert resp.status_code not in (403, 404), resp.text

    @pytest.mark.asyncio
    async def test_checkin_detail_404_of_another_hotel(self, client, db, hotel_analista):
        _seed_booking(db, booking_id="BK-OTRO", prop_id=2)
        resp = await client.get("/api/management/check-ins/BK-OTRO/detail?prop_id=1")
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_users_search_403_without_reservation_perms(self, client, db, global_analista):
        """users/search exige reservations.manage|read POR HOTEL (el rol global
        de check-ins no abre la búsqueda de usuarios del hotel)."""
        resp = await client.get("/api/management/users/search", params={"prop_id": 1, "q": "x"})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_users_search_200_with_reservations_read(self, client, db, hotel_analista):
        resp = await client.get("/api/management/users/search", params={"prop_id": 1, "q": "x"})
        assert resp.status_code == 200, resp.text
