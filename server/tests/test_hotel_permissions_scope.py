"""Scope del catálogo en el editor de roles del hotel (C 2026-08).

- ``list_hotel_roles.permission_codes`` expone SOLO códigos de scope HOTEL:
  ETL, usuarios, roles, auditoría, settings, properties.approve, cartera
  estratégica (system) y account.*/search.* (guest) NO aparecen.
- La API rechaza 400 cualquier código system/guest al crear/editar un rol de
  hotel (ocultarlo del editor no basta — defensa en profundidad).
- Clonar una plantilla global hereda SOLO la tajada hotel: los códigos de
  plataforma de la plantilla se descartan silenciosamente (el rol del hotel
  jamás porta permisos que no puede tener).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient
from passlib.context import CryptContext

from src.app.security.permissions import user_has_permission

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

CATALOG = [
    "etl.execute",
    "etl.read",
    "users.manage",
    "roles.read",
    "properties.approve",
    "account.read",
    "search.read",
    "dashboard.read",
    "reservations.manage",
    "reservations.read",
    "hr.portal.read",
    "hr.directory.read",
    "hotel.manage_roles",
]

HOTEL_VISIBLE = sorted(
    ["dashboard.read", "hr.directory.read", "hr.portal.read", "hotel.manage_roles", "reservations.manage", "reservations.read"]
)


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_catalog(db) -> None:
    # Sin campo ``scope`` a propósito: el filtro runtime usa el mapa canónico
    # (permission_scope), no la BD — así funciona aunque la colección aún no
    # haya sido migrada por el seed.
    for code in CATALOG:
        db.permissions.insert_one(
            {
                "permission_code": code,
                "description": code,
                "is_system": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )


def _seed_user(db, *, username: str, assigned_hotels: list[int]) -> ObjectId:
    return db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username.title(),
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "gerente_hotel",
            "role_ids": [],
            "assigned_hotels": assigned_hotels,
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id


@pytest_asyncio.fixture
async def logged_hotel_admin(client, db):
    _seed_catalog(db)
    role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "gerente_hotel",
            "display_name": "Gerente - Hotel 1",
            "permissions": ["hotel.manage_roles", "dashboard.read"],
            "is_active": True,
            "is_system": False,
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    user_id = _seed_user(db, username="gerente_scope", assigned_hotels=[1])
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": 1,
            "role_id": role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "gerente_scope", "password": "Pass123!"},
    )
    assert resp.status_code == 200, resp.text
    return client


class TestHotelRoleEditorScope:
    """El editor del hotel solo ve/otorga códigos de scope hotel."""

    @pytest.mark.asyncio
    async def test_list_roles_exposes_only_hotel_scope_codes(self, logged_hotel_admin, db):
        resp = await logged_hotel_admin.get("/api/management/hotels/1/roles")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert sorted(data["permission_codes"]) == HOTEL_VISIBLE, (
            f"permission_codes debe excluir system/guest; got {data['permission_codes']}"
        )
        assert "etl.execute" not in data["permission_codes"]
        assert "users.manage" not in data["permission_codes"]
        assert "account.read" not in data["permission_codes"]

    @pytest.mark.asyncio
    async def test_create_role_rejects_system_code(self, logged_hotel_admin):
        resp = await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "Con ETL", "display_name": "Con ETL", "permissions": ["etl.execute"]},
        )
        assert resp.status_code == 400, resp.text
        assert "etl.execute" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_role_rejects_guest_code(self, logged_hotel_admin):
        resp = await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "Con Guest", "display_name": "Con Guest", "permissions": ["account.read"]},
        )
        assert resp.status_code == 400, resp.text
        assert "account.read" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_role_accepts_hotel_codes(self, logged_hotel_admin, db):
        resp = await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "Recepcion", "display_name": "Recepción", "permissions": ["reservations.manage", "dashboard.read"]},
        )
        assert resp.status_code == 201, resp.text
        doc = db.hotel_roles.find_one({"name": "Recepcion"})
        assert doc is not None
        assert set(doc["permissions"]) == {"reservations.manage", "reservations.read", "dashboard.read"}
        # ensure_read_dependencies agregó reservations.read (hotel).

    @pytest.mark.asyncio
    async def test_update_role_rejects_system_code(self, logged_hotel_admin, db):
        role_id = db.hotel_roles.insert_one(
            {
                "prop_id": 1,
                "name": "A Editar",
                "display_name": "A Editar",
                "permissions": ["dashboard.read"],
                "is_active": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        ).inserted_id
        resp = await logged_hotel_admin.put(
            f"/api/management/hotels/1/roles/{role_id}",
            json={"permissions": ["dashboard.read", "etl.read"]},
        )
        assert resp.status_code == 400, resp.text
        assert "etl.read" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_clone_template_strips_system_codes(self, logged_hotel_admin, db):
        template_id = db.roles.insert_one(
            {
                "role_name": "gerente_scope",
                "display_name": "Gerente Scope",
                "permissions": ["reservations.read", "properties.approve", "etl.read"],
                "is_template": True,
                "is_system": True,
                "created_at": _now(),
            }
        ).inserted_id
        resp = await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "Clon Scope", "display_name": "Clon", "based_on_role_id": str(template_id)},
        )
        assert resp.status_code == 201, resp.text
        doc = db.hotel_roles.find_one({"name": "Clon Scope"})
        assert doc is not None
        assert doc["permissions"] == ["reservations.read"], (
            "el clon no debe heredar códigos system de la plantilla; "
            f"got {doc['permissions']}"
        )

    def test_no_global_fallback_in_hotel_context(self, db):
        """D 2026-08 (contrato documentado en require_prop_permission):
        deny-by-default en contexto de hotel — el rol GLOBAL NUNCA es fallback.
        Un usuario con el código en su rol global pero SIN role_assignment para
        el hotel NO tiene el permiso en ese hotel (evita escalada entre
        hoteles); sin contexto de hotel, el rol global sí vale (legado)."""
        role_id = db.roles.insert_one(
            {
                "role_name": "housekeeping",
                "display_name": "Housekeeping",
                "permissions": ["hr.portal.read"],
                "is_system": True,
                "created_at": _now(),
            }
        ).inserted_id
        user_id = db.users.insert_one(
            {
                "username": "sin_asignacion",
                "email": "sin_asignacion@hotel.local",
                "display_name": "Sin Asignación",
                "password_hash": _pwd.hash("Pass123!"),
                "primary_role": "housekeeping",
                "role_ids": [role_id],
                "assigned_hotels": [1],
                "is_active": True,
                "created_at": _now(),
            }
        ).inserted_id
        user = db.users.find_one({"_id": user_id})

        assert user_has_permission(db, user, "hr.portal.read", prop_id=1) is False, (
            "sin role_assignment para el hotel, el rol global NO debe otorgar el permiso"
        )
        assert user_has_permission(db, user, "hr.portal.read") is True, (
            "sin contexto de hotel, la resolución global legacy sigue vigente"
        )

    def test_scrub_removes_non_hotel_codes_from_hotel_roles(self, db):
        """Limpieza de datos (C 2026-08): hotel_roles históricos con códigos
        system/guest (clones previos al scope) se depuran a solo-scope-hotel,
        con audit entry por rol. Idempotente: roles limpios no se tocan."""
        from src.app.modules.hotel_permissions.service import scrub_hotel_role_scopes

        db.hotel_roles.insert_one(
            {
                "prop_id": 1,
                "name": "Con Basura",
                "display_name": "Con Basura",
                "permissions": ["reservations.read", "etl.read", "account.read", "users.manage"],
                "is_active": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
        db.hotel_roles.insert_one(
            {
                "prop_id": 1,
                "name": "Limpio",
                "display_name": "Limpio",
                "permissions": ["dashboard.read", "reservations.read"],
                "is_active": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )

        result = scrub_hotel_role_scopes(db, changed_by="test-scope")

        assert result["scanned"] == 2
        assert result["updated"] == 1
        assert result["removed_codes"] == {"Con Basura": ["account.read", "etl.read", "users.manage"]}
        con_basura = db.hotel_roles.find_one({"name": "Con Basura"})
        assert con_basura["permissions"] == ["reservations.read"], con_basura["permissions"]
        limpio = db.hotel_roles.find_one({"name": "Limpio"})
        assert limpio["permissions"] == ["dashboard.read", "reservations.read"], "rol limpio no debe tocarse"
        # Trazabilidad: un audit entry por rol depurado.
        entries = list(
            db.audit_log.find(
                {"entity_type": "hotel_role", "action": "scope_cleanup"},
                {"_id": 0, "entity_id": 1, "diff": 1, "changed_by": 1},
            )
        )
        assert len(entries) == 1
        assert entries[0]["changed_by"] == "test-scope"
        assert entries[0]["diff"]["permissions"]["old"] == ["reservations.read", "etl.read", "account.read", "users.manage"]
        assert entries[0]["diff"]["permissions"]["new"] == ["reservations.read"]

        # Idempotente: segunda corrida no toca nada.
        again = scrub_hotel_role_scopes(db)
        assert again["updated"] == 0
        assert db.audit_log.count_documents({"entity_type": "hotel_role", "action": "scope_cleanup"}) == 1
