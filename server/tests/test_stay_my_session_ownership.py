"""Ownership guard for ``POST /api/stay/my-session``.

The 2026-08 audit found a CRITICAL authorization bug in this endpoint. The
owner check was::

    is_owner = guest_email == user_email or booking.get("booking_id") == booking_id

The second operand is tautologically ``True`` (the booking was found *by* that
``booking_id``), so ``is_owner`` was always true and the 403 branch was dead
code. Any authenticated user holding ``reservations.read`` (the ``cliente``
role included) could mint a guest-portal session token for ANY checked-in
booking — hijacking the guest portal (chat, service requests, lost & found)
and leaking guest PII (name, room label, dates).

These tests pin the canonical behavior end-to-end:
1. The OWNER (cliente A) can create their session → 200.
2. A DIFFERENT client (cliente B) is denied → 403.
3. ``super_admin`` still bypasses via the staff role gate → 200.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from tests.conftest import _seed_user

CLIENTE_ROLE_PERMISSIONS = ["account.read", "account.update", "reservations.read"]


def _seed_cliente_role(db) -> ObjectId:
    """Seed the canonical ``cliente`` role so ``require_permission`` resolves."""
    role = db.roles.find_one({"role_name": "cliente"})
    if role:
        return role["_id"]
    return db.roles.insert_one(
        {
            "role_name": "cliente",
            "display_name": "Cliente",
            "permissions": CLIENTE_ROLE_PERMISSIONS,
            "is_system": True,
        }
    ).inserted_id


def _seed_booking(db, *, user_id: ObjectId, booking_id: str, guest_email: str, prop_id: int = 999) -> str:
    """Insert a checked-in booking owned by ``user_id``; returns its booking_id."""
    db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {"$set": {"hotel_name": "Test Hotel", "display_name": "Test Hotel"}},
        upsert=True,
    )
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "user_id": user_id,
            "prop_id": prop_id,
            "guest_name": "Guest A",
            "guest_email": guest_email,
            "status": "confirmed",
            "stay_status": "checked_in",
            "total_price": 120.0,
            "total_nights": 2,
            "assigned_rooms": ["HR-999-1"],
            "created_at": datetime.now(timezone.utc),
        }
    )
    return booking_id


async def _login(client, identifier: str, password: str) -> int:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
    )
    return resp.status_code


async def _request_session(client, booking_id: str, prop_id: int = 999) -> tuple[int, dict]:
    resp = await client.post(
        "/api/stay/my-session",
        params={"prop_id": prop_id},
        json={"booking_id": booking_id},
    )
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


class TestMySessionOwnership:
    """POST /api/stay/my-session must never mint a session for someone else's booking."""

    @pytest.mark.asyncio
    async def test_owner_gets_own_session(self, client, db, cliente_user):
        """The booking owner can create their session → 200 with a token."""
        _seed_cliente_role(db)
        booking_id = _seed_booking(
            db,
            user_id=ObjectId(cliente_user["user_id"]),
            booking_id="BK-MYSESS-OWNER",
            guest_email=cliente_user["email"],
        )

        assert await _login(client, cliente_user["username"], cliente_user["password"]) == 200
        status, body = await _request_session(client, booking_id)

        assert status == 200, f"owner must get their session, got {status}: {body}"
        assert body.get("booking_id") == booking_id
        assert body.get("token"), "a stay-session token must be minted for the owner"

    @pytest.mark.asyncio
    async def test_other_client_is_forbidden(self, client, db, cliente_user):
        """A different client asking for client A's booking must get 403.

        This is the regression that failed the audit: the tautological
        ``booking_id == booking_id`` OR made ``is_owner`` always true, so
        cliente B received the session token for cliente A's stay.
        """
        _seed_cliente_role(db)
        booking_id = _seed_booking(
            db,
            user_id=ObjectId(cliente_user["user_id"]),
            booking_id="BK-MYSESS-VICTIM",
            guest_email=cliente_user["email"],
        )
        # Client B — same role, different account, no relation to the booking.
        client_b = _seed_user(
            db,
            username="cliente_b",
            email="cliente_b@test.com",
            password="SecretB123!",
            role="cliente",
        )

        assert await _login(client, client_b["username"], client_b["password"]) == 200
        status, body = await _request_session(client, booking_id)

        assert status == 403, (
            f"cliente B must NOT obtain a session for cliente A's booking; "
            f"got {status} (a 200 here is the tautological-OR authorization bug): {body}"
        )
        assert body.get("detail") == "No tienes acceso a esta reserva."

    @pytest.mark.asyncio
    async def test_super_admin_staff_can_access_any_booking(self, client, db, admin_user, cliente_user):
        """super_admin (``*.*``) still bypasses ownership via the staff gate → 200."""
        _seed_cliente_role(db)
        booking_id = _seed_booking(
            db,
            user_id=ObjectId(cliente_user["user_id"]),
            booking_id="BK-MYSESS-STAFF",
            guest_email=cliente_user["email"],
        )

        assert await _login(client, admin_user["username"], admin_user["password"]) == 200
        status, body = await _request_session(client, booking_id)

        assert status == 200, f"super_admin must bypass ownership, got {status}: {body}"
        assert body.get("booking_id") == booking_id

    @pytest.mark.asyncio
    async def test_recepcionista_with_manage_can_access_any_booking(self, client, db, cliente_user):
        """Front-desk staff holding ``reservations.manage`` can open any stay.

        Pins the staff gate as PERMISSION-based (PBAC), not a hardcoded role
        list: the reservation-detail modal calls ``my-session`` to open the
        guest portal, and ``recepcionista`` holds ``reservations.manage`` in
        the canonical catalog. A role-list gate (super_admin/hotel_partner/…)
        would 403 them — a regression vs the pre-fix tautology.
        """
        db.roles.insert_one(
            {
                "role_name": "recepcionista",
                "display_name": "Recepcionista",
                "permissions": ["reservations.manage", "reservations.read"],
                "is_system": True,
            }
        )
        booking_id = _seed_booking(
            db,
            user_id=ObjectId(cliente_user["user_id"]),
            booking_id="BK-MYSESS-RECEPCION",
            guest_email=cliente_user["email"],
        )
        recepcionista = _seed_user(
            db,
            username="recepcion_test",
            email="recepcion@test.com",
            password="Recep123!",
            role="recepcionista",
        )
        # Migración E: la recepción necesita scope por-hotel (assigned_hotels)
        # + role_assignment con el rol del hotel que porta reservations.*.
        db.users.update_one(
            {"_id": ObjectId(recepcionista["user_id"])},
            {"$set": {"assigned_hotels": [999]}},
        )
        hotel_role_id = db.hotel_roles.insert_one(
            {
                "prop_id": 999,
                "name": "recepcionista",
                "display_name": "Recepcionista",
                "permissions": ["reservations.manage", "reservations.read"],
                "is_active": True,
            }
        ).inserted_id
        db.role_assignments.insert_one(
            {"user_id": ObjectId(recepcionista["user_id"]), "prop_id": 999, "role_id": hotel_role_id}
        )

        assert await _login(client, recepcionista["username"], recepcionista["password"]) == 200
        status, body = await _request_session(client, booking_id)

        assert status == 200, (
            f"staff with reservations.manage must open a guest's stay, got {status}: {body}"
        )

    @pytest.mark.asyncio
    async def test_legacy_booking_without_user_id_owner_email_gets_session(self, client, db, cliente_user):
        """Legacy bookings (pre-FK migration, no ``user_id``) still resolve via
        the email ownership fallback — the owner must not be locked out."""
        _seed_cliente_role(db)
        # No ``user_id`` field — simulates a booking created before the FK
        # migration where email is the only ownership signal.
        db.dim_hotels.update_one(
            {"prop_id": 998},
            {"$set": {"hotel_name": "Test Hotel", "display_name": "Test Hotel"}},
            upsert=True,
        )
        db.booking_orders.insert_one(
            {
                "booking_id": "BK-MYSESS-LEGACY",
                "prop_id": 998,
                "guest_name": "Guest Legacy",
                "guest_email": cliente_user["email"],
                "status": "confirmed",
                "stay_status": "checked_in",
                "total_price": 90.0,
                "total_nights": 1,
                "assigned_rooms": ["HR-998-1"],
                "created_at": datetime.now(timezone.utc),
            }
        )

        assert await _login(client, cliente_user["username"], cliente_user["password"]) == 200
        status, body = await _request_session(client, "BK-MYSESS-LEGACY", prop_id=998)

        assert status == 200, f"owner email fallback must work, got {status}: {body}"
        assert body.get("token"), "owner must receive a session token via the email fallback"
