"""Migración E (2026-08): propiedades y habitaciones gatean POR HOTEL.

Un usuario cuyo rol GLOBAL tiene ``properties.read``/``rooms.read`` pero SIN
``role_assignment`` para el hotel recibe 403; con el rol del hotel que otorga
el código → 200. ``read`` NO abre escrituras. Los catálogos maestros y las
vistas multi-hotel (options, room-features, history) siguen globales.
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
    for code in ("properties.read", "properties.update", "rooms.read", "rooms.update",
                 "rooms.manage", "audit.read"):
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
            "name": "rol_hotel_props",
            "display_name": "Rol Hotel Props",
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
    """Rol GLOBAL con properties.read + rooms.read, SIN role_assignment."""
    _seed_catalog(db)
    _seed_hotel(db, 1)
    creds = _seed_user(db, username="analista_props_global", role="props_manager",
                       permissions=["properties.read", "rooms.read", "audit.read"],
                       assigned_hotels=[1])
    await _login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = _seed_hotel_role(db, permissions=["properties.read", "rooms.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_editor(client, db, global_analista):
    """Hotel role con SOLO properties.update + rooms.manage: no abre lecturas."""
    role_id = _seed_hotel_role(db, permissions=["properties.update", "rooms.manage"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestPropertiesRoomsPropGate:
    """Operación de propiedades/habitaciones = por hotel."""

    # ── Propiedades ──

    @pytest.mark.asyncio
    async def test_property_detail_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/management/properties/1")
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_property_detail_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/properties/1")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_property_profile_update_403_with_read_only(self, client, hotel_analista):
        """properties.read NO abre escrituras: PUT /profile exige update."""
        resp = await client.put(
            "/api/management/properties/1/profile",
            json={"hotel_name": "Hotel 1", "display_name": "Hotel 1",
                  "description": "x", "display_country_label": "PE"},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_property_profile_update_passes_gate_with_update(self, client, hotel_editor):
        resp = await client.put(
            "/api/management/properties/1/profile",
            json={"hotel_name": "Hotel 1", "display_name": "Hotel 1",
                  "description": "x", "display_country_label": "PE"},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_property_history_global_exception_with_audit_read(self, client, db, global_analista):
        """Historial de cambios = auditoría de plataforma (audit.read global,
        sin role_assignment) → 200 SIN contexto de hotel."""
        db.content_changes.insert_one(
            {"prop_id": 1, "entity_type": "profile", "field": "hotel_name",
             "old_value": "A", "new_value": "B", "changed_by": "tester",
             "changed_at": _now()}
        )
        resp = await client.get("/api/management/properties/1/history")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_properties_options_global_exception_without_prop_id(self, client, global_analista):
        resp = await client.get("/api/management/properties/options")
        assert resp.status_code == 200, resp.text

    # ── Habitaciones ──

    @pytest.mark.asyncio
    async def test_rooms_list_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/management/rooms", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_rooms_list_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/management/rooms", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_rooms_create_403_with_read_only(self, client, hotel_analista):
        resp = await client.post(
            "/api/management/rooms?prop_id=1",
            json={"prop_id": 1, "name": "Estándar", "max_adults": 2,
                  "max_children": 0, "base_capacity": 2, "is_active": True},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_rooms_create_passes_gate_with_manage(self, client, hotel_editor):
        resp = await client.post(
            "/api/management/rooms?prop_id=1",
            json={"prop_id": 1, "name": "Estándar", "max_adults": 2,
                  "max_children": 0, "base_capacity": 2, "is_active": True},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_room_type_update_404_of_another_hotel(self, client, db, hotel_editor):
        room_type_id = "RT-2-otro"
        db.room_types.insert_one(
            {"prop_id": 2, "room_type_id": room_type_id, "name": "Otro",
             "max_adults": 2, "max_children": 0, "base_capacity": 2}
        )
        resp = await client.put(
            f"/api/management/rooms/{room_type_id}?prop_id=1",
            json={"name": "Otro", "max_adults": 2, "max_children": 0,
                  "base_capacity": 2, "is_active": True},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_room_features_get_200_with_hotel_role(self, client, db, hotel_analista):
        room_type_id = "RT-1-estandar"
        db.room_types.insert_one(
            {"prop_id": 1, "room_type_id": room_type_id, "name": "Estándar",
             "max_adults": 2, "max_children": 0, "base_capacity": 2}
        )
        resp = await client.get(
            f"/api/management/room-features/{room_type_id}", params={"prop_id": 1}
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_room_features_catalog_global_exception_without_prop_id(self, client, global_analista):
        """Catálogo maestro de features: rooms.read GLOBAL basta SIN prop_id."""
        resp = await client.get("/api/management/room-features")
        assert resp.status_code == 200, resp.text
