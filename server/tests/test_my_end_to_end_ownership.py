"""End-to-end cross-user ownership regression for all client ``my-*`` flows.

Client B must never receive client A's operational data.  The test uses the
real FastAPI app, session login, and MongoDB test database rather than calling
services directly, so it protects the API boundaries together.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from src.app.modules.billing.schemas import InvoiceCreate
from passlib.context import CryptContext

from src.app.modules.billing.service.lifecycle import create_invoice


_PASSWORDS = CryptContext(schemes=["bcrypt"], deprecated="auto")


CLIENT_ROLE_PERMISSIONS = [
    "account.read",
    "account.update",
    "reservations.read",
    "hr.read",
]


def _seed_user_b(db, *, username: str, email: str, password: str, role: str) -> dict[str, str]:
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": email,
            "display_name": username,
            "password_hash": _PASSWORDS.hash(password),
            "primary_role": role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id
    return {"user_id": str(user_id), "username": username, "email": email, "password": password}


def _seed_cliente_role(db) -> None:
    db.roles.insert_one(
        {
            "role_name": "cliente",
            "display_name": "Cliente",
            "permissions": CLIENT_ROLE_PERMISSIONS,
            "is_system": True,
        }
    )


def _seed_client_a_data(db, user_id: str, email: str) -> tuple[str, str]:
    """Create A's booking, invoice, employee profile, and favorite."""
    user_oid = ObjectId(user_id)
    booking_id = "BK-OWNERSHIP-A"
    db.dim_hotels.insert_one(
        {
            "prop_id": 999,
            "hotel_name": "Ownership Test Hotel",
            "display_name": "Ownership Test Hotel",
        }
    )
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "user_id": user_oid,
            "prop_id": 999,
            "status": "confirmed",
            "stay_status": "checked_in",
            "guest_name": "Cliente A",
            "guest_email": email,
            "check_in_date": "2026-09-01",
            "check_out_date": "2026-09-03",
            "total_nights": 2,
            "rooms": 1,
            "total_price": 220.0,
            "assigned_rooms": [],
            "created_at": datetime.now(timezone.utc),
        }
    )
    invoice = create_invoice(InvoiceCreate(booking_id=booking_id, subtotal=200.0, taxes=20.0))
    assert invoice is not None

    db.employees.insert_one(
        {
            "user_id": user_oid,
            "full_name": "Empleado A",
            "prop_id": 999,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    )
    db.user_favorites.insert_one(
        {
            "user_id": user_oid,
            "hotel_id": 999,
            "added_at": datetime.now(timezone.utc),
        }
    )
    return booking_id, str(invoice["id"])


@pytest.mark.asyncio
async def test_client_b_cannot_see_client_a_through_any_my_endpoint(client, db, cliente_user):
    """All five client self-service boundaries fail closed for client B."""
    _seed_cliente_role(db)
    booking_id, invoice_id = _seed_client_a_data(
        db,
        cliente_user["user_id"],
        cliente_user["email"],
    )
    client_b = _seed_user_b(
        db,
        username="ownership_client_b",
        email="ownership_b@test.com",
        password="ClientB123!",
        role="cliente",
    )

    # Positive control: the owner really sees each seeded resource. Without
    # this, an endpoint returning empty for everyone could falsely pass the
    # negative assertions below.
    owner_login = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert owner_login.status_code == 200, owner_login.text
    owner_reservations = await client.get("/api/reservations")
    assert owner_reservations.status_code == 200, owner_reservations.text
    assert owner_reservations.json()["total"] == 1
    owner_detail = await client.get(f"/api/reservations/{booking_id}")
    assert owner_detail.status_code == 200, owner_detail.text
    owner_invoices = await client.get("/api/billing/my-invoices")
    assert owner_invoices.status_code == 200, owner_invoices.text
    assert owner_invoices.json()["total"] == 1
    owner_favorites = await client.get("/api/account/favorites")
    assert owner_favorites.status_code == 200, owner_favorites.text
    assert owner_favorites.json()["favorites"] == [999]
    owner_portal = await client.get("/api/hr/my-portal")
    assert owner_portal.status_code == 200, owner_portal.text
    assert owner_portal.json()["employee_id"]
    owner_session = await client.post("/api/stay/my-session", json={"booking_id": booking_id})
    assert owner_session.status_code == 200, owner_session.text

    # Switch the same browser session to client B before the negative checks.
    login_response = await client.post(
        "/api/auth/login",
        json={"identifier": client_b["username"], "password": client_b["password"]},
    )
    assert login_response.status_code == 200, login_response.text
    current_user = await client.get("/api/auth/me")
    assert current_user.status_code == 200, current_user.text
    assert current_user.json()["user"]["username"] == client_b["username"]

    # 1. reservations: A's booking is not present in B's list.
    reservations = await client.get("/api/reservations")
    assert reservations.status_code == 200, reservations.text
    assert reservations.json()["total"] == 0
    assert reservations.json()["items"] == []
    # The detail route is also a client-facing reservation read boundary.
    reservation_detail = await client.get(f"/api/reservations/{booking_id}")
    assert reservation_detail.status_code == 403, reservation_detail.text

    # 2. my-invoices: invoice lookup joins through B's own ObjectId user_id.
    invoices = await client.get("/api/billing/my-invoices")
    assert invoices.status_code == 200, invoices.text
    assert invoices.json()["total"] == 0
    assert invoices.json()["items"] == []

    # 3. my-invoices/{id}/pay: knowing A's Mongo invoice id is not enough.
    payment = await client.post(f"/api/billing/my-invoices/{invoice_id}/pay")
    assert payment.status_code == 403, payment.text

    # 4. favorites: B gets B's collection slice, never A's favorite.
    favorites = await client.get("/api/account/favorites")
    assert favorites.status_code == 200, favorites.text
    assert favorites.json()["favorites"] == []

    # 5. my-portal: B cannot resolve A's employees.user_id backlink.
    portal = await client.get("/api/hr/my-portal")
    assert portal.status_code == 200, portal.text
    assert portal.json()["employee_id"] == ""

    # 6. my-session: the authenticated guest cannot mint A's stay token.
    session = await client.post("/api/stay/my-session", json={"booking_id": booking_id})
    assert session.status_code == 403, session.text
    assert session.json()["detail"] == "No tienes acceso a esta reserva."
