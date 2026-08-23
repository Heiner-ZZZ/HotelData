"""Migración E (2026-08): reseñas — moderación/staff POR HOTEL — tests.

Rol GLOBAL con ``reviews.read`` SIN role_assignment → 403 en las rutas staff
(con prop_id). Con el rol del hotel → 200. Sin prop_id → 400. Reseña de
otro hotel → 404 en moderate. El listado GET "" con prop_id gatea INLINE
(staff); la creación del huésped sigue global.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from bson import ObjectId

from tests._prop_gate_helpers import login, now, seed_catalog, seed_hotel, seed_hotel_role, seed_user

CATALOG = ["reviews.read", "reviews.moderate"]


def _seed_review(db, *, prop_id: int = 1, review_id: ObjectId | None = None,
                 status: str = "pending") -> ObjectId:
    oid = review_id or ObjectId()
    db.reviews.insert_one(
        {"_id": oid, "prop_id": prop_id, "rating": 5, "title": "Bueno",
         "comment": "Todo bien", "moderation_status": status,
         "user_id": ObjectId(), "created_at": now()}
    )
    return oid


@pytest_asyncio.fixture
async def global_analista(client, db):
    seed_catalog(db, CATALOG)
    seed_hotel(db, 1)
    creds = seed_user(db, username="analista_rev_global", role="reviews_manager",
                      permissions=["reviews.read"], assigned_hotels=[1])
    await login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_rev", permissions=["reviews.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_moderador(client, db, global_analista):
    role_id = seed_hotel_role(db, name="rol_hotel_rev_moderate",
                              permissions=["reviews.read", "reviews.moderate"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestReviewsPropGate:
    @pytest.mark.asyncio
    async def test_reputation_dashboard_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/reviews/reputation/dashboard", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_reputation_dashboard_400_without_prop_id(self, client, db, admin_user):
        await login(client, admin_user)
        resp = await client.get("/api/reviews/reputation/dashboard")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_reputation_dashboard_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/reviews/reputation/dashboard", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_list_with_prop_id_and_staff_filter_gates_inline(self, client, global_analista):
        """GET "" con prop_id + filtro de moderación es staff: rol global sin
        asignación → 403 INLINE (el rol global no basta en contexto de hotel)."""
        resp = await client.get(
            "/api/reviews", params={"prop_id": 1, "moderation_status": "pending"}
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_without_prop_id_global(self, client, global_analista):
        """GET "" sin prop_id: flujo huésped/multi-hotel → 200 (global)."""
        resp = await client.get("/api/reviews")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/reviews", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_moderate_404_of_another_hotel(self, client, db, hotel_moderador):
        review_id = _seed_review(db, prop_id=2)
        resp = await client.patch(
            f"/api/reviews/{review_id}/moderate?prop_id=1",
            json={"status": "approved", "reason": ""},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_moderate_passes_gate_with_role(self, client, db, hotel_moderador):
        """El write con reviews.moderate pasa el GATE (nunca 403): el status
        downstream es negocio de moderación."""
        review_id = _seed_review(db, prop_id=1, status="pending")
        resp = await client.patch(
            f"/api/reviews/{review_id}/moderate?prop_id=1",
            json={"status": "approved", "reason": ""},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_moderate_403_with_read_only(self, client, db, hotel_analista):
        """reviews.read NO abre moderación (separación read/moderate)."""
        review_id = _seed_review(db, prop_id=1)
        resp = await client.patch(
            f"/api/reviews/{review_id}/moderate?prop_id=1",
            json={"status": "approved", "reason": ""},
        )
        assert resp.status_code == 403, resp.text
