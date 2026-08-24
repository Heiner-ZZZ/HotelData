"""Regression tests for availability blackout deletion."""
from __future__ import annotations

import pytest
from bson import ObjectId

from tests.conftest import login


@pytest.mark.asyncio
async def test_delete_blackout_reverses_inventory_and_returns_success(client, db, admin_user):
    blackout_id = ObjectId("6a5fc805a7ffc4ee07aebe79")
    db.blackout_dates.insert_one({
        "_id": blackout_id,
        "prop_id": 1,
        "room_type_id": "RT-BLACKOUT",
        "start_date": "2026-09-10",
        "end_date": "2026-09-11",
        "reason": "Mantenimiento",
        # Legacy records can contain numeric values serialized as strings.
        "blocked_rooms": "2",
        "room_numbers": ["101", "102"],
    })
    for date in ("2026-09-10", "2026-09-11"):
        db.room_inventory_calendar.insert_one({
            "prop_id": 1,
            "room_type_id": "RT-BLACKOUT",
            "date": date,
            "total_rooms": 5,
            "blocked_rooms": 2,
            "available_rooms": 3,
        })

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    response = await client.delete(f"/api/management/availability/blackouts/{blackout_id}?prop_id=1")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "blackout_id": str(blackout_id),
        "deleted": True,
        "prop_id": 1,
    }
    assert db.blackout_dates.find_one({"_id": blackout_id}) is None
    for date in ("2026-09-10", "2026-09-11"):
        calendar = db.room_inventory_calendar.find_one({
            "prop_id": 1,
            "room_type_id": "RT-BLACKOUT",
            "date": date,
        })
        assert calendar["blocked_rooms"] == 0
        assert calendar["available_rooms"] == 5


@pytest.mark.asyncio
async def test_delete_maintenance_blackout_without_room_type_succeeds(client, db, admin_user):
    """Housekeeping maintenance writes blackout_dates docs with a different
    shape (hotel_room_id/room_label, no room_type_id/blocked_rooms). The
    availability list shows them too, so DELETE must remove them without
    leaking a KeyError as a 500 — and must skip the room-type inventory
    reversal, which does not apply to that schema.
    """
    blackout_id = ObjectId("6a8b8f5d71b798aef0a2d206")
    db.blackout_dates.insert_one({
        "_id": blackout_id,
        "prop_id": 1,
        "room_label": "100",
        "hotel_room_id": "HR-1-100",
        "start_date": "2026-06-29T17:26",
        "end_date": "2026-06-29T17:26",
        "source": "maintenance",
        "reason": "Mantenimiento programado",
    })

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    response = await client.delete(f"/api/management/availability/blackouts/{blackout_id}?prop_id=1")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "blackout_id": str(blackout_id),
        "deleted": True,
        "prop_id": 1,
    }
    assert db.blackout_dates.find_one({"_id": blackout_id}) is None
