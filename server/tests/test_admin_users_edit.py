"""Tests for editing users from the system-admin view.

Covers the ``PUT /api/admin/users/{user_id}`` endpoint (gated by
``users.update``), the ``roles`` selector payload exposed by
``GET /api/admin/users``, and the guards that protect the acting
account and super-admin accounts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
import pytest
from passlib.context import CryptContext

from tests.conftest import login


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _seed_role(db, *, role_name: str, permissions: list[str]) -> dict[str, Any]:
    role_id = ObjectId()
    db.roles.insert_one(
        {
            "_id": role_id,
            "role_name": role_name,
            "display_name": role_name.replace("_", " ").title(),
            "description": f"Rol de prueba {role_name}",
            "permissions": permissions,
            "is_system": False,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return {"_id": role_id, "role_name": role_name}


def _seed_user(
    db,
    *,
    username: str,
    email: str,
    password: str,
    role: str,
    role_id: Any | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    user_id = ObjectId()
    doc: dict[str, Any] = {
        "_id": user_id,
        "username": username,
        "email": email,
        "display_name": username.replace("_", " ").title(),
        "password_hash": _pwd.hash(password),
        "primary_role": role,
        "is_active": is_active,
        "created_at": datetime.now(timezone.utc),
    }
    if role_id is not None:
        doc["primary_role_id"] = role_id
        doc["role_ids"] = [role_id]
    db.users.insert_one(doc)
    return {
        "user_id": str(user_id),
        "username": username,
        "email": email,
        "password": password,
        "primary_role": role,
    }


@pytest.mark.asyncio
async def test_users_overview_exposes_roles_selector(client, db, admin_user):
    """GET /api/admin/users must return the role catalog so the frontend can
    render the role select in the edit modal."""
    role = _seed_role(db, role_name="recepcionista", permissions=["reservations.read"])
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.get("/api/admin/users")
    assert response.status_code == 200
    payload = response.json()
    assert "roles" in payload
    names = [r["role_name"] for r in payload["roles"]]
    assert "recepcionista" in names
    roles = {r["role_name"]: r for r in payload["roles"]}
    assert roles["recepcionista"]["description"]


@pytest.mark.asyncio
async def test_update_user_fields_and_role(client, db, admin_user):
    """PUT updates display_name, email, primary_role and keeps the FK in sync."""
    role = _seed_role(db, role_name="admin_sistema", permissions=["users.manage"])
    target = _seed_user(
        db,
        username="gerente1",
        email="gerente1@example.com",
        password="Pass123!",
        role="recepcionista",
        role_id=role["_id"],
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={
            "display_name": "Gerente Uno Editado",
            "email": "gerente1.nuevo@example.com",
            "primary_role": "admin_sistema",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True

    updated = db.users.find_one({"_id": ObjectId(target["user_id"])})
    assert updated["display_name"] == "Gerente Uno Editado"
    assert updated["email"] == "gerente1.nuevo@example.com"
    assert updated["primary_role"] == "admin_sistema"
    assert str(updated["primary_role_id"]) == str(role["_id"])
    assert str(role["_id"]) in [str(r) for r in updated.get("role_ids", [])]


@pytest.mark.asyncio
async def test_update_user_rejects_invalid_email(client, db, admin_user):
    target = _seed_user(
        db,
        username="recepcion",
        email="recepcion@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"email": "correo-invalido"},
    )
    assert response.status_code == 400
    assert "email" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_update_user_rejects_duplicate_email(client, db, admin_user):
    _seed_user(
        db,
        username="ocupado",
        email="ocupado@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    target = _seed_user(
        db,
        username="libre",
        email="libre@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"email": "ocupado@example.com"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_cannot_deactivate_self(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{admin_user['user_id']}",
        json={"is_active": False},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_rejects_protected_super_admin(client, db, admin_user):
    other_admin = _seed_user(
        db,
        username="super2",
        email="super2@example.com",
        password="Pass123!",
        role="super_admin",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{other_admin['user_id']}",
        json={"display_name": "No debería pasar"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_resets_password(client, db, admin_user):
    target = _seed_user(
        db,
        username="cambiapass",
        email="cambiapass@example.com",
        password="Vieja123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"password": "Nueva123!"},
    )
    assert response.status_code == 200

    doc = db.users.find_one({"username": "cambiapass"})
    assert _pwd.verify("Nueva123!", doc["password_hash"])
    assert not _pwd.verify("Vieja123!", doc["password_hash"])


@pytest.mark.asyncio
async def test_update_user_requires_users_update_permission(client, db):
    """A user holding only users.read cannot edit users."""
    role = _seed_role(db, role_name="lector", permissions=["users.read"])
    editor = _seed_user(
        db,
        username="solo_lector",
        email="solo_lector@example.com",
        password="Pass123!",
        role="lector",
        role_id=role["_id"],
    )
    target = _seed_user(
        db,
        username="victima",
        email="victima@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, editor["username"], editor["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"display_name": "Editado"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_writes_audit_log(client, db, admin_user):
    target = _seed_user(
        db,
        username="auditado",
        email="auditado@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"display_name": "Auditado Editado"},
    )
    assert response.status_code == 200

    entry = db.user_activity_logs.find_one({"action": "admin.user_updated"})
    assert entry is not None
    assert entry["details"]["target_username"] == "auditado"
    assert entry["username"] == admin_user["username"]


@pytest.mark.asyncio
async def test_update_user_unknown_role_rejected(client, db, admin_user):
    target = _seed_user(
        db,
        username="rolraro",
        email="rolraro@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"primary_role": "rol_que_no_existe"},
    )
    assert response.status_code == 400


# ─── Username ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_user_username(client, db, admin_user):
    target = _seed_user(
        db,
        username="viejo_nombre",
        email="viejo@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"username": "nuevo_nombre"},
    )
    assert response.status_code == 200
    assert db.users.find_one({"email": "viejo@example.com"})["username"] == "nuevo_nombre"


@pytest.mark.asyncio
async def test_update_user_username_duplicate_rejected(client, db, admin_user):
    _seed_user(
        db,
        username="ocupado",
        email="ocupado2@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    target = _seed_user(
        db,
        username="libre2",
        email="libre2@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"username": "ocupado"},
    )
    assert response.status_code == 400
    assert db.users.find_one({"email": "libre2@example.com"})["username"] == "libre2"


@pytest.mark.asyncio
async def test_update_user_username_with_spaces_rejected(client, db, admin_user):
    target = _seed_user(
        db,
        username="sin_espacios",
        email="sin_espacios@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"username": "con espacios"},
    )
    assert response.status_code == 400


# ─── Assigned hotels (roles de hotel) ───────────────────────────────────


HOTEL_ROLES = ("hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "maintenance")


def _seed_hotel(db, prop_id: int, label: str) -> None:
    db.dim_hotels.insert_one({"prop_id": prop_id, "hotel_name": label, "display_name": label})


@pytest.mark.asyncio
async def test_update_user_assigned_hotels_for_hotel_role(client, db, admin_user):
    _seed_hotel(db, 1, "Hotel Lima Centro")
    _seed_hotel(db, 2, "Hotel Cusco Plaza")
    target = _seed_user(
        db,
        username="socio_hotel",
        email="socio_hotel@example.com",
        password="Pass123!",
        role="gerente_hotel",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"assigned_hotels": [1, 2]},
    )
    assert response.status_code == 200
    doc = db.users.find_one({"username": "socio_hotel"})
    assert doc["assigned_hotels"] == [1, 2]


@pytest.mark.asyncio
async def test_update_user_assigned_hotels_rejected_for_non_hotel_role(client, db, admin_user):
    _seed_hotel(db, 1, "Hotel Lima Centro")
    target = _seed_user(
        db,
        username="recepcion_hoteles",
        email="recepcion_hoteles@example.com",
        password="Pass123!",
        role="recepcionista",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"assigned_hotels": [1]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_assigned_hotels_empty_rejected(client, db, admin_user):
    target = _seed_user(
        db,
        username="socio_vacio",
        email="socio_vacio@example.com",
        password="Pass123!",
        role="gerente_hotel",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"assigned_hotels": []},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_user_assigned_hotels_unknown_id_rejected(client, db, admin_user):
    target = _seed_user(
        db,
        username="socio_fantasma",
        email="socio_fantasma@example.com",
        password="Pass123!",
        role="gerente_hotel",
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        f"/api/admin/users/{target['user_id']}",
        json={"assigned_hotels": [9999]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_users_overview_exposes_assigned_hotels_with_labels(client, db, admin_user):
    _seed_hotel(db, 1, "Hotel Lima Centro")
    _seed_hotel(db, 2, "Hotel Cusco Plaza")
    target = _seed_user(
        db,
        username="socio_overview",
        email="socio_overview@example.com",
        password="Pass123!",
        role="gerente_hotel",
    )
    db.users.update_one(
        {"username": "socio_overview"},
        {"$set": {"assigned_hotels": [1, 2]}},
    )
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.get("/api/admin/users")
    assert response.status_code == 200
    payload = response.json()
    user = next(u for u in payload["users"] if u["username"] == "socio_overview")
    labels = {h["prop_id"]: h["label"] for h in user["assigned_hotels"]}
    assert labels == {1: "Hotel Lima Centro", 2: "Hotel Cusco Plaza"}
