"""Authorization contract for late check-out beyond the courtesy window.

El gate ``check-ins.late_checkout_approve`` (canónico + role allow-list
manager-only) se fijó en la fase de definición; aquí se cubre además el 403 a
nivel de ruta: una recepcionista puede completar el check-out normal/cortesía
pero NO aprobar una salida fuera de la cortesía, mientras que el gerente sí.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from passlib.context import CryptContext

import src.app.modules.reservations.service._checkinout._checkout as checkout_module
from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS
from src.app.security.permissions import (
    LATE_CHECKOUT_APPROVAL_PERMISSION,
    require_manager_authorization,
    user_has_permission,
)
from tests.conftest import login


def _can_approve_late_checkout(db, user) -> bool:
    """Gate unificado: late check-out usa el permiso manager-only compartido."""
    return require_manager_authorization(db, user, permission_code=LATE_CHECKOUT_APPROVAL_PERMISSION)

APPROVAL_PERMISSION = "check-ins.late_checkout_approve"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def test_late_checkout_approval_permission_is_canonical_and_manager_only() -> None:
    """La capacidad de aprobar late check-out no es parte del CRUD de recepción."""
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert APPROVAL_PERMISSION in catalog_codes
    assert APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["super_admin"]
    assert APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["gerente_hotel"]
    assert APPROVAL_PERMISSION not in ROLE_PERMISSION_CODES["recepcionista"]
    # sync_role_permissions es un alias de ROLE_PERMISSION_CODES: paridad.
    assert APPROVAL_PERMISSION in ROLE_PERMISSIONS["gerente_hotel"]
    assert APPROVAL_PERMISSION not in ROLE_PERMISSIONS["recepcionista"]


def _seed_user(db, username: str, role_name: str, permissions: list[str]) -> None:
    role_id = db.roles.insert_one(
        {
            "role_name": role_name,
            "display_name": role_name,
            "permissions": permissions,
            "is_system": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id
    db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username,
            "password_hash": _pwd.hash("LatePass123!"),
            "primary_role": role_name,
            "role_ids": [role_id],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )


def test_receptionist_cannot_approve_late_checkout(db) -> None:
    """Recepción completa el check-out normal/cortesía pero no aprueba la extensión."""
    _seed_user(db, "recepcionista_late_test", "recepcionista", ["check-ins.manage", "check-outs.manage"])
    user = db.users.find_one({"username": "recepcionista_late_test"})
    assert _can_approve_late_checkout(db, user) is False


def test_manager_can_approve_late_checkout(db) -> None:
    """El gerente con el catálogo canónico aprueba la extensión de salida."""
    _seed_user(db, "gerente_late_test", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    user = db.users.find_one({"username": "gerente_late_test"})
    assert _can_approve_late_checkout(db, user) is True


def test_manager_without_permission_cannot_approve(db) -> None:
    """Defense in depth: el role allow-list solo no alcanza, se exige el permiso."""
    _seed_user(db, "gerente_late_missing", "gerente_hotel", ["check-ins.manage"])
    user = db.users.find_one({"username": "gerente_late_missing"})
    assert _can_approve_late_checkout(db, user) is False


def test_custom_allowed_roles_narrows_the_gate(db) -> None:
    """El parámetro ``allowed_roles`` permite acotar a roles distintos del default."""
    _seed_user(db, "gerente_late_custom", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    user = db.users.find_one({"username": "gerente_late_custom"})
    assert _can_approve_late_checkout(db, user) is True
    assert (
        require_manager_authorization(
            db,
            user,
            permission_code=LATE_CHECKOUT_APPROVAL_PERMISSION,
            allowed_roles={"maintenance"},
        )
        is False
    )


def test_inactive_manager_cannot_approve(db) -> None:
    """Un usuario inactivo nunca aprueba, aunque tenga el rol y el permiso."""
    _seed_user(db, "gerente_late_inactive", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    db.users.update_one({"username": "gerente_late_inactive"}, {"$set": {"is_active": False}})
    user = db.users.find_one({"username": "gerente_late_inactive"})
    assert _can_approve_late_checkout(db, user) is False


def test_inactive_super_admin_cannot_approve(db) -> None:
    """La inactividad ANTECEDE al bypass de super_admin: una cuenta super_admin
    deshabilitada no aprueba nada (el control activo sí hace bypass)."""
    _seed_user(db, "super_admin_late_inactive", "super_admin", ROLE_PERMISSION_CODES["super_admin"])
    active = db.users.find_one({"username": "super_admin_late_inactive"})
    assert _can_approve_late_checkout(db, active) is True

    db.users.update_one({"username": "super_admin_late_inactive"}, {"$set": {"is_active": False}})
    inactive = db.users.find_one({"username": "super_admin_late_inactive"})
    assert _can_approve_late_checkout(db, inactive) is False


def test_hotel_scoped_grant_does_not_leak_into_manager_gate(db) -> None:
    """Defense in depth (RBAC por hotel): el permiso otorgado SOLO vía
    ``hotel_roles`` (con ``prop_id``) no confiere autoridad gerencial global.
    El gate unificado resuelve los roles globales (sin prop_id) y lo deniega;
    la vía por-hotel sí honra el grant cuando se pasa ``prop_id``, y otro
    hotel sin asignación cae en deny-by-default."""
    # Rol global gerente_hotel SIN el permiso late (solo CRUD base).
    _seed_user(db, "gerente_late_hotel_scoped", "gerente_hotel", ["check-ins.manage"])
    user = db.users.find_one({"username": "gerente_late_hotel_scoped"})

    # RBAC por hotel: hotel_role con el permiso + asignación para el prop 991.
    hotel_role_id = db.hotel_roles.insert_one(
        {
            "name": "gerente_hotel",
            "display_name": "Gerente de hotel",
            "permissions": ROLE_PERMISSION_CODES["gerente_hotel"],
            "is_active": True,
            "is_system": True,
            "prop_id": 991,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {
            "user_id": user["_id"],
            "role_id": hotel_role_id,
            "prop_id": 991,
            "created_at": datetime.now(UTC),
        }
    )

    # Gate unificado (sin prop_id): resuelve roles globales → denegado. El
    # grant por-hotel no se filtra a la resolución global (defensa en
    # profundidad: un empleado con rol restringido por hotel no gana la
    # autoridad gerencial global del rol canónico).
    assert _can_approve_late_checkout(db, user) is False

    # Vía RBAC por hotel (con prop_id): el grant por-hotel SÍ se honra.
    assert (
        user_has_permission(db, user, LATE_CHECKOUT_APPROVAL_PERMISSION, prop_id=991) is True
    )
    # Otro hotel sin asignación → deny-by-default (sin fallback al rol global).
    assert (
        user_has_permission(db, user, LATE_CHECKOUT_APPROVAL_PERMISSION, prop_id=992) is False
    )


# ── Gate a nivel de ruta (POST /check-outs/{id}/complete) ─────────────────

_FIXED_CHECK_OUT = "2026-08-15"


def _freeze_clock(monkeypatch, *, hour: int, minute: int) -> None:
    frozen = datetime(2026, 8, 15, hour, minute, tzinfo=UTC)
    monkeypatch.setattr(checkout_module, "local_today", lambda: _FIXED_CHECK_OUT)
    monkeypatch.setattr(checkout_module, "local_now", lambda: frozen, raising=False)


def _seed_checked_in_booking(db, booking_id: str) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 994,
            "guest_name": "Late Route Guest",
            "guest_email": "late.route@test.com",
            "check_in_date": "2026-08-14",
            "check_out_date": _FIXED_CHECK_OUT,
            "total_price": 180.0,
            "currency": "USD",
            "total_nights": 2,
            "rooms": 1,
            "assigned_rooms": [],
            "status": "confirmed",
            "stay_status": "checked_in",
            "is_test": True,
        }
    )


@pytest.mark.asyncio
async def test_receptionist_cannot_submit_approved_late_checkout(
    client: AsyncClient, db, monkeypatch
) -> None:
    """La recepcionista no puede aprobar late check-out vía ruta: 403 antes de escribir."""
    _seed_user(db, "recepcionista_late_route", "recepcionista", ["check-ins.manage", "check-outs.manage"])
    _seed_checked_in_booking(db, "BK-LC-ROUTE-403")
    _freeze_clock(monkeypatch, hour=14, minute=0)
    assert await login(client, "recepcionista_late_route", "LatePass123!") == 200

    response = await client.post(
        "/api/management/check-outs/BK-LC-ROUTE-403/complete",
        json={
            "check_out_keys_returned": True,
            "late_checkout_mode": "late_approved",
            "late_checkout_approved": True,
            "late_checkout_reason": "Recepción intenta aprobar fuera de cortesía",
            "late_checkout_fee": 25,
        },
    )

    assert response.status_code == 403
    assert "late check-out" in response.json()["detail"].lower()
    booking = db.booking_orders.find_one({"booking_id": "BK-LC-ROUTE-403"})
    assert booking.get("stay_status") == "checked_in"
    assert booking.get("check_out_mode") is None


@pytest.mark.asyncio
async def test_manager_can_submit_approved_late_checkout(
    client: AsyncClient, db, monkeypatch
) -> None:
    """El gerente aprueba el late check-out vía ruta: 200 + modo registrado."""
    _seed_user(db, "gerente_late_route", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    _seed_checked_in_booking(db, "BK-LC-ROUTE-200")
    db.hotel_policies.insert_one(
        {
            "prop_id": 994,
            "room_type_id": "",
            "rate_plan_id": "",
            "season_id": "",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "late_checkout_enabled": True,
            "late_checkout_courtesy_minutes": 60,
            "late_checkout_default_fee": 25.0,
        }
    )
    db.reception_shifts.insert_one(
        {
            "prop_id": 994,
            "status": "open",
            "shift_type": "morning",
            "employee": "Gerente Route",
            "opened_by": "gerente_late_route",
            "start_time": datetime.now(UTC).isoformat(),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    _freeze_clock(monkeypatch, hour=14, minute=0)
    assert await login(client, "gerente_late_route", "LatePass123!") == 200

    response = await client.post(
        "/api/management/check-outs/BK-LC-ROUTE-200/complete",
        json={
            "check_out_keys_returned": True,
            "late_checkout_mode": "late_approved",
            "late_checkout_approved": True,
            "late_checkout_reason": "Gerente autoriza salida tardía",
            "late_checkout_fee": 25,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stay_status"] == "checked_out"
    assert body["check_out_mode"] == "late_approved"
    assert body["late_checkout_fee"] == 25.0
    booking = db.booking_orders.find_one({"booking_id": "BK-LC-ROUTE-200"})
    assert booking["check_out_mode"] == "late_approved"
    assert booking["late_checkout_approved_by"] == "gerente_late_route"
