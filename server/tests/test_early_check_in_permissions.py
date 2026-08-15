"""Authorization contract for early check-in outside the courtesy window.

El gate ``check-ins.early_approve`` (canónico + role allow-list manager-only)
se fija aquí al mismo nivel que sus hermanos (late check-out y write-off):
unit del gate unificado ``require_manager_authorization`` con los casos límite
compartidos — inactivo → deny aunque tenga rol y permiso, inactivo super_admin
→ deny (la inactividad antecede al bypass ``*.*``) y RBAC por hotel
(hotel-scoped grant honrado con ``prop_id``, deny-by-default sin asignación,
sin fuga a la resolución global).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from passlib.context import CryptContext

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS
from src.app.security.permissions import (
    EARLY_CHECK_IN_APPROVAL_PERMISSION,
    require_manager_authorization,
    user_has_permission,
)
from tests.conftest import login

APPROVAL_PERMISSION = "check-ins.early_approve"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def test_early_approval_permission_is_canonical_and_manager_only() -> None:
    """The sensitive approval capability is not part of front-desk CRUD."""
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert APPROVAL_PERMISSION in catalog_codes
    assert APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["super_admin"]
    assert APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["gerente_hotel"]
    assert APPROVAL_PERMISSION not in ROLE_PERMISSION_CODES["recepcionista"]
    assert APPROVAL_PERMISSION in ROLE_PERMISSIONS["gerente_hotel"]
    assert APPROVAL_PERMISSION not in ROLE_PERMISSIONS["recepcionista"]


def _can_approve_early_check_in(db, user) -> bool:
    """Gate unificado: early check-in usa el permiso manager-only compartido."""
    return require_manager_authorization(db, user, permission_code=EARLY_CHECK_IN_APPROVAL_PERMISSION)


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
            "password_hash": _pwd.hash("EarlyPass123!"),
            "primary_role": role_name,
            "role_ids": [role_id],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )


def test_receptionist_cannot_approve_early_check_in(db) -> None:
    """Recepción completa el check-in normal/cortesía pero no aprueba la anticipación."""
    _seed_user(db, "recepcionista_early_unit", "recepcionista", ["check-ins.manage"])
    user = db.users.find_one({"username": "recepcionista_early_unit"})
    assert user_has_permission(db, user, APPROVAL_PERMISSION) is False
    assert _can_approve_early_check_in(db, user) is False


def test_manager_can_approve_early_check_in(db) -> None:
    """El gerente con el catálogo canónico aprueba la llegada anticipada."""
    _seed_user(db, "gerente_early_unit", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    user = db.users.find_one({"username": "gerente_early_unit"})
    assert user_has_permission(db, user, APPROVAL_PERMISSION) is True
    assert _can_approve_early_check_in(db, user) is True


def test_manager_without_permission_cannot_approve(db) -> None:
    """Defense in depth: el role allow-list solo no alcanza, se exige el permiso."""
    _seed_user(db, "gerente_early_missing", "gerente_hotel", ["check-ins.manage"])
    user = db.users.find_one({"username": "gerente_early_missing"})
    assert user_has_permission(db, user, APPROVAL_PERMISSION) is False
    assert _can_approve_early_check_in(db, user) is False


def test_inactive_manager_cannot_approve(db) -> None:
    """Un usuario inactivo nunca aprueba, aunque tenga el rol y el permiso."""
    _seed_user(db, "gerente_early_inactive", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    db.users.update_one({"username": "gerente_early_inactive"}, {"$set": {"is_active": False}})
    user = db.users.find_one({"username": "gerente_early_inactive"})
    assert user_has_permission(db, user, APPROVAL_PERMISSION) is False
    assert _can_approve_early_check_in(db, user) is False


def test_inactive_super_admin_cannot_approve(db) -> None:
    """La inactividad ANTECEDE al bypass de super_admin: una cuenta super_admin
    deshabilitada no aprueba nada (el control activo sí hace bypass)."""
    _seed_user(db, "super_admin_early_inactive", "super_admin", ROLE_PERMISSION_CODES["super_admin"])
    active = db.users.find_one({"username": "super_admin_early_inactive"})
    assert _can_approve_early_check_in(db, active) is True

    db.users.update_one({"username": "super_admin_early_inactive"}, {"$set": {"is_active": False}})
    inactive = db.users.find_one({"username": "super_admin_early_inactive"})
    assert user_has_permission(db, inactive, APPROVAL_PERMISSION) is False
    assert _can_approve_early_check_in(db, inactive) is False


def test_hotel_scoped_grant_does_not_leak_into_manager_gate(db) -> None:
    """Defense in depth (RBAC por hotel): el permiso otorgado SOLO vía
    ``hotel_roles`` (con ``prop_id``) no confiere autoridad gerencial global;
    la vía por-hotel sí honra el grant cuando se pasa ``prop_id``, y otro
    hotel sin asignación cae en deny-by-default (mismo contrato que los
    gates hermanos)."""
    _seed_user(db, "gerente_early_hotel_scoped", "gerente_hotel", ["check-ins.manage"])
    user = db.users.find_one({"username": "gerente_early_hotel_scoped"})

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

    # Gate unificado (sin prop_id): resuelve roles globales → denegado.
    assert _can_approve_early_check_in(db, user) is False

    # Vía RBAC por hotel (con prop_id): el grant por-hotel SÍ se honra.
    assert user_has_permission(db, user, APPROVAL_PERMISSION, prop_id=991) is True
    # Otro hotel sin asignación → deny-by-default (sin fallback al rol global).
    assert user_has_permission(db, user, APPROVAL_PERMISSION, prop_id=992) is False


def _seed_receptionist(db) -> dict[str, str]:
    role_id = db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["check-ins.manage"],
            "is_system": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id
    password = "ReceptionPass123!"
    db.users.insert_one(
        {
            "username": "recepcionista_early_test",
            "email": "recepcionista_early_test@hotel.local",
            "display_name": "Recepcionista Early Test",
            "password_hash": _pwd.hash(password),
            "primary_role": "recepcionista",
            "role_ids": [role_id],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )
    return {"username": "recepcionista_early_test", "password": password}


@pytest.mark.asyncio
async def test_receptionist_cannot_submit_approved_early_check_in(
    client: AsyncClient,
    db,
) -> None:
    """A receptionist keeps normal/courtesy check-in but cannot approve early."""
    credentials = _seed_receptionist(db)
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-EARLY-AUTH-ROUTE",
            "prop_id": 991,
            "guest_name": "Early Authorization Guest",
            "status": "confirmed",
            "check_in_date": "2099-08-14",
            "check_out_date": "2099-08-16",
            "assigned_rooms": [],
            "is_test": True,
        }
    )
    assert await login(client, credentials["username"], credentials["password"]) == 200

    response = await client.post(
        "/api/management/check-ins/BK-EARLY-AUTH-ROUTE/complete",
        json={
            "early_check_in_mode": "early_approved",
            "early_check_in_approved": True,
            "early_check_in_reason": "Recepción intenta aprobar fuera de cortesía",
            "early_check_in_fee": 25,
        },
    )

    assert response.status_code == 403
    assert "early" in response.json()["detail"].lower()
    booking = db.booking_orders.find_one({"booking_id": "BK-EARLY-AUTH-ROUTE"})
    assert booking.get("check_in_observations") is None
    assert booking.get("stay_status") is None
