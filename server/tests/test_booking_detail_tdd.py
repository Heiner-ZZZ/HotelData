"""TDD reproduction for BK-20260827142115-6C3CC929 validation error.

Seam: HTTP API GET /api/reservations/{booking_id} and PATCH /api/reservations/{booking_id}
Expected: 200 with BookingResponse containing _id / id
Current: 400 with "1 validation error for BookingResponse _id Field required"
"""
import pytest
import pytest_asyncio
from bson import ObjectId
from tests._prop_gate_helpers import login, seed_catalog, seed_hotel, seed_hotel_role, seed_user

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def superadmin_with_hotel(client, db):
    # Use the existing superadmin fixture from conftest if available, else seed
    # We need a user with super_admin and access to prop 1
    seed_catalog(db, ["reservations.read", "reservations.update"])
    seed_hotel(db, 1)
    # Try to use existing superadmin, but ensure it has hotel access
    # Instead seed a fresh super_admin-like user
    creds = seed_user(db, username="superadmin_tdd", role="super_admin", permissions=["reservations.read", "reservations.update"], assigned_hotels=[1])
    # Also ensure role_assignment for prop 1
    role_id = seed_hotel_role(db, name="super_hotel_role", permissions=["reservations.read", "reservations.update"])
    db.role_assignments.insert_one({"user_id": ObjectId(creds["user_id"]), "prop_id": 1, "role_id": role_id})
    await login(client, creds)
    return creds

async def test_get_booking_detail_returns_200_with_id(client, db, superadmin_with_hotel):
    # Seed a booking similar to BK-20260827142115-6C3CC929
    booking_id = "BK-20260827142115-6C3CC929"
    # Clean any existing
    db.booking_orders.delete_many({"booking_id": booking_id})
    db.booking_orders.insert_one({
        "_id": ObjectId("6a9047dbe0f46f1368a5de10"),
        "booking_id": booking_id,
        "prop_id": 1,
        "user_id": ObjectId(superadmin_with_hotel["user_id"]),
        "status": "pending",
        "guest_name": "Test Guest",
        "guest_email": "test@example.com",
        "check_in_date": "2026-08-30",
        "check_out_date": "2026-08-31",
        "rooms": 1,
        "total_nights": 1,
        "total_price": 100.0,
        "currency": "USD",
        "created_at": "2026-08-27T14:21:15",
        "updated_at": "2026-08-27T14:21:15",
        "is_test": True,
        "booking_source": "web",
    })
    db.booking_guests.delete_many({"booking_id": booking_id})
    db.booking_guests.insert_one({"booking_id": booking_id, "guest_name": "Test Guest", "is_primary": True})
    db.booking_status_history.delete_many({"booking_id": booking_id})
    db.booking_status_history.insert_one({"booking_id": booking_id, "status": "pending", "changed_at": "2026-08-27T14:21:15", "reason": "initial", "changed_by": "test"})

    resp = await client.get(f"/api/reservations/{booking_id}", params={"prop_id": 1})
    print("GET status", resp.status_code)
    print("GET body", resp.text[:2000])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # BookingResponse should have id (from _id)
    assert "id" in data or "_id" in data
    assert data.get("booking_id") == booking_id

async def test_patch_booking_returns_200_with_id(client, db, superadmin_with_hotel):
    booking_id = "BK-20260827142115-6C3CC929"
    # Ensure booking exists (from previous test, but re-seed if needed)
    if not db.booking_orders.find_one({"booking_id": booking_id}):
        db.booking_orders.insert_one({
            "_id": ObjectId("6a9047dbe0f46f1368a5de10"),
            "booking_id": booking_id,
            "prop_id": 1,
            "user_id": ObjectId(superadmin_with_hotel["user_id"]),
            "status": "pending",
            "guest_name": "Test Guest",
            "guest_email": "test@example.com",
            "check_in_date": "2026-08-30",
            "check_out_date": "2026-08-31",
            "rooms": 1,
            "total_nights": 1,
            "total_price": 100.0,
            "currency": "USD",
            "created_at": "2026-08-27T14:21:15",
            "updated_at": "2026-08-27T14:21:15",
            "is_test": True,
        })
    resp = await client.patch(f"/api/reservations/{booking_id}", params={"prop_id": 1}, json={"comment": "nuevo comentario"})
    print("PATCH status", resp.status_code)
    print("PATCH body", resp.text[:3000])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "id" in data or "_id" in data
