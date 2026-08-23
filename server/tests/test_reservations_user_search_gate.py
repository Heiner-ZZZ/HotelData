"""Prefill de huéspedes (GET /api/management/users/search) — gate de reservas.

Decisión C 2026-08 (lógica dura): el endpoint busca usuarios registrados para
precargar los datos del huésped al crear una reserva. Es una operación de
RESERVAS, no de plataforma: se gatea con ``reservations.manage`` /
``reservations.read``. ``users.read`` (lista global de usuarios del sistema)
queda como permiso de plataforma y NO debe ser requisito del prefill — un
recepcionista con su rol canónico (reservations.*, sin users.read) debe poder
buscar huéspedes.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from bson import ObjectId
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(UTC)


def _seed_catalog(db) -> None:
    for code in ("reservations.read", "reservations.manage", "users.read"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )


def _seed_recepcionista(db) -> dict[str, str]:
    db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepción",
            "permissions": ["reservations.read", "reservations.manage"],
            "is_system": True,
            "created_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": "recepcion_prefill",
            "email": "recepcion_prefill@hotel.local",
            "display_name": "Recepción",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "recepcionista",
            "role_ids": [ObjectId()],
            "assigned_hotels": [1],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": "recepcion_prefill", "password": "Pass123!"}


@pytest_asyncio.fixture
async def logged_recepcionista(client, db):
    _seed_catalog(db)
    creds = _seed_recepcionista(db)
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest.mark.asyncio
async def test_prefill_works_with_reservations_read_and_without_users_read(
    logged_recepcionista, db
):
    """El recepcionista canónico (reservations.*, SIN users.read) puede buscar
    huéspedes registrados para el prefill."""
    db.users.insert_one(
        {
            "username": "ana_guest",
            "email": "ana@test.com",
            "display_name": "Ana Huesped",
            "is_active": True,
            "created_at": _now(),
        }
    )
    resp = await logged_recepcionista.get(
        "/api/management/users/search", params={"q": "ana", "limit": 10}
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert any("ana" in (i.get("email") or "").lower() for i in items), items
