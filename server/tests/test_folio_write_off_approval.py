"""Authorization contract for closing a folio with balance (write-off).

Cerrar un folio CON SALDO mediante una excepción (``approved_write_off``,
``complimentary_stay`` o ``approved_external_settlement``) es un ajuste
financiero: la recepción tiene ``billing.manage`` pero NO puede condonar
saldos sin aprobación de supervisor. Reutiliza el gate unificado
``require_manager_authorization`` vía ``require_supervisor_authorization`` con
la allow-list ``SUPERVISOR_AUTHORIZATION_ROLES`` (gerente_hotel,
admin_sistema, super_admin).

Cubre el patrón pedido de punta a punta: catálogo canónico, unit del gate
(defensa en profundidad) y 403/200 a nivel de ruta.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from passlib.context import CryptContext

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS
from src.app.security.permissions import (
    FOLIO_ADJUST_APPROVAL_PERMISSION,
    require_supervisor_authorization,
    user_has_permission,
)
from tests.conftest import login

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _can_approve_write_off(db, user) -> bool:
    """Gate unificado de supervisor: folio con saldo / write-off."""
    return require_supervisor_authorization(
        db, user, permission_code=FOLIO_ADJUST_APPROVAL_PERMISSION
    )


def test_write_off_approval_permission_is_canonical_and_supervisor_only() -> None:
    """La capacidad de aprobar un write-off no es parte del CRUD de recepción."""
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert FOLIO_ADJUST_APPROVAL_PERMISSION in catalog_codes
    assert FOLIO_ADJUST_APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["super_admin"]
    assert FOLIO_ADJUST_APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["gerente_hotel"]
    assert FOLIO_ADJUST_APPROVAL_PERMISSION in ROLE_PERMISSION_CODES["admin_sistema"]
    assert FOLIO_ADJUST_APPROVAL_PERMISSION not in ROLE_PERMISSION_CODES["recepcionista"]
    # sync_role_permissions es un alias de ROLE_PERMISSION_CODES: paridad.
    assert FOLIO_ADJUST_APPROVAL_PERMISSION in ROLE_PERMISSIONS["gerente_hotel"]
    assert FOLIO_ADJUST_APPROVAL_PERMISSION not in ROLE_PERMISSIONS["recepcionista"]


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
            "password_hash": _pwd.hash("WriteOff123!"),
            "primary_role": role_name,
            "role_ids": [role_id],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )


def test_receptionist_cannot_approve_write_off(db) -> None:
    """Recepción cierra folios normales/cortesía pero NO condona saldos."""
    _seed_user(db, "recepcionista_writeoff", "recepcionista", ["billing.manage"])
    user = db.users.find_one({"username": "recepcionista_writeoff"})
    assert _can_approve_write_off(db, user) is False


def test_manager_can_approve_write_off(db) -> None:
    """El gerente con el catálogo canónico aprueba el cierre con saldo."""
    _seed_user(db, "gerente_writeoff", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    user = db.users.find_one({"username": "gerente_writeoff"})
    assert _can_approve_write_off(db, user) is True


def test_admin_sistema_can_approve_write_off(db) -> None:
    """admin_sistema está en la allow-list de supervisor (nivel sistema)."""
    _seed_user(db, "admin_sistema_writeoff", "admin_sistema", ROLE_PERMISSION_CODES["admin_sistema"])
    user = db.users.find_one({"username": "admin_sistema_writeoff"})
    assert _can_approve_write_off(db, user) is True


def test_manager_without_permission_cannot_approve(db) -> None:
    """Defense in depth: la allow-list sola no alcanza, se exige el permiso."""
    _seed_user(db, "gerente_writeoff_missing", "gerente_hotel", ["billing.read"])
    user = db.users.find_one({"username": "gerente_writeoff_missing"})
    assert _can_approve_write_off(db, user) is False


def test_custom_allowed_roles_narrows_the_supervisor_gate(db) -> None:
    """``allowed_roles`` custom acota el gate por encima del default supervisor."""
    _seed_user(db, "gerente_writeoff_custom", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    user = db.users.find_one({"username": "gerente_writeoff_custom"})
    assert _can_approve_write_off(db, user) is True
    assert (
        require_supervisor_authorization(
            db,
            user,
            permission_code=FOLIO_ADJUST_APPROVAL_PERMISSION,
            allowed_roles={"recepcionista"},
        )
        is False
    )


def test_inactive_manager_cannot_approve_write_off(db) -> None:
    """Un usuario inactivo nunca aprueba, aunque tenga rol y permiso."""
    _seed_user(db, "gerente_writeoff_inactive", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    db.users.update_one({"username": "gerente_writeoff_inactive"}, {"$set": {"is_active": False}})
    user = db.users.find_one({"username": "gerente_writeoff_inactive"})
    assert _can_approve_write_off(db, user) is False


def test_inactive_super_admin_cannot_approve_write_off(db) -> None:
    """La inactividad ANTECEDE al bypass de super_admin (mismo contrato)."""
    _seed_user(db, "super_admin_writeoff_inactive", "super_admin", [])
    active = db.users.find_one({"username": "super_admin_writeoff_inactive"})
    assert _can_approve_write_off(db, active) is True

    db.users.update_one({"username": "super_admin_writeoff_inactive"}, {"$set": {"is_active": False}})
    inactive = db.users.find_one({"username": "super_admin_writeoff_inactive"})
    assert _can_approve_write_off(db, inactive) is False


def test_hotel_scoped_grant_does_not_leak_into_supervisor_gate(db) -> None:
    """Defense in depth (RBAC por hotel): el permiso otorgado SOLO vía
    ``hotel_roles`` (con ``prop_id``) no confiere autoridad de supervisor
    global; la vía por-hotel sí se honra con ``prop_id``, y otro hotel sin
    asignación cae en deny-by-default."""
    _seed_user(db, "gerente_writeoff_scoped", "gerente_hotel", ["billing.read"])
    user = db.users.find_one({"username": "gerente_writeoff_scoped"})

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

    assert _can_approve_write_off(db, user) is False
    assert (
        user_has_permission(db, user, FOLIO_ADJUST_APPROVAL_PERMISSION, prop_id=991) is True
    )
    assert (
        user_has_permission(db, user, FOLIO_ADJUST_APPROVAL_PERMISSION, prop_id=992) is False
    )


# ── Gate a nivel de ruta (POST /api/billing/folios/{id}/close) ──────────────


def _seed_booking_with_folio(db, booking_id: str, *, total_due: float) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 994,
            "guest_name": "Write Off Guest",
            "total_price": 120.0,
            "total_nights": 2,
            "status": "confirmed",
            "stay_status": "checked_in",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-12",
            "created_at": datetime.now(UTC),
        }
    )
    db.guest_folios.insert_one(
        {
            "folio_number": f"FL-WO-{booking_id}",
            "booking_id": booking_id,
            "prop_id": 994,
            "status": "open",
            "total_room": total_due,
            "total_charges": total_due,
            "total_due": total_due,
            "postings": [],
            "posting_count": 0,
            "created_at": datetime.now(UTC),
            "closed_at": None,
            "closed_by": None,
            "invoice_id": None,
        }
    )


@pytest.mark.asyncio
async def test_receptionist_cannot_close_folio_with_write_off(
    client: AsyncClient, db
) -> None:
    """La recepcionista tiene billing.manage pero no puede condonar: 403 antes
    de tocar el folio (queda abierto e intacto)."""
    _seed_user(db, "recepcionista_wo_route", "recepcionista", ["billing.manage"])
    _seed_booking_with_folio(db, "BK-WO-ROUTE-403", total_due=120.0)
    assert await login(client, "recepcionista_wo_route", "WriteOff123!") == 200

    response = await client.post(
        "/api/billing/folios/BK-WO-ROUTE-403/close",
        json={"close_reason": "approved_write_off: Recepción intenta condonar"},
    )

    assert response.status_code == 403
    assert "billing.write_off.approve" in response.json()["detail"]
    folio = db.guest_folios.find_one({"booking_id": "BK-WO-ROUTE-403"})
    assert folio["status"] == "open"
    assert folio.get("close_reason") is None


@pytest.mark.asyncio
async def test_manager_can_close_folio_with_write_off(
    client: AsyncClient, db
) -> None:
    """El gerente (catálogo canónico) cierra con write-off: 200 + folio cerrado
    con la razón documentada."""
    _seed_user(db, "gerente_wo_route", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    _seed_booking_with_folio(db, "BK-WO-ROUTE-200", total_due=120.0)
    assert await login(client, "gerente_wo_route", "WriteOff123!") == 200

    response = await client.post(
        "/api/billing/folios/BK-WO-ROUTE-200/close",
        json={"close_reason": "approved_write_off: Huésped con problema de pago"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
    folio = db.guest_folios.find_one({"booking_id": "BK-WO-ROUTE-200"})
    assert folio["status"] == "closed"
    assert folio["close_reason"].startswith("approved_write_off:")


@pytest.mark.asyncio
async def test_manager_can_settle_folio_with_write_off(
    client: AsyncClient, db
) -> None:
    """El botón de write-off del detalle de folio acepta al gerente por su permiso de aprobación."""
    _seed_user(db, "gerente_settle_route", "gerente_hotel", ROLE_PERMISSION_CODES["gerente_hotel"])
    _seed_booking_with_folio(db, "BK-WO-SETTLE-200", total_due=120.0)
    assert await login(client, "gerente_settle_route", "WriteOff123!") == 200

    response = await client.post(
        "/api/billing/folios/BK-WO-SETTLE-200/settle",
        json={
            "settlement_type": "write_off",
            "idempotency_key": "SETTLE-WO-200",
            "reason": "Huésped con problema de pago",
            "approval_reference": "AUTH-SETTLE-200",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "written_off"
    folio = db.guest_folios.find_one({"booking_id": "BK-WO-SETTLE-200"})
    assert folio["status"] == "written_off"
    assert folio["total_due"] == 0.0


@pytest.mark.asyncio
async def test_receptionist_cannot_settle_folio_with_write_off(
    client: AsyncClient, db
) -> None:
    """billing.manage no reemplaza la aprobación supervisora del write-off."""
    _seed_user(db, "recepcionista_settle_route", "recepcionista", ["billing.manage"])
    _seed_booking_with_folio(db, "BK-WO-SETTLE-403", total_due=120.0)
    assert await login(client, "recepcionista_settle_route", "WriteOff123!") == 200

    response = await client.post(
        "/api/billing/folios/BK-WO-SETTLE-403/settle",
        json={
            "settlement_type": "write_off",
            "idempotency_key": "SETTLE-WO-403",
            "reason": "Intento no autorizado",
            "approval_reference": "AUTH-SETTLE-403",
        },
    )

    assert response.status_code == 403
    assert "billing.write_off.approve" in response.json()["detail"]
    folio = db.guest_folios.find_one({"booking_id": "BK-WO-SETTLE-403"})
    assert folio["status"] == "open"
    assert folio["total_due"] == 120.0


@pytest.mark.asyncio
async def test_admin_sistema_can_close_folio_with_write_off(
    client: AsyncClient, db
) -> None:
    """admin_sistema (allow-list supervisor) aprueba el cierre con saldo."""
    _seed_user(db, "admin_wo_route", "admin_sistema", ROLE_PERMISSION_CODES["admin_sistema"])
    _seed_booking_with_folio(db, "BK-WO-ROUTE-ADMIN", total_due=75.0)
    assert await login(client, "admin_wo_route", "WriteOff123!") == 200

    response = await client.post(
        "/api/billing/folios/BK-WO-ROUTE-ADMIN/close",
        json={"close_reason": "approved_external_settlement: convenio externo"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
    folio = db.guest_folios.find_one({"booking_id": "BK-WO-ROUTE-ADMIN"})
    assert folio["close_reason"].startswith("approved_external_settlement:")


@pytest.mark.asyncio
async def test_close_folio_with_balance_without_exception_conflicts_with_action(
    client: AsyncClient, db
) -> None:
    """Cerrar un folio con saldo sin close_reason de excepción → 409 con
    instrucción de QUÉ hacer (registrar el pago o pedir autorización de
    supervisor), no solo el estado."""
    _seed_user(db, "recepcionista_wo_409", "recepcionista", ["billing.manage"])
    _seed_booking_with_folio(db, "BK-WO-ROUTE-409", total_due=80.0)
    assert await login(client, "recepcionista_wo_409", "WriteOff123!") == 200

    response = await client.post("/api/billing/folios/BK-WO-ROUTE-409/close", json={})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "Registrá el pago del saldo" in detail
    assert "pedile a un supervisor" in detail
    folio = db.guest_folios.find_one({"booking_id": "BK-WO-ROUTE-409"})
    assert folio["status"] == "open"


@pytest.mark.asyncio
async def test_receptionist_normal_close_still_works(
    client: AsyncClient, db
) -> None:
    """La recepción conserva el cierre NORMAL (sin excepción de saldo): el
    gate supervisor solo aplica a los ajustes financieros."""
    _seed_user(db, "recepcionista_wo_normal", "recepcionista", ["billing.manage"])
    _seed_booking_with_folio(db, "BK-WO-ROUTE-NORMAL", total_due=0.0)
    assert await login(client, "recepcionista_wo_normal", "WriteOff123!") == 200

    response = await client.post(
        "/api/billing/folios/BK-WO-ROUTE-NORMAL/close",
        json={},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
