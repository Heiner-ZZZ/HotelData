"""HR module FK migration: employees.user_id and employee_shifts.employee_id.

Both fields must be stored/queried as BSON ObjectId FKs (to ``users._id``
and ``employees._id`` respectively), matching the rest of the codebase
(``employee_documents.employee_id``, ``reception_shifts.employee_id``,
``booking_orders.user_id``, …). The API boundary still accepts the hex
string (frontend contract unchanged); conversion happens inside the module.

The audit (Mongo 27018, 2026-08) found these two fields stored as hex
strings while every sibling FK used ObjectId — the same class of bug that
made ``booking_orders.user_id`` hide a client's bookings when a reader
mixed types. These tests pin the canonical behavior end-to-end.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId


def _seed_employee(db, *, user_id=None, full_name="Test Employee", prop_id=1, **extra):
    """Insert a minimal employee; returns its ``_id`` (ObjectId)."""
    doc: dict = {
        "full_name": full_name,
        "id_document": f"ID-{ObjectId()}",
        "prop_id": prop_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    if user_id is not None:
        doc["user_id"] = user_id
    doc.update(extra)
    return db.employees.insert_one(doc).inserted_id


async def _login_admin(client, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    assert resp.status_code == 200, resp.text


class TestEmployeeUserIdObjectIdFk:
    """employees.user_id must be a BSON ObjectId FK to users._id."""

    @pytest.mark.asyncio
    async def test_create_employee_with_user_id_stores_object_id(self, client, db, admin_user):
        """POST /api/hr with a hex user_id must persist it as ObjectId.

        Pins the ``create_employee`` write path: a regression that stores
        the raw hex string would pass service-level tests but break any
        reader that queries employees.user_id by ObjectId.
        """
        await _login_admin(client, admin_user)
        resp = await client.post(
            "/api/hr",
            json={
                "full_name": "Nuevo Empleado",
                "id_document": "EMP-0001",
                "email": "nuevo@test.com",
                "prop_id": 1,
                "user_id": admin_user["user_id"],  # hex string from the client
                "department": "housekeeping",
            },
        )
        assert resp.status_code == 201, resp.text
        doc = db.employees.find_one({"full_name": "Nuevo Empleado"})
        assert doc is not None
        assert isinstance(doc.get("user_id"), ObjectId), (
            f"create_employee must store user_id as ObjectId, got {type(doc.get('user_id')).__name__}"
        )
        assert doc["user_id"] == ObjectId(admin_user["user_id"])

    def test_ensure_user_account_writes_object_id(self, db):
        """Auto-created accounts must backlink employees.user_id as ObjectId."""
        from src.app.modules.hr.routes import _ensure_user_account

        emp_id = _seed_employee(db, full_name="Sin Cuenta", prop_id=5)
        emp = db.employees.find_one({"_id": emp_id})
        creds = _ensure_user_account(db, emp)
        assert creds["username"] != "", "account creation failed"
        doc = db.employees.find_one({"_id": emp_id})
        assert isinstance(doc.get("user_id"), ObjectId), (
            f"_ensure_user_account must store user_id as ObjectId, got {type(doc.get('user_id')).__name__}"
        )
        assert db.users.count_documents({"_id": doc["user_id"]}) == 1, (
            "the stored user_id must reference a real users._id"
        )

    @pytest.mark.asyncio
    async def test_my_portal_links_user_via_object_id(self, client, db, admin_user):
        """my-portal must find the employee by ObjectId user_id (not hex str)."""
        _seed_employee(db, user_id=ObjectId(admin_user["user_id"]), full_name="Soy Admin")

        await _login_admin(client, admin_user)
        resp = await client.get("/api/hr/my-portal")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["employee_id"] != "", (
            "my-portal must find the employee via ObjectId user_id; got the "
            f"directory fallback instead: {body}"
        )


class TestEmployeeShiftEmployeeIdObjectIdFk:
    """employee_shifts.employee_id must be a BSON ObjectId FK to employees._id."""

    @pytest.mark.asyncio
    async def test_create_shift_stores_employee_id_as_object_id(self, client, db, admin_user):
        """POST /api/hr/shifts must persist employee_id as ObjectId."""
        emp_id = _seed_employee(db, full_name="Turno Nuevo", prop_id=1)

        await _login_admin(client, admin_user)
        resp = await client.post(
            "/api/hr/shifts",
            json={
                "employee_id": str(emp_id),  # hex string from the client
                "date": "2026-08-20",
                "scheduled_start": "08:00",
                "scheduled_end": "16:00",
                "area": "Recepción",
            },
        )
        assert resp.status_code == 201, resp.text
        doc = db.employee_shifts.find_one({"date": "2026-08-20"})
        assert doc is not None
        assert isinstance(doc.get("employee_id"), ObjectId), (
            f"create_shift must store employee_id as ObjectId, got {type(doc.get('employee_id')).__name__}"
        )
        assert doc["employee_id"] == emp_id

    @pytest.mark.asyncio
    async def test_update_shift_stores_employee_id_as_object_id(self, client, db, admin_user):
        """PUT /api/hr/shifts/{id} must persist employee_id as ObjectId."""
        emp_a = _seed_employee(db, full_name="Turno A", prop_id=1)
        shift_id = db.employee_shifts.insert_one(
            {
                "employee_id": emp_a,
                "date": "2026-08-22",
                "scheduled_start": "08:00",
                "scheduled_end": "16:00",
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ).inserted_id
        emp_b = _seed_employee(db, full_name="Turno B", prop_id=1)

        await _login_admin(client, admin_user)
        resp = await client.put(
            f"/api/hr/shifts/{shift_id}",
            json={
                "employee_id": str(emp_b),  # hex string from the client
                "date": "2026-08-22",
                "scheduled_start": "09:00",
                "scheduled_end": "17:00",
            },
        )
        assert resp.status_code == 200, resp.text
        doc = db.employee_shifts.find_one({"_id": shift_id})
        assert isinstance(doc.get("employee_id"), ObjectId), (
            f"update_shift must store employee_id as ObjectId, got {type(doc.get('employee_id')).__name__}"
        )
        assert doc["employee_id"] == emp_b

    @pytest.mark.asyncio
    async def test_list_shifts_filters_by_object_id(self, client, db, admin_user):
        """GET /api/hr/shifts?employee_id=<hex> must match ObjectId rows."""
        emp_id = _seed_employee(db, full_name="Filtro Turnos", prop_id=1)
        db.employee_shifts.insert_one(
            {
                "employee_id": emp_id,  # canonical ObjectId
                "date": "2026-08-21",
                "scheduled_start": "08:00",
                "scheduled_end": "16:00",
                "status": "pending",
            }
        )

        await _login_admin(client, admin_user)
        resp = await client.get("/api/hr/shifts", params={"employee_id": str(emp_id)})
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        assert len(items) == 1, (
            f"list_shifts must find the shift via ObjectId filter, got {len(items)} item(s)"
        )

    def test_reception_expected_shift_type_reads_object_id_fks(self, db):
        """reception's HR-schedule lookup must work with ObjectId FKs.

        Pins the cross-module reader (reception/shifts.py): it resolves
        username → users._id → employees.user_id → employees._id →
        employee_shifts.employee_id. Any str() coercion on the way breaks
        the chain and silently falls back to the time-of-day heuristic.
        """
        from src.app.modules.reception.shifts import resolve_expected_shift_type

        user_id = db.users.insert_one(
            {
                "username": "portero_test",
                "email": "portero@test.com",
                "display_name": "Portero",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
        ).inserted_id
        emp_id = _seed_employee(db, user_id=user_id, full_name="Portero")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        db.employee_shifts.insert_one(
            {
                "employee_id": emp_id,
                "date": today,
                "scheduled_start": "08:00",
                "scheduled_end": "16:00",
                "status": "pending",
            }
        )

        at_dt = datetime.now(timezone.utc).replace(hour=10, minute=0)
        shift_type, source = resolve_expected_shift_type("portero_test", at_dt)
        assert source == "schedule", (
            "resolve_expected_shift_type must find the HR schedule via ObjectId FKs "
            f"(employees.user_id / employee_shifts.employee_id); got source={source!r} "
            "(time_of_day fallback)"
        )
        assert shift_type == "morning"
