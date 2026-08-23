"""Migración E (2026-08): billing gatea por hotel — tests de ruta.

Un usuario cuyo rol GLOBAL tiene ``billing.read`` pero SIN ``role_assignment``
para el hotel recibe 403 (el rol global ya no basta en contexto de hotel);
con el rol del hotel que otorga el código → 200. Sin ``prop_id`` → 400.
Cross-hotel: una factura de otro hotel no es legible (404). El combo
``require_any_prop_permission`` (emisión fiscal = ``billing.manage`` O
``check-outs.manage``) deja pasar al usuario que tiene SOLO el segundo
código en su rol de hotel. Las excepciones globales documentadas
(``my-invoices`` auto-servicio del huésped, ``folios/categories`` catálogo)
siguen funcionando SIN prop_id.
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
    for code in ("billing.read", "billing.manage", "check-outs.manage", "account.read"):
        db.permissions.insert_one(
            {"permission_code": code, "description": code, "is_system": True,
             "created_at": _now(), "updated_at": _now()}
        )


def _seed_user(db, *, username: str, role: str, permissions: list[str],
               assigned_hotels: list[int] | None = None) -> dict[str, str]:
    """Rol GLOBAL (legacy) con *permissions* — SIN role_assignment por defecto."""
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
            "name": "rol_hotel_billing",
            "display_name": "Rol Hotel Billing",
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
async def global_cajero(client, db):
    """Rol GLOBAL con billing.read, SIN role_assignment (el hueco pre-E)."""
    _seed_catalog(db)
    creds = _seed_user(db, username="cajero_global", role="cajero",
                       permissions=["billing.read"], assigned_hotels=[1])
    await _login(client, creds)
    return creds


@pytest_asyncio.fixture
async def hotel_cajero(client, db, global_cajero):
    role_id = _seed_hotel_role(db, permissions=["billing.read"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_cajero["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_cajero


@pytest_asyncio.fixture
async def hotel_emisor_checkout(client, db, global_cajero):
    """Hotel role con SOLO check-outs.manage: pasa el combo de emisión fiscal
    (billing.manage O check-outs.manage) pero no billing.read."""
    role_id = _seed_hotel_role(db, permissions=["check-outs.manage"])
    db.role_assignments.insert_one(
        {"user_id": ObjectId(global_cajero["user_id"]), "prop_id": 1, "role_id": role_id}
    )
    return global_cajero


class TestBillingPropGate:
    """Operación de facturación = por hotel (rol global sin asignación → 403)."""

    @pytest.mark.asyncio
    async def test_list_invoices_403_global_role_without_assignment(self, client, global_cajero):
        resp = await client.get("/api/billing/invoices", params={"prop_id": 1})
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_list_invoices_400_without_prop_id(self, client, db, admin_user):
        await _login(client, admin_user)
        resp = await client.get("/api/billing/invoices")
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_list_invoices_200_with_hotel_role(self, client, hotel_cajero):
        resp = await client.get("/api/billing/invoices", params={"prop_id": 1})
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_invoice_detail_404_of_another_hotel(self, client, db, hotel_cajero):
        invoice_id = db.reservation_invoices.insert_one(
            {
                "booking_id": "BK-OTRO-HOTEL-1",
                "prop_id": 2,
                "status": "issued",
                "subtotal": 100.0,
                "taxes": 18.0,
                "total": 118.0,
                "issued_at": _now(),
            }
        ).inserted_id
        resp = await client.get(f"/api/billing/invoices/{invoice_id}", params={"prop_id": 1})
        assert resp.status_code == 404, resp.text

    @pytest.mark.asyncio
    async def test_create_invoice_403_without_either_combo_code(self, client, hotel_cajero):
        """billing.read NO alcanza para emitir: el combo exige billing.manage
        O check-outs.manage."""
        resp = await client.post(
            "/api/billing/invoices?prop_id=1",
            json={"booking_id": "BK-INEXISTENTE", "subtotal": 100.0},
        )
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_create_invoice_passes_with_only_second_combo_code(self, client, hotel_emisor_checkout):
        """El combo require_any_prop_permission deja pasar al usuario con SOLO
        check-outs.manage: la dependencia pasa y el 400 viene del negocio
        (reserva inválida), nunca 403 del gate."""
        resp = await client.post(
            "/api/billing/invoices?prop_id=1",
            json={"booking_id": "BK-INEXISTENTE", "subtotal": 100.0},
        )
        assert resp.status_code == 400, resp.text
        assert "No se pudo crear la factura" in resp.text

    @pytest.mark.asyncio
    async def test_my_invoices_stays_global_exception(self, client, db):
        """Auto-servicio del huésped: account.read global basta SIN prop_id."""
        _seed_catalog(db)
        creds = _seed_user(db, username="huesped_billing", role="cliente",
                           permissions=["account.read"])
        await _login(client, creds)
        resp = await client.get("/api/billing/my-invoices")
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_my_invoice_detail_200_own_invoice(self, client, db):
        """Detalle self-service: account.read global + factura de una reserva
        del usuario → 200 SIN prop_id (excepción global documentada)."""
        _seed_catalog(db)
        creds = _seed_user(db, username="huesped_detalle", role="cliente",
                           permissions=["account.read"])
        user_id = ObjectId(creds["user_id"])
        booking_id = "BK-HUESPED-OWN"
        db.booking_orders.insert_one(
            {"booking_id": booking_id, "prop_id": 1, "user_id": user_id,
             "guest_name": "Huesped", "status": "confirmed", "created_at": _now()}
        )
        invoice_id = db.reservation_invoices.insert_one(
            {"booking_id": booking_id, "prop_id": 1, "invoice_number": "INV-OWN-1",
             "status": "issued", "subtotal": 100.0, "taxes": 18.0, "total": 118.0,
             "issued_at": _now()}
        ).inserted_id
        await _login(client, creds)
        resp = await client.get(f"/api/billing/my-invoices/{invoice_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["invoice_number"] == "INV-OWN-1"

    @pytest.mark.asyncio
    async def test_my_invoice_detail_403_other_user_invoice(self, client, db):
        """Un huésped NO ve facturas de reservas ajenas (self-scoped)."""
        _seed_catalog(db)
        creds = _seed_user(db, username="huesped_ajeno", role="cliente",
                           permissions=["account.read"])
        other = _seed_user(db, username="otro_huesped", role="cliente",
                           permissions=["account.read"])
        other_id = ObjectId(other["user_id"])
        booking_id = "BK-OTRO-USER"
        db.booking_orders.insert_one(
            {"booking_id": booking_id, "prop_id": 1, "user_id": other_id,
             "guest_name": "Otro", "status": "confirmed", "created_at": _now()}
        )
        invoice_id = db.reservation_invoices.insert_one(
            {"booking_id": booking_id, "prop_id": 1, "invoice_number": "INV-OTHER-1",
             "status": "issued", "subtotal": 100.0, "taxes": 18.0, "total": 118.0,
             "issued_at": _now()}
        ).inserted_id
        await _login(client, creds)
        resp = await client.get(f"/api/billing/my-invoices/{invoice_id}")
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_folios_categories_stays_global_exception(self, client, global_cajero):
        """Catálogo de referencia: billing.read global basta SIN prop_id."""
        resp = await client.get("/api/billing/folios/categories")
        assert resp.status_code == 200, resp.text
