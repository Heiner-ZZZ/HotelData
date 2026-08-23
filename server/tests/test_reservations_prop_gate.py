"""Migración E (2026-08): reservas gatean POR HOTEL — tests de ruta.

Rol GLOBAL con ``reservations.read`` SIN role_assignment → 403; con el rol
del hotel → 200. Sin prop_id → 400. ``read`` no abre escrituras. Booking de
otro hotel → 404. El detalle GET /{booking_id} sigue mixto (huésped/staff):
staff sin asignación → 403 INLINE incluso con prop_id.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from bson import ObjectId

from tests._prop_gate_helpers import login, now, seed_catalog, seed_hotel, seed_hotel_role, seed_user

CATALOG = ["reservations.read", "reservations.create", "reservations.update",
           "reservations.delete", "check-ins.read", "check-outs.read"]


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
    creds = seed_user(db, username="analista_res_global", role="reservations_manager",
                      permissions=["reservations.read"], assigned_hotels=[1])
    await login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_res", permissions=["reservations.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_gestor(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_res_manage",
                              permissions=["reservations.create", "reservations.update",
                                           "reservations.delete"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestReservationsPropGate:
    @pytest.mark.asyncio
    async def test_list_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/reservations", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_without_prop_id_global_multi_hotel(self, client, db, admin_user):
        """GET /api/reservations sin prop_id = vista multi-hotel/global
        (excepción documentada: admin → 200 con lista vacía)."""
        await login(client, admin_user)
        resp = await client.get("/api/reservations")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/reservations", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_rate_plans_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get(
            "/api/reservations/rate-plans",
            params={"prop_id": 1, "check_in": "2026-09-01", "check_out": "2026-09-03"},
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_read_does_not_open_writes(self, client, db, hotel_analista):
        """reservations.read NO abre escrituras: POST cancel exige delete."""
        _seed_booking(db, booking_id="BK-CANCEL", status="pending")
        resp = await client.post("/api/reservations/BK-CANCEL/cancel?prop_id=1", json={})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_booking_detail_404_of_another_hotel(self, client, db, hotel_analista):
        _seed_booking(db, booking_id="BK-OTRO", prop_id=2)
        resp = await client.get("/api/reservations/BK-OTRO?prop_id=1")
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_detail_staff_403_without_assignment_inline(self, client, db, global_analista):
        """GET /{booking_id} es MIXTO: staff (no cliente) sin role_assignment
        recibe 403 INLINE incluso con prop_id (el rol global no basta)."""
        _seed_booking(db, booking_id="BK-STAFF")
        resp = await client.get("/api/reservations/BK-STAFF", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_detail_200_with_hotel_role(self, client, db, hotel_analista):
        _seed_booking(db, booking_id="BK-1")
        resp = await client.get("/api/reservations/BK-1", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_options_global_exception_without_prop_id(self, client, global_analista):
        """Picker multi-hotel: reservations.read GLOBAL basta SIN prop_id."""
        resp = await client.get("/api/reservations/options")
        assert resp.status_code == 200, resp.text
