"""Instay staff: gates por-hotel (Migración E).

Las operaciones del staff inbox (sesiones, service requests, conversaciones,
stream) operan POR HOTEL: ``prop_id`` por QUERY obligatorio +
``require_prop_permission`` (deny-by-default sin ``role_assignments``), y los
recursos (sesión por token, request por id, booking) deben pertenecer al
hotel pedido (404 cross-hotel). Las escrituras con ``prop_id`` en el body
validan consistencia query↔body (hueco del middleware).

Las rutas de HUÉSPED (``/api/stay/guest/*``) son token-based sin gate —
auto-servicio, no se tocan.
"""
from __future__ import annotations

import pytest
from _prop_gate_helpers import login, seed_hotel, seed_hotel_role, seed_user
from bson import ObjectId


def _seed_global_user(db, *, code: str, hotel: int = 1) -> dict[str, str]:
    return seed_user(
        db,
        username=f"staff_stay_{code.split('.')[0]}",
        role="staff_stay_global",
        permissions=[code],
        assigned_hotels=[hotel],
    )


def _assign(db, user_id: str, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {"user_id": ObjectId(user_id), "prop_id": prop_id, "role_id": role_id}
    )


class TestStaySessionsPropGate:
    @pytest.mark.asyncio
    async def test_list_400_without_prop_id(self, client, db):
        """Sin contexto de hotel → 400 (deny-by-default)."""
        creds = _seed_global_user(db, code="reservations.read")
        await login(client, creds)
        resp = await client.get("/api/stay/sessions")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_list_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, code="reservations.read")
        await login(client, creds)
        resp = await client.get("/api/stay/sessions", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, code="reservations.read")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.get("/api/stay/sessions", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_create_400_without_query_prop_id_even_with_body(self, client, db):
        """El body con prop_id NO basta: sin query → 400 (hueco del middleware)."""
        creds = _seed_global_user(db, code="reservations.manage")
        await login(client, creds)
        resp = await client.post(
            "/api/stay/sessions",
            json={"booking_id": "BK-1", "prop_id": 1, "room_label": "101", "guest_name": "X",
                  "check_in": "2026-08-22", "check_out": "2026-08-23"},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_create_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, code="reservations.manage")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1})
        await login(client, creds)
        resp = await client.post(
            "/api/stay/sessions",
            params={"prop_id": 1},
            json={"booking_id": "BK-1", "prop_id": 1, "room_label": "101", "guest_name": "X",
                  "check_in": "2026-08-22", "check_out": "2026-08-23"},
        )
        assert resp.status_code == 201, resp.text

    @pytest.mark.asyncio
    async def test_token_404_session_of_another_hotel(self, client, db):
        """Cross-hotel: sesión del hotel 2 NO es legible con prop_id=1."""
        creds = _seed_global_user(db, code="reservations.read")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        db.stay_sessions.insert_one({"token": "TOK-OTRO", "prop_id": 2, "active": True})
        await login(client, creds)
        resp = await client.get(
            "/api/stay/sessions/TOK-OTRO",
            params={"prop_id": 1},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_token_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, code="reservations.read")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        db.stay_sessions.insert_one({"token": "TOK-1", "prop_id": 1, "active": True})
        await login(client, creds)
        resp = await client.get("/api/stay/sessions/TOK-1", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text


class TestStayRequestsPropGate:
    @pytest.mark.asyncio
    async def test_update_404_request_of_another_hotel(self, client, db):
        """Cross-hotel: request del hotel 2 NO es editable con prop_id=1."""
        creds = _seed_global_user(db, code="reservations.read")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        req_id = db.stay_service_requests.insert_one(
            {"prop_id": 2, "status": "in_progress"}
        ).inserted_id
        await login(client, creds)
        resp = await client.put(
            f"/api/stay/requests/{req_id}",
            params={"prop_id": 1},
            json={"status": "completed"},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_analytics_403_global_role(self, client, db):
        creds = _seed_global_user(db, code="reports.requests.read")
        await login(client, creds)
        resp = await client.get(
            "/api/stay/requests/analytics",
            params={"prop_id": 1},
        )
        assert resp.status_code == 403, resp.text
