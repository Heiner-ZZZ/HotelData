"""Migración E (2026-08): expenses gatea por hotel — tests de ruta.

Un usuario cuyo rol GLOBAL tiene ``revenue.read`` pero SIN ``role_assignment``
para el hotel recibe 403 (el rol global ya no basta en contexto de hotel);
con el rol del hotel que otorga el código → 200. Sin ``prop_id`` → 400.
``revenue.manage`` NO abre lecturas (separación read/manage). Los catálogos
de referencia (categories, chart-of-accounts) siguen globales SIN prop_id.
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
    for code in ("revenue.read", "revenue.manage"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )


def _seed_user(db, *, username: str, role: str, permissions: list[str],
               assigned_hotels: list[int] | None = None) -> dict[str, str]:
    db.roles.insert_one(
        {
            "role_name": role,
            "display_name": role.replace("_", " ").title(),
            "permissions": permissions,
            "is_system": True,
            "created_at": _now(),
        }
    )
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@hotel.local",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": role,
            "role_ids": [],
            "assigned_hotels": assigned_hotels if assigned_hotels is not None else [],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": username, "password": "Pass123!"}


def _seed_hotel_role(db, *, prop_id: int = 1, permissions: list[str]) -> ObjectId:
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": "rol_hotel_expenses",
            "display_name": "Rol Hotel Expenses",
            "permissions": permissions,
            "is_active": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id


async def _login(client, creds: dict[str, str]) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text


@pytest_asyncio.fixture
async def global_analista(client, db):
    """Rol GLOBAL con revenue.read, SIN role_assignment (el hueco pre-E)."""
    _seed_catalog(db)
    creds = _seed_user(db, username="analista_exp_global", role="revenue_manager",
                       permissions=["revenue.read"], assigned_hotels=[1])
    await _login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_analista(client, db, global_analista):
    role_id = _seed_hotel_role(db, permissions=["revenue.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


@pytest_asyncio.fixture
async def hotel_gestor(client, db, global_analista):
    """Hotel role con SOLO revenue.manage: no abre lecturas (separación)."""
    role_id = _seed_hotel_role(db, permissions=["revenue.manage"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_analista["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_analista


class TestExpensesPropGate:
    """Operación financiera = por hotel (rol global sin asignación → 403)."""

    @pytest.mark.asyncio
    async def test_list_invoices_403_global_role_without_assignment(self, client, global_analista):
        resp = await client.get("/api/expenses/invoices", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_invoices_400_without_prop_id(self, client, db, admin_user):
        await _login(client, admin_user)
        resp = await client.get("/api/expenses/invoices")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_list_invoices_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/expenses/invoices", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_ledger_report_200_with_hotel_role(self, client, hotel_analista):
        resp = await client.get("/api/expenses/ledger/summary", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_ledger_path_alias_uses_path_prop_id(self, client, hotel_analista):
        resp = await client.get("/api/expenses/ledger/1/periods")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_read_does_not_open_writes(self, client, hotel_analista):
        """revenue.read NO abre escrituras (la jerarquía manage⊃read solo va
        en un sentido): POST /invoices exige revenue.manage."""
        resp = await client.post(
            "/api/expenses/invoices?prop_id=1",
            json={"vendor_name": "Proveedor", "category": "otros",
                  "amount": 1.0, "prop_id": 1},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_create_invoice_passes_gate_with_manage(self, client, hotel_gestor):
        """El write con revenue.manage en el rol del hotel pasa el GATE
        (nunca 403): el status downstream es negocio de facturas, que tiene
        sus propios tests."""
        resp = await client.post(
            "/api/expenses/invoices?prop_id=1",
            json={"vendor_name": "Proveedor", "category": "otros",
                  "amount": 1.0, "prop_id": 1},
        )
        assert resp.status_code != 403, resp.text

    @pytest.mark.asyncio
    async def test_invoice_detail_404_of_another_hotel(self, client, db, hotel_analista):
        invoice_id = db.expense_invoices.insert_one(
            {"prop_id": 2, "vendor_name": "Proveedor Otro", "status": "pending",
             "amount": 100.0, "total": 100.0, "created_at": _now()}
        ).inserted_id
        resp = await client.get(f"/api/expenses/invoices/{invoice_id}", params={"prop_id": 1})
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_categories_global_exception_without_prop_id(self, client, global_analista):
        """Catálogo global de categorías: revenue.read GLOBAL basta SIN prop_id."""
        resp = await client.get("/api/expenses/categories")
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_chart_of_accounts_global_exception_without_prop_id(self, client, global_analista):
        """COA global: revenue.read GLOBAL basta SIN prop_id."""
        resp = await client.get("/api/expenses/ledger/accounts")
        assert resp.status_code == 200, resp.text
