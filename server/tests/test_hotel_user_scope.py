"""Alcance por hotel en los puntos de creación de usuarios de hotel.

Extiende el fix del onboarding (test_register_property.py) al resto de puntos
donde se crean usuarios con roles de hotel:

1. ``hr.routes._ensure_user_account`` — cuenta auto-generada para empleados.
   - Con ``prop_id`` → ``assigned_hotels == [prop_id]``.
   - Sin ``prop_id`` (``EmployeeCreate.prop_id`` es opcional) → NO debe crear
     una cuenta sin restricción (deny-by-default). Como ``hotel_filter``
     filtra solo por ``assigned_hotels`` (vacío = sin restricción), una cuenta
     con ``[]`` vería TODOS los hoteles del sistema.

2. ``admin.service.ownership.create_ownership_user`` — el super admin crea
   usuarios de hotel.
   - Sin ``assigned_hotels`` → rechazar (antes escribía ``[]`` = sin
     restricción = acceso a todo el sistema).
   - Con hoteles → el usuario queda acotado a esos ``prop_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.admin.service.ownership import (
    create_ownership_user,
    update_assigned_hotels,
)
from src.app.modules.hr.routes import _ensure_user_account
from src.app.modules.hr.service.collections import EMPLOYEES_COLLECTION
from src.app.security.hotel_filter import hotel_filter_from_user, user_can_access_hotel


def _seed_employee(db, *, prop_id: int | None, email: str):
    emp_id = db[EMPLOYEES_COLLECTION].insert_one(
        {
            "full_name": "Empleado Test",
            "email": email,
            "department": "recepción",
            "department_name": "Recepción",
            "prop_id": prop_id,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ).inserted_id
    return db[EMPLOYEES_COLLECTION].find_one({"_id": emp_id})


# ── HR: cuenta auto-generada para empleados ────────────────────────────


@pytest.mark.asyncio
async def test_hr_auto_account_scoped_to_employee_hotel(db):
    """Empleado con prop_id → la cuenta auto-generada queda acotada a su hotel."""
    emp = _seed_employee(db, prop_id=7, email="emp7@hotel.local")

    creds = _ensure_user_account(db, emp)

    assert creds["username"], "debe crear la cuenta del empleado"
    user = db.users.find_one({"username": creds["username"]})
    assert user is not None
    assert user["assigned_hotels"] == [7]
    assert hotel_filter_from_user(user) == {"prop_id": {"$in": [7]}}
    assert user_can_access_hotel(user, 7) is True
    assert user_can_access_hotel(user, 8) is False


@pytest.mark.asyncio
async def test_hr_auto_account_no_unlimited_scope_without_prop_id(db):
    """RED: empleado sin prop_id → NO crear cuenta con alcance ilimitado.

    Hoy ``_ensure_user_account`` escribe ``assigned_hotels: []`` cuando el
    empleado no tiene ``prop_id``; como ``hotel_filter`` trata vacío como
    "sin restricción", esa cuenta vería todos los hoteles. Deny-by-default:
    sin hotel, sin cuenta.
    """
    emp = _seed_employee(db, prop_id=None, email="emp_sin_hotel@hotel.local")

    creds = _ensure_user_account(db, emp)

    assert creds["username"] == ""
    assert creds["password"] is None
    assert db.users.count_documents({"email": "emp_sin_hotel@hotel.local"}) == 0


# ── Ownership: super admin crea usuarios de hotel ─────────────────────


def test_create_ownership_user_requires_hotels(db):
    """RED: crear usuario de hotel sin assigned_hotels debe ser rechazado.

    Hoy ``create_ownership_user`` escribe ``assigned_hotels or []`` — un
    hotel_partner sin hoteles queda con alcance ilimitado (ve todo el
    sistema). El endpoint de admin lo deja pasar como 200.
    """
    result = create_ownership_user(
        "owner_sin_hoteles",
        "owner_sin_hoteles@hotel.local",
        "Pass123!",
        "hotel_partner",
    )

    assert result["ok"] is False
    assert db.users.count_documents({"username": "owner_sin_hoteles"}) == 0


@pytest.mark.asyncio
async def test_ownership_users_create_api_400_without_hotels(client, db, admin_user):
    """RED (route-level): POST /api/admin/ownership/users sin assigned_hotels
    debe devolver 400 — el route pasa ``body.get("assigned_hotels", [])`` y el
    service lo rechaza (antes creaba el usuario con alcance ilimitado)."""
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "admin_test", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/api/admin/ownership/users",
        json={
            "username": "owner_api",
            "email": "owner_api@hotel.local",
            "password": "Pass123!",
            "primary_role": "hotel_partner",
            "assigned_hotels": [],
        },
    )
    assert resp.status_code == 400, resp.text
    assert db.users.count_documents({"username": "owner_api"}) == 0


def test_update_assigned_hotels_rejects_empty_list(db):
    """RED: vaciar assigned_hotels vía update NO debe dar alcance ilimitado.

    hotel_filter trata la lista vacía como "sin restricción", así que un
    admin que "quita todos los hoteles" creyendo revocar acceso, en realidad
    dejaría al usuario viendo TODO el sistema.
    """
    result = create_ownership_user(
        "owner_update",
        "owner_update@hotel.local",
        "Pass123!",
        "hotel_partner",
        assigned_hotels=[3],
    )
    assert result["ok"] is True
    user_id = result["user"]["user_id"]

    resp = update_assigned_hotels(user_id, [])

    assert resp["ok"] is False
    user = db.users.find_one({"username": "owner_update"})
    assert user["assigned_hotels"] == [3]  # sin cambios


@pytest.mark.asyncio
async def test_create_ownership_user_scoped_to_hotels(db):
    """Con assigned_hotels → el usuario queda acotado a esos prop_id."""
    result = create_ownership_user(
        "owner_hotel1",
        "owner_hotel1@hotel.local",
        "Pass123!",
        "hotel_partner",
        assigned_hotels=[3],
    )

    assert result["ok"] is True
    user = db.users.find_one({"username": "owner_hotel1"})
    assert user is not None
    assert user["assigned_hotels"] == [3]
    assert hotel_filter_from_user(user) == {"prop_id": {"$in": [3]}}
    assert user_can_access_hotel(user, 3) is True
    assert user_can_access_hotel(user, 4) is False
