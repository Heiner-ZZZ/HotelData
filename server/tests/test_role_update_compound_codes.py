"""PUT /api/admin/permissions/roles/{role_name} must accept compound codes.

Regression: ``update_role_definition`` required a ``<resource>.read`` sibling
for EVERY non-read permission code. Compound standalone codes like
``hotel.manage_roles`` (the only code behind the "Equipo y permisos" nav
item) have no ``hotel.read`` in the catalog, so saving any role that holds
them — e.g. ``gerente_hotel`` from the system-admin role editor — failed with
400 "No se pueden guardar acciones sin un permiso Read disponible: hotel.read".

The preview filter already handled this class (``_filter_preview_codes``
keeps ``hotel.manage_roles``); the save path must use the same criterion:
only CRUD actions (create/update/delete/manage/execute) imply a read
dependency. Compound actions are complete permissions on their own.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tests.conftest import login

pytestmark = pytest.mark.asyncio

CATALOG_CODES = [
    "hotel.manage_roles",
    "dashboard.read",
    "reservations.read",
    "reservations.manage",
    "hr.read",
    "users.read",
    "users.update",
    "inventory.read",
    "properties.read",
    "properties.approve",
]


def _seed_catalog(db) -> None:
    for code in CATALOG_CODES:
        db.permissions.insert_one(
            {
                "permission_code": code,
                "description": code,
                "is_system": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )


def _seed_role(db, *, role_name: str, permissions: list[str]) -> None:
    db.roles.insert_one(
        {
            "role_name": role_name,
            "display_name": role_name.replace("_", " ").title(),
            "description": f"Rol de prueba {role_name}",
            "permissions": permissions,
            "is_system": True,
            "is_template": False,
            "created_at": datetime.now(timezone.utc),
        }
    )


async def test_put_role_accepts_compound_code_without_read_sibling(client, db, admin_user):
    """``hotel.manage_roles`` must save even though ``hotel.read`` is not a
    catalog code (regression: the system-admin role editor returned 400 when
    saving gerente_hotel)."""
    _seed_catalog(db)
    _seed_role(db, role_name="gerente_hotel", permissions=["hotel.manage_roles", "dashboard.read"])
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        "/api/admin/permissions/roles/gerente_hotel",
        json={
            "description": "Gerente de hotel",
            "permission_codes": ["hotel.manage_roles", "dashboard.read"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True


async def test_put_role_keeps_compound_code_in_stored_permissions(client, db, admin_user):
    """The compound code survives the round-trip and lands in the role doc."""
    _seed_catalog(db)
    _seed_role(db, role_name="gerente_hotel", permissions=["dashboard.read"])
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        "/api/admin/permissions/roles/gerente_hotel",
        json={
            "description": "Gerente de hotel",
            "permission_codes": ["hotel.manage_roles", "dashboard.read"],
        },
    )
    assert response.status_code == 200, response.text

    role = db.roles.find_one({"role_name": "gerente_hotel"})
    assert role is not None
    assert "hotel.manage_roles" in role["permissions"]
    assert "dashboard.read" in role["permissions"]


async def test_round_trip_all_catalog_roles_holding_compound_code(client, db, admin_user):
    """Audit regression: every role in the catalog that holds
    ``hotel.manage_roles`` (the only compound code without a ``hotel.read``
    sibling) must round-trip through the role editor with its FULL permission
    set. Mirrors the dev-DB audit: gerente_hotel (27 codes) and hotel_partner
    (10 codes) both hold it; saving their complete set must return 200."""
    _seed_catalog(db)
    _seed_role(
        db,
        role_name="gerente_hotel",
        permissions=[
            "hotel.manage_roles",
            "dashboard.read",
            "reservations.manage",
            "reservations.read",
            "properties.approve",
            "properties.read",
        ],
    )
    _seed_role(
        db,
        role_name="hotel_partner",
        permissions=["hotel.manage_roles", "dashboard.read", "properties.read"],
    )
    await login(client, admin_user["username"], admin_user["password"])

    for role_name, codes in [
        ("gerente_hotel", ["hotel.manage_roles", "dashboard.read", "reservations.manage", "reservations.read", "properties.approve", "properties.read"]),
        ("hotel_partner", ["hotel.manage_roles", "dashboard.read", "properties.read"]),
    ]:
        response = await client.put(
            f"/api/admin/permissions/roles/{role_name}",
            json={"description": "Rol de prueba", "permission_codes": codes},
        )
        assert response.status_code == 200, f"{role_name}: {response.text}"
        assert response.json()["ok"] is True


async def test_put_role_still_rejects_crud_action_without_read_sibling(client, db, admin_user):
    """The guard remains for real CRUD grants: ``users.update`` without a
    ``users.read`` in the catalog is still rejected (400)."""
    _seed_catalog(db)
    _seed_role(db, role_name="gerente_hotel", permissions=["dashboard.read"])
    await login(client, admin_user["username"], admin_user["password"])

    db.permissions.delete_many({"permission_code": "users.read"})
    response = await client.put(
        "/api/admin/permissions/roles/gerente_hotel",
        json={
            "description": "Gerente de hotel",
            "permission_codes": ["users.update", "dashboard.read"],
        },
    )

    assert response.status_code == 400
    assert "users.read" in response.json()["message"]
