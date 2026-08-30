"""Amenities: gates por-hotel (Migración E).

Antes: CRUD/photos/stock con ``require_permission("amenities.*")`` GLOBAL y
``prop_id`` solo en el body para las escrituras (hueco del middleware).

Ahora:
- ``PUT /api/management/amenities`` y ``/special-requests`` → prop_id por
  QUERY obligatorio + consistencia query↔body, gate ``amenities.manage``.
- ``POST /api/management/amenities/photos`` (prop_id ya en query) y
  ``GET .../photos`` → gate ``amenities.manage`` / ``amenities.read``.
- ``DELETE .../photos/{photo_id}`` → gate + la foto debe pertenecer al hotel
  pedido (404 cross-hotel; el doc amenity_photos guarda prop_id).
- ``PUT /api/amenities/stock`` → prop_id por QUERY + consistencia.
Deny-by-default: sin ``role_assignments`` el rol GLOBAL no es fallback.
"""
from __future__ import annotations

from typing import ClassVar

import pytest
from _prop_gate_helpers import login, seed_hotel, seed_hotel_role, seed_user
from bson import ObjectId


def _seed_global_user(db, *, codes: list[str], hotel: int = 1) -> dict[str, str]:
    """Rol GLOBAL con los códigos (el hueco pre-E) sin role_assignment."""
    return seed_user(
        db,
        username=f"staff_amen_{abs(hash(tuple(codes))) % 10_000}",
        role="staff_amen_global",
        permissions=codes,
        assigned_hotels=[hotel],
    )


def _assign(db, user_id: str, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {"user_id": ObjectId(user_id), "prop_id": prop_id, "role_id": role_id}
    )


class TestAmenitiesUpdatePropGate:
    _PATH = "/api/management/amenities"
    _BODY: ClassVar[dict[str, object]] = {"prop_id": 1, "active_amenities": []}

    @pytest.mark.asyncio
    async def test_put_400_without_query_prop_id_even_with_body(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        await login(client, creds)
        resp = await client.put(self._PATH, json=self._BODY)
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_put_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        await login(client, creds)
        resp = await client.put(self._PATH, params={"prop_id": 1}, json=self._BODY)
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_put_400_on_body_query_mismatch(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["amenities.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.put(
            self._PATH, params={"prop_id": 1}, json={**self._BODY, "prop_id": 2}
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_put_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["amenities.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.put(self._PATH, params={"prop_id": 1}, json=self._BODY)
        assert resp.status_code == 200, resp.text


class TestSpecialRequestsPropGate:
    _PATH = "/api/management/amenities/special-requests"
    _BODY: ClassVar[dict[str, object]] = {"prop_id": 1, "special_requests": []}

    @pytest.mark.asyncio
    async def test_put_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        await login(client, creds)
        resp = await client.put(self._PATH, params={"prop_id": 1}, json=self._BODY)
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_put_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["amenities.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.put(self._PATH, params={"prop_id": 1}, json=self._BODY)
        assert resp.status_code == 200, resp.text


class TestAmenityPhotosPropGate:
    @pytest.mark.asyncio
    async def test_list_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.read"])
        await login(client, creds)
        resp = await client.get(
            "/api/management/amenities/photos", params={"prop_id": 1, "amenity_label": "Spa"}
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.read"])
        role_id = seed_hotel_role(db, prop_id=1, name="recepcionista_1", permissions=["amenities.read"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.get(
            "/api/management/amenities/photos", params={"prop_id": 1, "amenity_label": "Spa"}
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_upload_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        await login(client, creds)
        resp = await client.post(
            "/api/management/amenities/photos",
            params={"prop_id": 1, "amenity_label": "Spa"},
            files={"file": ("foto.png", b"data", "image/png")},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_delete_404_photo_of_another_hotel(self, client, db):
        """Cross-hotel: foto del hotel 2 NO es borrable pasando prop_id=1."""
        creds = _seed_global_user(db, codes=["amenities.manage"])
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["amenities.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        gridfs_id = ObjectId()
        db.amenity_photos.insert_one(
            {"prop_id": 2, "amenity_label": "Spa", "gridfs_id": gridfs_id, "filename": "x.png"}
        )
        await login(client, creds)
        resp = await client.delete(
            f"/api/management/amenities/photos/{gridfs_id}",
            params={"prop_id": 1},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_delete_200_photo_of_same_hotel(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["amenities.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        gridfs_id = ObjectId()
        db.amenity_photos.insert_one(
            {"prop_id": 1, "amenity_label": "Spa", "gridfs_id": gridfs_id, "filename": "x.png"}
        )
        await login(client, creds)
        resp = await client.delete(
            f"/api/management/amenities/photos/{gridfs_id}",
            params={"prop_id": 1},
        )
        assert resp.status_code == 200, resp.text


class TestAmenityStockPropGate:
    _PATH = "/api/amenities/stock"
    _BODY: ClassVar[dict[str, object]] = {"prop_id": 1, "amenity_label": "Spa", "total_stock": 10, "room_type_id": ""}

    @pytest.mark.asyncio
    async def test_put_403_global_role_without_hotel_assignment(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        await login(client, creds)
        resp = await client.put(self._PATH, params={"prop_id": 1}, json=self._BODY)
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_put_200_with_hotel_role(self, client, db):
        creds = _seed_global_user(db, codes=["amenities.manage"])
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["amenities.manage"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.put(self._PATH, params={"prop_id": 1}, json=self._BODY)
        assert resp.status_code == 200, resp.text
