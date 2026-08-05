"""Fase 1 — RBAC por hotel: hotel_roles + role_assignments + resolución con contexto de prop_id.

Cubre:
- ``ensure_hotel_permission_collections()`` crea ``hotel_roles`` y ``role_assignments`` con índices.
- ``user_has_permission(db, user, code, prop_id=...)`` resuelve permisos desde ``hotel_roles``
  vía ``role_assignments``; sin prop_id conserva la resolución global actual.
- El mismo rol global puede tener permisos DISTINTOS según el hotel (grant/deny por hotel).
- Sin asignación para el hotel → fallback al rol global (backward compat).
- Asignación existente → el rol del hotel es autoritativo (deny-by-default si está inactivo).
- Dependency ``require_prop_permission``: prop_id explícito o resuelto desde el request; 403 si no.
- Migración ``migrate_hotel_roles``: roles → plantillas (is_template), clones por (prop_id, rol),
  backfill de asignaciones, idempotente, ``--dry-run`` y ``--only-prop-id``.

Todos los asserts se hacen contra MongoDB real en ``hoteldata_hub_test`` (fixtures de conftest).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException
from starlette.requests import Request

from scripts.migrate_hotel_roles import migrate_hotel_roles
from src.app.security.collections import (
    HOTEL_ROLES_COLLECTION,
    ROLE_ASSIGNMENTS_COLLECTION,
    ensure_hotel_permission_collections,
)
from src.app.security.dependencies import require_prop_permission
from src.app.security.permissions import user_has_permission
from src.app.security.session import SESSION_COOKIE_NAME, hash_session_token

pytestmark = pytest.mark.asyncio


# ── Helpers ──


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_hotel_role(
    db,
    *,
    prop_id: int,
    permissions: list[str],
    based_on_role_id: ObjectId,
    name: str = "recepcionista",
    is_active: bool = True,
) -> ObjectId:
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": name,
            "display_name": name.title(),
            "permissions": permissions,
            "based_on_role_id": based_on_role_id,
            "is_active": is_active,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id


def _assign(db, user_id: ObjectId, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": prop_id,
            "role_id": role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )


def _seed_session(db, user: dict) -> str:
    token = "test-session-token-001"
    db.user_sessions.insert_one(
        {
            "session_token_hash": hash_session_token(token),
            "user_id": user["_id"],
            "username": user["username"],
            "email": user["email"],
            "is_active": True,
            "created_at": _now(),
            "expires_at": _now(),
        }
    )
    return token


def _make_request(token: str, query: str = "") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/management/hotels/1/roles",
        "raw_path": b"/api/management/hotels/1/roles",
        "query_string": query.encode(),
        "root_path": "",
        "headers": [(b"cookie", f"{SESSION_COOKIE_NAME}={token}".encode())],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }
    return Request(scope)


# ── Fixtures ──


@pytest.fixture
def hotel_staff_role(db):
    """Plantilla global (rol de sistema) con permisos básicos de hotel."""
    role_id = db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["dashboard.read", "reservations.read"],
            "is_template": False,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    return db.roles.find_one({"_id": role_id})


@pytest.fixture
def hotel_staff_user(db, hotel_staff_role):
    """Staff de recepción con assigned_hotels [1, 2] y rol global recepcionista."""
    user_id = db.users.insert_one(
        {
            "username": "staff1",
            "email": "staff1@hotel.local",
            "display_name": "Staff Uno",
            "password_hash": "unused-in-test",
            "primary_role": "recepcionista",
            "primary_role_id": hotel_staff_role["_id"],
            "role_ids": [hotel_staff_role["_id"]],
            "assigned_hotels": [1, 2],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return db.users.find_one({"_id": user_id})


# ── 1. ensure de colecciones ──


async def test_ensure_hotel_permission_collections_creates_both_collections(db):
    ensure_hotel_permission_collections()
    names = set(db.list_collection_names())
    assert HOTEL_ROLES_COLLECTION in names
    assert ROLE_ASSIGNMENTS_COLLECTION in names

    idx_user_prop = next(
        (i for i in db.role_assignments.list_indexes() if i["name"] == "idx_ra_user_prop"),
        None,
    )
    assert idx_user_prop is not None, "falta índice único (user_id, prop_id)"
    assert idx_user_prop.get("unique") is True


# ── 2. Resolución global (backward compat) ──


async def test_global_resolution_without_prop_id_is_unchanged(db, hotel_staff_user):
    assert user_has_permission(db, hotel_staff_user, "reservations.read") is True
    assert user_has_permission(db, hotel_staff_user, "dashboard.read") is True
    assert user_has_permission(db, hotel_staff_user, "payments.read") is False


async def test_super_admin_bypasses_hotel_context(db, admin_user):
    user = db.users.find_one({"_id": ObjectId(admin_user["user_id"])})
    assert user_has_permission(db, user, "anything.at.all", prop_id=7) is True


# ── 3. Resolución con contexto de hotel ──


async def test_hotel_role_grants_permission_not_in_global_role(db, hotel_staff_user, hotel_staff_role):
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read", "reservations.read", "payments.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)

    # El hotel le da payments.read; su rol global no.
    assert user_has_permission(db, hotel_staff_user, "payments.read", prop_id=1) is True
    assert user_has_permission(db, hotel_staff_user, "payments.read") is False


async def test_hotel_role_can_deny_permission_global_role_has(db, hotel_staff_user, hotel_staff_role):
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read"],  # sin reservations.read
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)

    assert user_has_permission(db, hotel_staff_user, "reservations.read", prop_id=1) is False
    assert user_has_permission(db, hotel_staff_user, "reservations.read") is True


async def test_same_user_different_permissions_across_hotels(db, hotel_staff_user, hotel_staff_role):
    # Hotel 1: recepcionista con payments.read. Hotel 2: sin él.
    rich_role = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read", "reservations.read", "payments.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    basic_role = _create_hotel_role(
        db,
        prop_id=2,
        permissions=["dashboard.read", "reservations.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, rich_role)
    _assign(db, hotel_staff_user["_id"], 2, basic_role)

    assert user_has_permission(db, hotel_staff_user, "payments.read", prop_id=1) is True
    assert user_has_permission(db, hotel_staff_user, "payments.read", prop_id=2) is False


async def test_no_assignment_denies_in_hotel_context(db, hotel_staff_user):
    """Guardrail deny-by-default: sin asignación para el hotel, sin acceso.

    El rol global sí tiene dashboard.read/reservations.read, pero en contexto
    de hotel estricto una petición sin asignación deniega (no hace fallback).
    """
    assert user_has_permission(db, hotel_staff_user, "reservations.read", prop_id=1) is False
    assert user_has_permission(db, hotel_staff_user, "reservations.read") is True


async def test_no_assignment_cannot_escalate_across_hotels(db):
    """El rol global no debe abrir permisos en hoteles sin asignación.

    Rol global con payments.read, pero el rol del hotel 1 se lo quita. Sin
    asignación para el hotel 2, el usuario NO puede usar payments.read allí
    (antes, el fallback global lo habría concedido — escalada entre hoteles).
    """
    rich_role_id = db.roles.insert_one(
        {
            "role_name": "recepcionista_amplio",
            "display_name": "Recepcionista Amplio",
            "permissions": ["dashboard.read", "reservations.read", "payments.read"],
            "is_template": False,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    user_id = db.users.insert_one(
        {
            "username": "staff2",
            "email": "staff2@hotel.local",
            "display_name": "Staff Dos",
            "password_hash": "x",
            "primary_role": "recepcionista_amplio",
            "primary_role_id": rich_role_id,
            "role_ids": [rich_role_id],
            "assigned_hotels": [1, 2],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    user = db.users.find_one({"_id": user_id})

    restricted_role = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read", "reservations.read"],  # sin payments.read
        based_on_role_id=rich_role_id,
    )
    _assign(db, user_id, 1, restricted_role)

    # En su hotel asignado (1) el rol de hotel le quita payments.read.
    assert user_has_permission(db, user, "payments.read", prop_id=1) is False
    # En el hotel 2 (sin asignación) tampoco: deny, no fallback al rol global.
    assert user_has_permission(db, user, "payments.read", prop_id=2) is False


async def test_inactive_hotel_role_denies_instead_of_fallback(db, hotel_staff_user, hotel_staff_role):
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["payments.read"],
        based_on_role_id=hotel_staff_role["_id"],
        is_active=False,
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)

    # La asignación existe → el rol inactivo deniega; NO cae al rol global.
    assert user_has_permission(db, hotel_staff_user, "payments.read", prop_id=1) is False
    assert user_has_permission(db, hotel_staff_user, "payments.read") is False


# ── 4. Dependency require_prop_permission ──


async def test_require_prop_permission_grants_with_explicit_prop_id(db, hotel_staff_user, hotel_staff_role):
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read", "reservations.read", "payments.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)
    token = _seed_session(db, hotel_staff_user)

    dependency = require_prop_permission("payments.read", prop_id=1)
    user = dependency(_make_request(token))
    assert user["username"] == "staff1"


async def test_require_prop_permission_denies_403(db, hotel_staff_user, hotel_staff_role):
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read", "reservations.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)
    token = _seed_session(db, hotel_staff_user)

    dependency = require_prop_permission("payments.read", prop_id=1)
    with pytest.raises(HTTPException) as excinfo:
        dependency(_make_request(token))
    assert excinfo.value.status_code == 403
    assert "payments.read" in excinfo.value.detail


async def test_require_prop_permission_resolves_prop_id_from_query(db, hotel_staff_user, hotel_staff_role):
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read", "reservations.read", "payments.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)
    token = _seed_session(db, hotel_staff_user)

    dependency = require_prop_permission("payments.read")
    user = dependency(_make_request(token, query="prop_id=1"))
    assert user["username"] == "staff1"


async def test_require_prop_permission_missing_prop_id_denies(db, hotel_staff_user):
    token = _seed_session(db, hotel_staff_user)
    dependency = require_prop_permission("dashboard.read")
    with pytest.raises(HTTPException) as excinfo:
        dependency(_make_request(token))
    assert excinfo.value.status_code == 400


async def test_require_prop_permission_denies_hotel_outside_scope(db, hotel_staff_user, hotel_staff_role):
    """La dependency también valida el alcance por hotel (user_can_access_hotel)."""
    role_id = _create_hotel_role(
        db,
        prop_id=1,
        permissions=["dashboard.read"],
        based_on_role_id=hotel_staff_role["_id"],
    )
    _assign(db, hotel_staff_user["_id"], 1, role_id)
    # Restringir el alcance del usuario a solo el hotel 1.
    db.users.update_one(
        {"_id": hotel_staff_user["_id"]},
        {"$set": {"assigned_hotels": [1]}},
    )
    token = _seed_session(db, hotel_staff_user)

    dep_ok = require_prop_permission("dashboard.read", prop_id=1)
    assert dep_ok(_make_request(token))["username"] == "staff1"

    dep_out = require_prop_permission("dashboard.read", prop_id=2)
    with pytest.raises(HTTPException) as excinfo:
        dep_out(_make_request(token))
    assert excinfo.value.status_code == 403


# ── 5. Migración migrate_hotel_roles ──


async def test_migration_marks_roles_as_templates(db, hotel_staff_role, hotel_staff_user):
    result = migrate_hotel_roles(db)
    assert result["roles_marked_template"] == 1
    assert db.roles.find_one({"_id": hotel_staff_role["_id"]})["is_template"] is True


async def test_migration_creates_hotel_roles_and_assignments(db, hotel_staff_role, hotel_staff_user):
    result = migrate_hotel_roles(db)
    assert result["hotel_roles_created"] == 2  # prop 1 y prop 2
    assert result["assignments_created"] == 2

    for prop_id in (1, 2):
        hr = db.hotel_roles.find_one({"prop_id": prop_id, "name": "recepcionista"})
        assert hr is not None
        assert hr["permissions"] == hotel_staff_role["permissions"]
        assert hr["based_on_role_id"] == hotel_staff_role["_id"]
        assert hr["is_active"] is True
        assert hr["metadata"]["migration_id"] == "hotel_roles_fase1"

        assignment = db.role_assignments.find_one(
            {"user_id": hotel_staff_user["_id"], "prop_id": prop_id}
        )
        assert assignment is not None
        assert assignment["role_id"] == hr["_id"]


async def test_migration_is_idempotent(db, hotel_staff_role, hotel_staff_user):
    first = migrate_hotel_roles(db)
    assert first["hotel_roles_created"] == 2

    second = migrate_hotel_roles(db)
    assert second["hotel_roles_created"] == 0
    assert second["assignments_created"] == 0
    assert db.hotel_roles.count_documents({}) == 2
    assert db.role_assignments.count_documents({}) == 2


async def test_migration_dry_run_writes_nothing(db, hotel_staff_role, hotel_staff_user):
    result = migrate_hotel_roles(db, dry_run=True)
    assert result["hotel_roles_created"] == 2  # reporta lo que haría
    assert result["assignments_created"] == 2
    assert db.hotel_roles.count_documents({}) == 0
    assert db.role_assignments.count_documents({}) == 0
    assert db.roles.find_one({"_id": hotel_staff_role["_id"]}).get("is_template") is not True


async def test_migration_skips_users_without_assigned_hotels(db, hotel_staff_role):
    db.users.insert_one(
        {
            "username": "sin_hoteles",
            "email": "sin@hotel.local",
            "display_name": "Sin Hoteles",
            "password_hash": "x",
            "primary_role": "recepcionista",
            "primary_role_id": hotel_staff_role["_id"],
            "role_ids": [hotel_staff_role["_id"]],
            "assigned_hotels": [],
            "is_active": True,
            "created_at": _now(),
        }
    )
    result = migrate_hotel_roles(db)
    assert result["hotel_roles_created"] == 0
    assert result["assignments_created"] == 0


async def test_migration_respects_only_prop_id(db, hotel_staff_role, hotel_staff_user):
    result = migrate_hotel_roles(db, only_prop_id=1)
    assert result["hotel_roles_created"] == 1
    assert result["assignments_created"] == 1
    assert db.hotel_roles.count_documents({"prop_id": 1}) == 1
    assert db.hotel_roles.count_documents({"prop_id": 2}) == 0
