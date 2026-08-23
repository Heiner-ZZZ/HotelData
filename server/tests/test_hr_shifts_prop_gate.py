"""Turnos HR: check-in/check-out con gate por-hotel (Fase 1 RBAC).

Migración E (2026-08): ``POST /api/hr/shifts/{shift_id}/check-in`` y
``.../check-out`` estaban gateadas con ``require_any_permission("hr.shifts.manage",
"hr.portal.read")`` GLOBAL — un usuario con cualquiera de los códigos en su
rol global podía registrar asistencia en turnos de CUALQUIER hotel sin que su
rol por-hotel (``role_assignments`` → ``hotel_roles``) ni el scope del hotel
se validaran.

Ahora exigen ``require_any_prop_permission("hr.shifts.manage", "hr.portal.read")``
+ pertenencia del turno al hotel pedido:

- ``prop_id`` obligatorio (query) → 400 sin contexto de hotel.
- Deny-by-default sin asignación para el hotel → 403 aunque el rol global
  conceda el código (el rol global NUNCA es fallback en contexto de hotel).
- El turno debe pertenecer al hotel pedido (via el empleado al que está
  asignado) → 404 cross-hotel (no se filtra la existencia).
- El gerente registra la asistencia (``hr.shifts.manage``) O el empleado
  auto-registra la suya desde Mi Portal (``hr.portal.read``).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from conftest import _seed_user


def _seed_employee(db, *, prop_id: int = 1, full_name: str = "Empleado Turno"):
    """Insert a minimal active employee; returns its ``_id`` (ObjectId)."""
    return db.employees.insert_one(
        {
            "full_name": full_name,
            "id_document": f"ID-{ObjectId()}",
            "prop_id": prop_id,
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id


def _seed_shift(db, *, employee_id: ObjectId, status: str = "pending"):
    """Insert a minimal employee shift; returns its ``_id`` (ObjectId)."""
    return db.employee_shifts.insert_one(
        {
            "employee_id": employee_id,
            "date": "2026-08-22",
            "status": status,
            "actual_check_in": None,
            "actual_check_out": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    ).inserted_id


def _seed_hotel_role(db, *, prop_id: int = 1, name: str = "rol_turnos", permissions: list[str]):
    """Insert an active hotel role; returns its id."""
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": name,
            "display_name": name,
            "permissions": permissions,
            "is_active": True,
        }
    ).inserted_id


def _assign(db, user_id: ObjectId, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {"user_id": user_id, "prop_id": prop_id, "role_id": role_id}
    )


def _seed_global_hr_user(db) -> dict[str, str]:
    """User whose GLOBAL role grants both codes (the pre-E hole).

    Assigned to hotel 1 for scope, but WITHOUT any ``role_assignments``
    row — the regression scenario: the global codes must NOT be enough.
    """
    db.roles.insert_one(
        {
            "role_name": "recepcionista_turnos",
            "display_name": "Recepcionista Turnos",
            "permissions": ["hr.shifts.manage", "hr.portal.read"],
            "is_system": False,
        }
    )
    creds = _seed_user(
        db,
        username="cajero_turnos",
        email="cajero_turnos@test.com",
        password="Pass123!",
        role="recepcionista_turnos",
    )
    db.users.update_one(
        {"_id": ObjectId(creds["user_id"])},
        {"$set": {"assigned_hotels": [1]}},
    )
    return creds


async def _login(client, creds: dict[str, str]) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text


class TestShiftCheckInRequiresHotelScope:
    """Check-in de turno: contexto de hotel + rol del hotel (any-of)."""

    @pytest.mark.asyncio
    async def test_checkin_400_without_prop_id(self, client, db, admin_user):
        """Sin contexto de hotel el dependency rechaza con 400 (deny-by-default)."""
        emp_id = _seed_employee(db, prop_id=1)
        shift_id = _seed_shift(db, employee_id=emp_id)
        await _login(client, admin_user)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-in",
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_checkin_403_global_role_without_hotel_assignment(self, client, db):
        """Los códigos GLOBALES ya no bastan: sin role_assignment → 403."""
        creds = _seed_global_hr_user(db)
        emp_id = _seed_employee(db, prop_id=1)
        shift_id = _seed_shift(db, employee_id=emp_id)
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-in",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_checkin_404_shift_of_another_hotel(self, client, db):
        """Cross-hotel: turno del hotel 2 NO es operable pasando prop_id=1."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(
            db, prop_id=1, name="gerente_hotel_1",
            permissions=["hr.shifts.manage"],
        )
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=2, full_name="Otro Hotel")
        shift_id = _seed_shift(db, employee_id=emp_id)
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-in",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_checkin_200_manager_hotel_role(self, client, db):
        """El gerente con rol del hotel (hr.shifts.manage) registra el check-in."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(
            db, prop_id=1, name="gerente_hotel_1",
            permissions=["hr.shifts.manage"],
        )
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1)
        shift_id = _seed_shift(db, employee_id=emp_id)
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-in",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id), "notes": "llegó a tiempo"},
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_checkin_auto_completes_stale_active_shift(self, client, db):
        """Regresión 2026-08: un turno activo de un día ANTERIOR (check-in sin
        check-out, ej. el caso de julio que bloqueaba el logout) se completa
        SOLO para ese empleado cuando registra un nuevo check-in."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(
            db, prop_id=1, name="gerente_hotel_1",
            permissions=["hr.shifts.manage"],
        )
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1)
        other_emp_id = _seed_employee(db, prop_id=1, full_name="Otro Empleado")
        yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        stale_id = _seed_shift(db, employee_id=emp_id, status="active")
        db.employee_shifts.update_one({"_id": stale_id}, {"$set": {"date": yesterday}})
        # El turno stale de OTRO empleado no se toca
        other_stale_id = _seed_shift(db, employee_id=other_emp_id, status="active")
        db.employee_shifts.update_one({"_id": other_stale_id}, {"$set": {"date": yesterday}})
        today_shift_id = _seed_shift(db, employee_id=emp_id, status="pending")
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{today_shift_id}/check-in",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id), "notes": "nuevo día"},
        )
        assert resp.status_code == 200, resp.text
        stale = db.employee_shifts.find_one({"_id": stale_id})
        assert stale["status"] == "completed"
        assert "autom" in (stale.get("check_out_notes") or "")
        # El del otro empleado sigue intacto (individual por empleado)
        assert db.employee_shifts.find_one({"_id": other_stale_id})["status"] == "active"

    @pytest.mark.asyncio
    async def test_checkin_200_self_service_portal_role(self, client, db):
        """Auto-servicio: el empleado con hr.portal.read registra su asistencia."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(
            db, prop_id=1, name="recepcionista_1",
            permissions=["hr.portal.read"],
        )
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1)
        shift_id = _seed_shift(db, employee_id=emp_id)
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-in",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "active"


class TestShiftCheckOutRequiresHotelScope:
    """Check-out de turno: mismo gate por-hotel, transición active → completed."""

    @pytest.mark.asyncio
    async def test_checkout_200_manager_hotel_role(self, client, db):
        """El gerente con rol del hotel cierra el turno activo."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(
            db, prop_id=1, name="gerente_hotel_1",
            permissions=["hr.shifts.manage"],
        )
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1)
        shift_id = _seed_shift(db, employee_id=emp_id, status="active")
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-out",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"
        shift = db.employee_shifts.find_one({"_id": ObjectId(shift_id)})
        assert shift["status"] == "completed"

    @pytest.mark.asyncio
    async def test_checkout_404_shift_of_another_hotel(self, client, db):
        """Cross-hotel en check-out: turno del hotel 2 → 404 con prop_id=1."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(
            db, prop_id=1, name="gerente_hotel_1",
            permissions=["hr.shifts.manage"],
        )
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=2)
        shift_id = _seed_shift(db, employee_id=emp_id, status="active")
        await _login(client, creds)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-out",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_checkout_200_super_admin_bypass(self, client, db, admin_user):
        """super_admin conserva el bypass con prop_id presente."""
        emp_id = _seed_employee(db, prop_id=1)
        shift_id = _seed_shift(db, employee_id=emp_id, status="active")
        await _login(client, admin_user)
        resp = await client.post(
            f"/api/hr/shifts/{shift_id}/check-out",
            params={"prop_id": 1},
            json={"employee_id": str(emp_id)},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"
