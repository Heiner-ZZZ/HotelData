"""Hotel products: gates por-hotel (Migración E).

- CRUD/restock con ``prop_id`` en el PATH → ``require_prop_permission``
  (resolución por path).
- Reports por hotel (prop_id query) → ``require_prop_permission``.
- Line-items de reserva: ``prop_id`` por QUERY + pertenencia del booking al
  hotel (404 cross-hotel).
- Earnings (``users.manage``) siguen GLOBALES por diseño (plataforma).

Deny-by-default: sin ``role_assignments`` el rol GLOBAL no es fallback.
"""
from __future__ import annotations

import pytest
from _prop_gate_helpers import login, seed_hotel, seed_hotel_role, seed_user
from bson import ObjectId


def _seed_global_user(db, *, code: str, hotel: int = 1) -> dict[str, str]:
    return seed_user(
        db,
        username=f"staff_prod_{code.split('.')[0]}",
        role="staff_prod_global",
        permissions=[code],
        assigned_hotels=[hotel],
    )


def _assign(db, user_id: str, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {"user_id": ObjectId(user_id), "prop_id": prop_id, "role_id": role_id}
    )


class TestProductsCrudPropGate:
    @pytest.mark.asyncio
    async def test_list_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, code="properties.read")
        await login(client, creds)
        resp = await client.get("/api/management/products/hotels/1")
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, code="properties.read")
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["properties.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.get("/api/management/products/hotels/1")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_reports_margin_403_global_role(self, client, db):
        creds = _seed_global_user(db, code="inventory.products.cost.read")
        await login(client, creds)
        resp = await client.get("/api/management/products/reports/margin", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_restock_403_global_role(self, client, db):
        creds = _seed_global_user(db, code="inventory.products.cost.manage")
        await login(client, creds)
        resp = await client.post(
            "/api/management/products/hotels/1/PROD-1/restock",
            params={"prop_id": 1},
            json={"qty": 5, "cost_price": 10},
        )
        assert resp.status_code == 403, resp.text


class TestProductsLineItemsPropGate:
    @pytest.mark.asyncio
    async def test_line_items_404_booking_of_another_hotel(self, client, db):
        """Cross-hotel: booking del hotel 2 NO es legible con prop_id=1."""
        creds = _seed_global_user(db, code="reservations.read")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        db.booking_orders.insert_one({"booking_id": "BK-OTRO", "prop_id": 2})
        await login(client, creds)
        resp = await client.get(
            "/api/management/products/bookings/BK-OTRO/line-items",
            params={"prop_id": 1},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_line_items_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, code="reservations.read")
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["reservations.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        db.booking_orders.insert_one({"booking_id": "BK-1", "prop_id": 1})
        await login(client, creds)
        resp = await client.get(
            "/api/management/products/bookings/BK-1/line-items",
            params={"prop_id": 1},
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_line_items_403_global_role(self, client, db):
        creds = _seed_global_user(db, code="reservations.read")
        await login(client, creds)
        resp = await client.get(
            "/api/management/products/bookings/BK-1/line-items",
            params={"prop_id": 1},
        )
        assert resp.status_code == 403, resp.text
