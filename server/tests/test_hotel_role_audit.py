"""Auditoría por rol — panel de auditoría del hotel_role (Fase 2 + audit trail).

Cubre la pista de auditoría de ``hotel_roles``:

1. Las mutaciones (create/update/delete) escriben entradas en ``audit_log``
   con ``entity_type="hotel_role"``, ``entity_id=str(role_id)``, el actor
   (``changed_by``) y un ``diff`` de permisos (``permissions: {old, new}``).
2. El endpoint ``GET /api/management/hotels/{prop_id}/roles/{role_id}/audit``
   devuelve el resumen del rol (creador, fechas, plantilla base, conteo de
   permisos) + el historial cronológico de cambios, protegido con
   ``require_prop_permission("hotel.manage_roles")``.
3. Roles creados antes del audit trail (sin entradas) responden 200 con
   historial vacío pero con ``created_by``/fechas del documento.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient
from passlib.context import CryptContext

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

CATALOG_CODES = [
    "hotel.manage_roles",
    "dashboard.read",
    "reservations.read",
    "reservations.manage",
    "hr.read",
    "payments.read",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_catalog(db) -> None:
    for code in CATALOG_CODES:
        db.permissions.insert_one(
            {
                "permission_code": code,
                "description": code,
                "is_system": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )


def _seed_user(db, *, username: str, email: str, assigned_hotels: list[int]) -> ObjectId:
    return db.users.insert_one(
        {
            "username": username,
            "email": email,
            "display_name": username.title(),
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "recepcionista",
            "role_ids": [],
            "assigned_hotels": assigned_hotels,
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id


# ── Fixtures (mismo patrón que test_hotel_permissions_api.py) ──


@pytest.fixture
def hotel_permissions_catalog(db):
    _seed_catalog(db)
    return CATALOG_CODES


@pytest.fixture
def hotel_admin_role(db, hotel_permissions_catalog):
    role_id = db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": ["dashboard.read", "reservations.read", "hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    return db.roles.find_one({"_id": role_id})


@pytest.fixture
def hotel_admin_hotel_role(db, hotel_admin_role):
    role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "gerente_hotel",
            "display_name": "Gerente - Hotel 1",
            "permissions": ["dashboard.read", "reservations.read", "hotel.manage_roles"],
            "based_on_role_id": hotel_admin_role["_id"],
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    return db.hotel_roles.find_one({"_id": role_id})


@pytest.fixture
def hotel_admin_user(db, hotel_admin_hotel_role):
    user_id = _seed_user(db, username="gerente1", email="gerente1@hotel.local", assigned_hotels=[1])
    db.users.update_one({"_id": user_id}, {"$set": {"primary_role": "gerente_hotel"}})
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": 1,
            "role_id": hotel_admin_hotel_role["_id"],
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )
    return db.users.find_one({"_id": user_id})


@pytest_asyncio.fixture
async def logged_hotel_admin(client: AsyncClient, hotel_admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "gerente1", "password": "Pass123!"},
    )
    assert resp.status_code == 200, resp.text
    return client


def _audit_entries(db, role_id: str) -> list[dict]:
    return list(
        db.audit_log.find(
            {"entity_type": "hotel_role", "entity_id": role_id}
        ).sort("timestamp", 1)
    )


# ── Writes de auditoría en las mutaciones ──


async def test_role_audit_create_writes_entry(logged_hotel_admin: AsyncClient, db):
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={
            "name": "recepcionista",
            "display_name": "Recepcionista Hotel 1",
            "permissions": ["dashboard.read", "reservations.manage"],
        },
    )
    assert resp.status_code == 201, resp.text
    rid = resp.json()["id"]

    entries = _audit_entries(db, rid)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["action"] == "create"
    assert entry["changed_by"] == "gerente1"
    assert entry["entity_type"] == "hotel_role"
    assert entry["entity_id"] == rid
    assert entry["diff"]["permissions"]["old"] == []
    assert set(entry["diff"]["permissions"]["new"]) == {
        "dashboard.read",
        "reservations.manage",
        "reservations.read",  # ensure_read_dependencies
    }


async def test_role_audit_update_writes_permission_diff(logged_hotel_admin: AsyncClient, db):
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={
            "display_name": "Recepcionista (editado)",
            "permissions": ["dashboard.read", "reservations.manage", "hr.read"],
        },
    )
    assert resp.status_code == 200, resp.text

    entries = _audit_entries(db, rid)
    assert len(entries) == 2
    update = entries[-1]
    assert update["action"] == "update"
    assert update["changed_by"] == "gerente1"
    diff = update["diff"]["permissions"]
    assert set(diff["old"]) == {"dashboard.read", "reservations.read"}
    assert set(diff["new"]) == {"dashboard.read", "reservations.manage", "reservations.read", "hr.read"}
    # display_name también queda en el diff
    assert "display_name" in update["diff"]


async def test_role_audit_delete_writes_entry(logged_hotel_admin: AsyncClient, db):
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "temporal", "permissions": ["dashboard.read"]},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    resp = await logged_hotel_admin.delete(f"/api/management/hotels/1/roles/{rid}")
    assert resp.status_code == 200, resp.text

    entries = _audit_entries(db, rid)
    assert len(entries) == 2
    delete = entries[-1]
    assert delete["action"] == "delete"
    assert delete["changed_by"] == "gerente1"
    assert delete["diff"]["permissions"]["new"] == []


async def test_role_audit_update_without_permission_change_has_no_permissions_diff(
    logged_hotel_admin: AsyncClient, db
):
    """Solo renombrar el rol no debe escribir un diff de permisos."""
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
    )
    rid = create.json()["id"]

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"display_name": "Solo renombrado"},
    )
    assert resp.status_code == 200, resp.text

    entries = _audit_entries(db, rid)
    assert entries[-1]["action"] == "update"
    assert "permissions" not in entries[-1]["diff"]
    assert "display_name" in entries[-1]["diff"]


# ── Endpoint GET /roles/{role_id}/audit ──


async def test_role_audit_endpoint_returns_creator_dates_and_history(
    logged_hotel_admin: AsyncClient, db
):
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={
            "name": "recepcionista",
            "display_name": "Recepcionista Hotel 1",
            "permissions": ["dashboard.read", "reservations.read"],
        },
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]
    await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.manage", "hr.read"]},
    )

    resp = await logged_hotel_admin.get(f"/api/management/hotels/1/roles/{rid}/audit")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["id"] == rid
    assert body["created_by"] == "gerente1"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None
    assert body["permission_count"] == 4  # incluye reservations.read (dependency)
    assert isinstance(body["entries"], list)
    assert len(body["entries"]) == 2
    # Orden cronológico: create → update
    assert body["entries"][0]["action"] == "create"
    assert body["entries"][1]["action"] == "update"
    assert body["entries"][1]["changed_by"] == "gerente1"
    assert "permissions" in body["entries"][1]["diff"]
    assert body["entries"][1]["timestamp"] >= body["entries"][0]["timestamp"]


async def test_role_audit_endpoint_shows_template_base(logged_hotel_admin: AsyncClient, db, hotel_admin_role):
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={
            "name": "clon",
            "based_on_role_id": str(hotel_admin_role["_id"]),
            "permissions": ["dashboard.read"],
        },
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]

    resp = await logged_hotel_admin.get(f"/api/management/hotels/1/roles/{rid}/audit")
    assert resp.status_code == 200
    assert resp.json()["based_on"] == "gerente_hotel"


async def test_role_audit_endpoint_empty_history_for_pre_audit_role(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role
):
    """Rol insertado directamente (simula creación antes del audit trail):
    responde 200 con historial vacío pero con los metadatos del documento."""
    rid = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "legacy_role",
            "display_name": "Rol legado",
            "permissions": ["dashboard.read"],
            "based_on_role_id": hotel_admin_role["_id"],
            "is_active": True,
            "is_system": False,
            "created_by": "system",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id

    resp = await logged_hotel_admin.get(
        f"/api/management/hotels/1/roles/{rid}/audit"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_by"] == "system"
    assert body["permission_count"] == 1
    assert body["based_on"] == "gerente_hotel"
    assert body["entries"] == []


async def test_role_audit_404_for_role_in_another_hotel(
    client: AsyncClient, db, admin_user, hotel_admin_hotel_role
):
    """El rol existe en el hotel 1 pero se consulta en el hotel 2 → 404
    (super_admin tiene alcance global; la ausencia de scope 404 no puede
    enmascarar el 404 del rol)."""
    resp = await client.post(
        "/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, resp.text
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await client.get(f"/api/management/hotels/2/roles/{rid}/audit")
    assert resp.status_code == 404


async def test_role_audit_requires_auth(client: AsyncClient):
    resp = await client.get("/api/management/hotels/1/roles/000000000000000000000000/audit")
    assert resp.status_code == 401


async def test_role_audit_forbidden_without_hotel_manage_roles(
    client: AsyncClient, db, hotel_permissions_catalog, hotel_admin_role, hotel_admin_hotel_role
):
    """Staff con asignación a un rol sin hotel.manage_roles → 403."""
    basic_hotel_role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "recepcionista",
            "display_name": "Recepcionista Hotel 1",
            "permissions": ["dashboard.read", "reservations.read"],
            "based_on_role_id": hotel_admin_role["_id"],
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    staff_id = _seed_user(db, username="staff_audit", email="staff_audit@hotel.local", assigned_hotels=[1])
    db.role_assignments.insert_one(
        {
            "user_id": staff_id,
            "prop_id": 1,
            "role_id": basic_hotel_role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )

    resp = await client.post("/api/auth/login", json={"identifier": "staff_audit", "password": "Pass123!"})
    assert resp.status_code == 200
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await client.get(f"/api/management/hotels/1/roles/{rid}/audit")
    assert resp.status_code == 403
