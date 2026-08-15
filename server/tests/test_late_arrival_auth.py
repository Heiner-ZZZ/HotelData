"""Autorización del sprint de llegadas tardías.

La declaración de llegada tardía protege la reserva del auto no-show y es una
señal OPERATIVA de recepción, no una autorización gerencial: el gate es
``check-ins.manage`` (recepcionista incluido). A diferencia del early check-in
fuera de cortesía (``check-ins.early_approve``) y de la reapertura de no-show
(``check-ins.no_show_reopen``), NO requiere un código adicional — el contrato
de permisos del sprint es:

| Capacidad                              | Permiso                          | Roles                              |
|----------------------------------------|----------------------------------|------------------------------------|
| Declarar/retirar llegada tardía        | check-ins.manage                 | recepcionista, gerente_hotel,      |
|                                        |                                  | super_admin                        |
| Marcar no-show manual                  | reservations.update              | recepcionista, gerente_hotel,      |
|                                        |                                  | super_admin                        |
| Aprobar early check-in fuera cortesía  | check-ins.early_approve          | gerente_hotel, super_admin         |
| Reabrir no-show (caso gerente)         | check-ins.no_show_reopen         | gerente_hotel, super_admin         |
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from passlib.context import CryptContext

from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from tests.conftest import login

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

LATE_ARRIVAL_GATE = "check-ins.manage"


# ─────────────────────── Catálogo canónico ─────────────────────────────


def test_late_arrival_gate_is_canonical_front_desk_permission() -> None:
    """La declaración de llegada tardía usa ``check-ins.manage`` (ya canónico,
    ya en recepción) — no se inventa un código nuevo para una señal operativa."""
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert LATE_ARRIVAL_GATE in catalog_codes
    assert LATE_ARRIVAL_GATE in ROLE_PERMISSION_CODES["recepcionista"]
    assert LATE_ARRIVAL_GATE in ROLE_PERMISSION_CODES["gerente_hotel"]
    assert LATE_ARRIVAL_GATE in ROLE_PERMISSION_CODES["super_admin"]
    assert LATE_ARRIVAL_GATE not in ROLE_PERMISSION_CODES["cliente"]
    # La reapertura de no-show sigue siendo la única autorización gerencial
    # del sprint (defensa en profundidad role allow-list aparte).
    assert "check-ins.no_show_reopen" not in ROLE_PERMISSION_CODES["recepcionista"]


# ─────────────────────────── Helpers ───────────────────────────────────


def _seed_booking(db, booking_id: str = "BK-LA-AUTH") -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "guest_name": "Late Arrival Auth Guest",
            "guest_email": "late-auth@test.com",
            "status": "confirmed",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-12",
            "total_nights": 2,
            "total_price": 220.0,
            "currency": "USD",
            "is_test": True,
            "created_at": datetime.now(UTC),
        }
    )


def _seed_receptionist(db) -> dict[str, str]:
    """Recepcionista con ``check-ins.manage`` (perfil canónico de recepción)."""
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
            "username": "recepcionista_late_test",
            "email": "recepcionista_late_test@hotel.local",
            "display_name": "Recepcionista Late Test",
            "password_hash": _pwd.hash(password),
            "primary_role": "recepcionista",
            "role_ids": [role_id],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )
    return {"username": "recepcionista_late_test", "password": password}


# ─────────────────────────── Ruta: contrato ────────────────────────────


@pytest.mark.asyncio
async def test_receptionist_can_declare_late_arrival(client, db) -> None:
    """Recepción (check-ins.manage) declara la llegada tardía: 200 + flag."""
    credentials = _seed_receptionist(db)
    _seed_booking(db)
    assert await login(client, credentials["username"], credentials["password"]) == 200

    response = await client.post(
        "/api/management/check-ins/BK-LA-AUTH/declare-late-arrival",
        json={"declared_late_arrival": True, "estimated_arrival_time": "01:45"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["declared_late_arrival"] is True
    doc = db.booking_orders.find_one({"booking_id": "BK-LA-AUTH"})
    assert doc["declared_late_arrival"] is True
    assert doc["estimated_arrival_time"] == "01:45"


@pytest.mark.asyncio
async def test_receptionist_can_clear_late_arrival(client, db) -> None:
    credentials = _seed_receptionist(db)
    _seed_booking(db)
    db.booking_orders.update_one(
        {"booking_id": "BK-LA-AUTH"},
        {"$set": {"declared_late_arrival": True}},
    )
    assert await login(client, credentials["username"], credentials["password"]) == 200

    response = await client.post(
        "/api/management/check-ins/BK-LA-AUTH/declare-late-arrival",
        json={"declared_late_arrival": False},
    )

    assert response.status_code == 200
    assert response.json()["declared_late_arrival"] is False
    doc = db.booking_orders.find_one({"booking_id": "BK-LA-AUTH"})
    assert doc["declared_late_arrival"] is False


@pytest.mark.asyncio
async def test_cliente_cannot_declare_late_arrival(client, cliente_user, db) -> None:
    """El huésped (rol cliente, sin check-ins.manage) recibe 403 y la reserva
    no se toca — la declaración es operación de recepción."""
    _seed_booking(db)
    assert await login(client, cliente_user["username"], cliente_user["password"]) == 200

    response = await client.post(
        "/api/management/check-ins/BK-LA-AUTH/declare-late-arrival",
        json={"declared_late_arrival": True, "estimated_arrival_time": "01:45"},
    )

    assert response.status_code == 403
    doc = db.booking_orders.find_one({"booking_id": "BK-LA-AUTH"})
    assert doc.get("declared_late_arrival") in (None, False)
    assert doc.get("estimated_arrival_time") is None
