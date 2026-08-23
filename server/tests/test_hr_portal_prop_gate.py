"""Portal HR: gate por-hotel (Fase 1 RBAC) + chequeo cross-hotel.

Fix B (2026-08): ``GET /api/hr/portal/{employee_id}`` y
``GET /api/hr/portal/{employee_id}/tasks`` estaban gateadas con
``require_permission("hr.portal.read")`` GLOBAL — un usuario con el código
en su rol global (ej. housekeeping) podía leer el portal de empleados de
CUALQUIER hotel sin que su rol por-hotel (``role_assignments`` →
``hotel_roles``) ni el scope del hotel se validaran.

Ahora exigen ``require_prop_permission("hr.portal.read")``:
- ``prop_id`` obligatorio (query) → 400 sin contexto de hotel.
- Deny-by-default sin asignación para el hotel → 403 aunque el rol global
  conceda el código (el rol global NUNCA es fallback en contexto de hotel).
- El empleado debe pertenecer al hotel pedido → 404 cross-hotel (no se filtra
  la existencia).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId
from conftest import _seed_user


def _seed_employee(db, *, prop_id: int = 1, full_name: str = "Empleado Portal", **extra):
    """Insert a minimal active employee; returns its ``_id`` (ObjectId)."""
    doc: dict = {
        "full_name": full_name,
        "id_document": f"ID-{ObjectId()}",
        "prop_id": prop_id,
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    doc.update(extra)
    return db.employees.insert_one(doc).inserted_id


def _seed_hotel_role(db, *, prop_id: int = 1, name: str = "recepcionista_portal"):
    """Insert an active hotel role granting ``hr.portal.read``; returns its id."""
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": name,
            "display_name": name,
            "permissions": ["hr.portal.read"],
            "is_active": True,
        }
    ).inserted_id


def _assign(db, user_id: ObjectId, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {"user_id": user_id, "prop_id": prop_id, "role_id": role_id}
    )


def _seed_global_hr_user(db) -> dict[str, str]:
    """User whose GLOBAL role grants ``hr.portal.read`` (the pre-B hole).

    Assigned to hotel 1 for scope, but WITHOUT any ``role_assignments``
    row — the regression scenario: the global code must NOT be enough.
    """
    db.roles.insert_one(
        {
            "role_name": "housekeeping",
            "display_name": "Housekeeping",
            "permissions": ["hr.portal.read"],
            "is_system": False,
        }
    )
    creds = _seed_user(
        db,
        username="portero_global",
        email="portero_global@test.com",
        password="Pass123!",
        role="housekeeping",
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


class TestPortalRequiresHotelScope:
    """The per-employee portal is a per-hotel feature: hotel context + hotel role."""

    @pytest.mark.asyncio
    async def test_portal_400_without_prop_id(self, client, db, admin_user):
        """Sin contexto de hotel el dependency rechaza con 400 (deny-by-default)."""
        emp_id = _seed_employee(db, prop_id=1)
        await _login(client, admin_user)
        resp = await client.get(f"/api/hr/portal/{emp_id}")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_portal_403_global_hr_role_without_hotel_assignment(self, client, db):
        """El código GLOBAL hr.portal.read ya no basta: sin role_assignment → 403."""
        creds = _seed_global_hr_user(db)
        emp_id = _seed_employee(db, prop_id=1)
        await _login(client, creds)
        resp = await client.get(f"/api/hr/portal/{emp_id}", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_portal_200_hotel_role_grants_access(self, client, db):
        """Con rol del hotel que otorga hr.portal.read → 200 y payload completo."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(db, prop_id=1)
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1, full_name="Con Acceso")
        await _login(client, creds)
        resp = await client.get(f"/api/hr/portal/{emp_id}", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["employee"]["id"] == str(emp_id)
        assert body["employee"]["full_name"] == "Con Acceso"

    @pytest.mark.asyncio
    async def test_portal_200_serializes_active_shift_object_ids(self, client, db):
        """Regresión 2026-08: un shift activo con FK ObjectId (employee_id) en
        ``current_shift`` crasheaba la serialización (PydanticSerializationError,
        HTTP 500) porque el dict permisivo no convierte ObjectIds. El portal
        debe devolver 200 con el shift en forma JSON-safe."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(db, prop_id=1)
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1, full_name="Con Turno")
        db.employee_shifts.insert_one({
            "employee_id": emp_id,  # FK ObjectId — el leak
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "status": "active",
            "scheduled_start": "09:00",
            "scheduled_end": "17:00",
            "area": "Recepción",
            "created_at": datetime.now(UTC),
        })
        await _login(client, creds)
        resp = await client.get(f"/api/hr/portal/{emp_id}", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["current_shift"]["employee_id"] == str(emp_id)
        assert body["current_shift"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_portal_404_employee_of_another_hotel(self, client, db):
        """Cross-hotel: empleado del hotel 2 NO es legible pasando prop_id=1."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(db, prop_id=1)
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=2, full_name="Otro Hotel")
        await _login(client, creds)
        resp = await client.get(f"/api/hr/portal/{emp_id}", params={"prop_id": 1})
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_portal_tasks_requires_prop_gate(self, client, db):
        """El endpoint de tareas sigue el mismo gate: sin asignación → 403."""
        creds = _seed_global_hr_user(db)
        emp_id = _seed_employee(db, prop_id=1)
        await _login(client, creds)
        resp = await client.get(f"/api/hr/portal/{emp_id}/tasks", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_portal_tasks_200_with_hotel_role(self, client, db):
        """Tareas con rol del hotel → 200 (payload con listas, posiblemente vacías)."""
        creds = _seed_global_hr_user(db)
        role_id = _seed_hotel_role(db, prop_id=1)
        _assign(db, ObjectId(creds["user_id"]), 1, role_id)
        emp_id = _seed_employee(db, prop_id=1)
        await _login(client, creds)
        resp = await client.get(f"/api/hr/portal/{emp_id}/tasks", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body.get("assigned_tasks"), list)
        assert isinstance(body.get("dirty_rooms"), list)
