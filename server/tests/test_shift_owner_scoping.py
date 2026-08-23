"""Scoping de turnos por dueño (2026-08): cada empleado solo ve y cierra SU turno.

El turno de caja sigue siendo UNO por hotel (un solo cajón físico), pero su
visibilidad y cierre quedan aislados por el usuario que lo abrió (``opened_by`` /
``opened_by_id``). Un empleado del mismo hotel NO ve el turno activo de un
compañero (ni su detalle, ni lo puede cerrar, ni recibe sus datos en el 409 de
apertura); el gerente (``shifts.manage``) sí ve y cierra cualquier turno.

Migración E (2026-08): reception gatea POR HOTEL (``require_prop_permission``)
— cada usuario necesita hotel_roles + role_assignments en los props de test
(``_grant_hotel_scopes``) y las llamadas llevan ``prop_id``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId

from tests.conftest import _seed_user, login

_UTC = UTC

# Props de test usados por este archivo (9901-9909): con la migración E,
# reception gatea POR HOTEL (require_prop_permission) — sin role_assignment
# el rol global ya no basta. Cada usuario recibe hotel_roles + assignments en
# todos estos props para que el scoping por DUEÑO siga siendo el foco del test.
_SCOPE_PROPS = list(range(9901, 9910))


def _grant_hotel_scopes(db, user_id, permissions: list[str], suffix: str) -> None:
    """Crea hotel_roles + role_assignments del usuario en los props de test.

    El nombre del hotel role es único por usuario: hotel_roles tiene índice
    único (prop_id, name) — dos empleados en el mismo prop NO pueden
    compartir nombre de rol.
    """
    for prop_id in _SCOPE_PROPS:
        role_id = db.hotel_roles.insert_one(
            {
                "prop_id": prop_id,
                "name": f"test_role_{suffix}",
                "display_name": f"Rol Test {suffix}",
                "permissions": permissions,
                "is_active": True,
                "created_at": datetime.now(_UTC),
                "updated_at": datetime.now(_UTC),
            }
        ).inserted_id
        db.role_assignments.insert_one(
            {"user_id": user_id, "prop_id": prop_id, "role_id": role_id}
        )
    db.users.update_one({"_id": user_id}, {"$set": {"assigned_hotels": _SCOPE_PROPS}})


def _seed_role(db, name: str, permissions: list[str]) -> None:
    db.roles.delete_many({"role_name": name})
    db.roles.insert_one({"role_name": name, "permissions": permissions, "is_active": True})


def _seed_shift(db, prop_id: int, *, opened_by: str, opened_by_id, status: str = "open"):
    """Insert a shift owned by ``opened_by`` (with its FK ``opened_by_id``)."""
    db.reception_shifts.delete_many({"prop_id": prop_id})
    inserted = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": status,
            "shift_type": "morning",
            "start_time": datetime.now(_UTC).isoformat(),
            "transactions": [],
            "cash_initial": 100.0,
            "opened_by": opened_by,
            "opened_by_id": opened_by_id,
            "employee": opened_by,
        }
    )
    return str(inserted.inserted_id)


def _seed_two_recepcionistas(db) -> tuple[dict, dict]:
    _seed_role(db, "recepcionista", ["shifts.read", "shifts.create", "shifts.update"])
    a = _seed_user(
        db, username="recep_a", email="recep_a@example.com",
        password="Pass123!", role="recepcionista",
    )
    b = _seed_user(
        db, username="recep_b", email="recep_b@example.com",
        password="Pass123!", role="recepcionista",
    )
    _grant_hotel_scopes(db, ObjectId(a["user_id"]), ["shifts.read", "shifts.create", "shifts.update"], "recep_a")
    _grant_hotel_scopes(db, ObjectId(b["user_id"]), ["shifts.read", "shifts.create", "shifts.update"], "recep_b")
    return a, b


def _seed_manager(db) -> dict:
    _seed_role(db, "gerente", ["shifts.read", "shifts.manage"])
    manager = _seed_user(
        db, username="gerente_x", email="gerente_x@example.com",
        password="Pass123!", role="gerente",
    )
    _grant_hotel_scopes(db, ObjectId(manager["user_id"]), ["shifts.read", "shifts.manage"], "gerente_x")
    return manager


def _user_id(db, username: str):
    return db.users.find_one({"username": username})["_id"]


# ── GET /shifts/active ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_active_shift_hidden_from_other_employee(client, db):
    a, b = _seed_two_recepcionistas(db)
    prop_id = 9901
    _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, b["username"], b["password"])
    resp = await client.get("/api/reception/shifts/active", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # El turno de A queda oculto: shift null + flag occupied, SIN datos de caja.
    assert body["shift"] is None
    assert body["occupied"] is True
    assert body["opener_username"] == a["username"]
    # Sí se expone cuándo alcanza su límite (sin caja/transacciones del ajeno).
    assert isinstance(body["expires_at"], str) and body["expires_at"]
    assert isinstance(body["max_open_hours"], (int, float))
    assert "cash_initial" not in body
    assert "transactions" not in body


@pytest.mark.asyncio
async def test_active_shift_visible_to_owner(client, db):
    a, _ = _seed_two_recepcionistas(db)
    prop_id = 9902
    _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, a["username"], a["password"])
    resp = await client.get("/api/reception/shifts/active", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["shift"] is not None
    assert body["shift"]["opened_by"] == a["username"]
    assert body.get("occupied") is None


@pytest.mark.asyncio
async def test_active_shift_visible_to_manager(client, db):
    a, _ = _seed_two_recepcionistas(db)
    manager = _seed_manager(db)
    prop_id = 9903
    _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, manager["username"], manager["password"])
    resp = await client.get("/api/reception/shifts/active", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["shift"] is not None
    assert body["shift"]["opened_by"] == a["username"]


# ── GET /shifts/{id} ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_shift_detail_hidden_from_other_employee(client, db):
    a, b = _seed_two_recepcionistas(db)
    prop_id = 9904
    shift_id = _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, b["username"], b["password"])
    resp = await client.get(f"/api/reception/shifts/{shift_id}", params={"prop_id": prop_id})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_shift_detail_visible_to_owner_and_manager(client, db):
    a, _ = _seed_two_recepcionistas(db)
    manager = _seed_manager(db)
    prop_id = 9905
    shift_id = _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, a["username"], a["password"])
    assert (await client.get(f"/api/reception/shifts/{shift_id}", params={"prop_id": prop_id})).status_code == 200

    assert await login(client, manager["username"], manager["password"])
    assert (await client.get(f"/api/reception/shifts/{shift_id}", params={"prop_id": prop_id})).status_code == 200


# ── POST /shifts/{id}/close ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_shift_rejected_for_other_employee(client, db):
    a, b = _seed_two_recepcionistas(db)
    prop_id = 9906
    shift_id = _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, b["username"], b["password"])
    resp = await client.post(
        f"/api/reception/shifts/{shift_id}/close",
        params={"prop_id": prop_id},
        json={"cash_counted": 100.0},
    )
    assert resp.status_code == 403
    assert "cerrar" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_close_shift_allowed_for_manager(client, db):
    a, _ = _seed_two_recepcionistas(db)
    manager = _seed_manager(db)
    prop_id = 9907
    shift_id = _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, manager["username"], manager["password"])
    resp = await client.post(
        f"/api/reception/shifts/{shift_id}/close",
        params={"prop_id": prop_id},
        json={"cash_counted": 100.0},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["shift"]["status"] == "closed"


# ── GET /shifts (listado) ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_shifts_scoped_to_owner(client, db):
    a, b = _seed_two_recepcionistas(db)
    prop_id = 9908
    # A tiene un turno abierto; B tiene un turno cerrado en el mismo hotel.
    db.reception_shifts.delete_many({"prop_id": prop_id})
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id, "status": "open", "shift_type": "morning",
            "start_time": datetime.now(_UTC).isoformat(), "transactions": [],
            "cash_initial": 100.0, "opened_by": a["username"],
            "opened_by_id": _user_id(db, a["username"]),
        }
    )
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id, "status": "closed", "shift_type": "morning",
            "start_time": datetime.now(_UTC).isoformat(), "transactions": [],
            "cash_initial": 50.0, "opened_by": b["username"],
            "opened_by_id": _user_id(db, b["username"]),
        }
    )

    assert await login(client, b["username"], b["password"])
    resp = await client.get("/api/reception/shifts", params={"prop_id": prop_id})
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert all(s["opened_by"] == b["username"] for s in items)
    assert any(s["status"] == "closed" for s in items)

    assert await login(client, a["username"], a["password"])
    resp = await client.get("/api/reception/shifts", params={"prop_id": prop_id})
    items = resp.json()["items"]
    assert all(s["opened_by"] == a["username"] for s in items)


# ── POST /shifts/open (409 redactado) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_open_conflict_redacted_for_other_employee(client, db):
    a, b = _seed_two_recepcionistas(db)
    prop_id = 9909
    _seed_shift(db, prop_id, opened_by=a["username"], opened_by_id=_user_id(db, a["username"]))

    assert await login(client, b["username"], b["password"])
    resp = await client.post(
        "/api/reception/shifts/open",
        params={"prop_id": prop_id},
        json={"prop_id": prop_id, "shift_type": "morning", "employee": "B"},
    )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "active_shift_exists"
    # El snapshot del turno ajeno NO viaja (redactado) y el mensaje no revela datos.
    assert detail["active_shift"] is None
    assert "otro empleado" in detail["message"].lower()
