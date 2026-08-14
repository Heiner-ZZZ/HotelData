"""GET /api/hr (employee list) must expose account + role-assignment status.

The HR directory page shows each employee's user-account link: whether the
employee has a user account (``employees.user_id`` that still resolves to a
``users._id``) and whether that account has a per-hotel role assigned
(``role_assignments`` row for that user in the employee's ``prop_id``). This
lets the UI render an indicator with a link to Team Permissions.

Regression: the list previously returned the raw ``user_id`` only — the
frontend could not tell "orphan" (user deleted) from "no account", and had
no way to know if the account was already assigned a hotel role.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from tests.conftest import login

pytestmark = pytest.mark.asyncio


def _seed_employee(db, *, full_name: str, user_id=None, prop_id: int = 1) -> ObjectId:
    doc: dict = {
        "full_name": full_name,
        "id_document": f"ID-{ObjectId()}",
        "email": f"{full_name.replace(' ', '.')}@test.com",
        "prop_id": prop_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    if user_id is not None:
        doc["user_id"] = user_id
    return db.employees.insert_one(doc).inserted_id


def _seed_user(db, *, username: str) -> ObjectId:
    return db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@test.com",
            "display_name": username.title(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id


async def test_list_marks_employee_with_live_account_and_role(client, db, admin_user):
    """Employee whose user exists AND has a hotel role → both flags True."""
    user_id = _seed_user(db, username="carlos.cta")
    _seed_employee(db, full_name="Carlos Con Cuenta", user_id=user_id)
    role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["dashboard.read"],
            "is_active": True,
            "is_system": False,
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": 1,
            "role_id": role_id,
            "assigned_by": "test",
            "assigned_at": datetime.now(timezone.utc),
        }
    )

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.get("/api/hr", params={"prop_id": 1})
    assert resp.status_code == 200, resp.text
    items = {i["full_name"]: i for i in resp.json()["items"]}

    emp = items.get("Carlos Con Cuenta")
    assert emp is not None
    assert emp["has_user_account"] is True
    assert emp["role_assigned"] is True


async def test_list_marks_employee_with_live_account_but_no_role(client, db, admin_user):
    """User exists but no hotel role assignment → account True, role False."""
    user_id = _seed_user(db, username="maria.sr")
    _seed_employee(db, full_name="María Sin Rol", user_id=user_id)

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.get("/api/hr", params={"prop_id": 1})
    items = {i["full_name"]: i for i in resp.json()["items"]}

    emp = items["María Sin Rol"]
    assert emp["has_user_account"] is True
    assert emp["role_assigned"] is False


async def test_list_marks_orphan_user_id_as_no_account(client, db, admin_user):
    """``user_id`` pointing to a deleted user → account False (orphan)."""
    orphan_id = ObjectId()
    _seed_employee(db, full_name="Huérfano", user_id=orphan_id)
    assert db.users.count_documents({"_id": orphan_id}) == 0

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.get("/api/hr", params={"prop_id": 1})
    items = {i["full_name"]: i for i in resp.json()["items"]}

    emp = items["Huérfano"]
    assert emp["has_user_account"] is False
    assert emp["role_assigned"] is False


async def test_list_marks_employee_without_user_id(client, db, admin_user):
    """No ``user_id`` at all → both flags False (frontend shows 'sin cuenta')."""
    _seed_employee(db, full_name="Sin Cuenta")

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    resp = await client.get("/api/hr", params={"prop_id": 1})
    items = {i["full_name"]: i for i in resp.json()["items"]}

    emp = items["Sin Cuenta"]
    assert emp["has_user_account"] is False
    assert emp["role_assigned"] is False
