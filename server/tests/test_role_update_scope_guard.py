"""Guard de scope en el editor GLOBAL de roles (C 2026-08, lógica dura).

``update_role_definition`` (PUT /api/admin/permissions/roles/{role_name},
editor del super admin) no debe poder otorgar códigos de PLATAFORMA (system:
etl.*, users.*, roles.*, audit.*, settings.*, properties.approve…) a roles
no-plataforma, ni códigos de HUÉSPED (guest: account.*, search.*) a roles que
no son cliente. La allow-list vive en ``PLATFORM_ROLES`` / ``GUEST_ROLES``.

Esto complementa el invariante del seed: aunque el seed esté sano, el editor
runtime no puede romperlo por accidente.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId

from src.app.modules.admin.service.role_update import update_role_definition

_ACTING = {"username": "super_admin_test", "_id": ObjectId()}


def _now() -> datetime:
    return datetime.now(UTC)


def _seed(db) -> None:
    for code in ("reservations.read", "users.read", "etl.read", "etl.execute", "account.read"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )
    db.roles.insert_one(
        {"role_name": "recepcionista", "display_name": "Recepción",
         "permissions": ["reservations.read"], "created_at": _now()}
    )
    db.roles.insert_one(
        {"role_name": "operador_datos", "display_name": "Operador",
         "permissions": ["etl.execute"], "created_at": _now()}
    )
    db.roles.insert_one(
        {"role_name": "cliente", "display_name": "Cliente",
         "permissions": ["account.read"], "created_at": _now()}
    )


def test_platform_codes_rejected_on_hotel_roles(db) -> None:
    _seed(db)
    res = update_role_definition(
        "recepcionista", "d", ["reservations.read", "users.read"], _ACTING
    )
    assert res["ok"] is False, "users.read (plataforma) debe rechazarse en recepcionista"
    assert "users.read" in res["message"]
    assert "plataforma" in res["message"].lower() or "huésped" in res["message"].lower()

    res_etl = update_role_definition("recepcionista", "d", ["etl.execute"], _ACTING)
    assert res_etl["ok"] is False, "etl.execute (plataforma) debe rechazarse en recepcionista"


def test_guest_codes_rejected_on_non_guest_roles(db) -> None:
    _seed(db)
    res = update_role_definition("recepcionista", "d", ["account.read"], _ACTING)
    assert res["ok"] is False, "account.read (huésped) debe rechazarse en recepcionista"


def test_platform_roles_may_carry_platform_codes(db) -> None:
    _seed(db)
    res = update_role_definition("operador_datos", "d", ["etl.execute"], _ACTING)
    assert res["ok"] is True, f"operador_datos puede portar etl.execute: {res}"


def test_guest_role_may_carry_guest_codes(db) -> None:
    _seed(db)
    res = update_role_definition("cliente", "d", ["account.read"], _ACTING)
    assert res["ok"] is True, f"cliente puede portar account.read: {res}"
