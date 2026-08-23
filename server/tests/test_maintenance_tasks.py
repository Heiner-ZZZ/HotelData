"""Tests for maintenance_tasks CRUD with room_id as foreign key.

Covers create, list, update, complete and delete endpoints under
/api/housekeeping/maintenance. Every test uses room_id (hotel_room_id)
instead of room_label as the primary room reference.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Helpers ──


async def _login_admin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"identifier": "admin_test", "password": "AdminPass123!"},
    )
    assert response.status_code == 200


def _seed_room(db, *, hotel_room_id: str = "HR-1-101", room_label: str = "101") -> str:
    db.hotel_rooms.insert_one(
        {
            "hotel_room_id": hotel_room_id,
            "prop_id": 1,
            "room_number": room_label,
            "room_label": room_label,
            "room_type_id": "RT-1-standard",
            "room_type_name": "Standard",
            "floor": 1,
            "is_active": True,
        }
    )
    return hotel_room_id


# ── Fixtures ──


@pytest_asyncio.fixture
async def logged_client(client: AsyncClient, admin_user):
    await _login_admin(client)
    return client


@pytest.fixture
def room_id(db):
    return _seed_room(db)


@pytest.fixture
def other_room_id(db):
    return _seed_room(db, hotel_room_id="HR-1-102", room_label="102")


# ── Tests ──


async def test_create_maintenance_with_room_id(logged_client: AsyncClient, room_id: str):
    payload = {
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "preventive",
        "title": "Revisión HVAC",
        "description": "Test maintenance",
        "priority": "high",
        "scheduled_date": "2026-07-22",
        "auto_block": True,
        "status": "scheduled",
    }
    response = await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["roomId"] == room_id
    assert data["roomLabel"] == "101"
    assert data["roomNumber"] == "101"
    assert data["roomTypeId"] == "RT-1-standard"
    assert data["taskType"] == "preventive"
    assert data["title"] == "Revisión HVAC"
    assert data["status"] == "scheduled"
    assert data["propId"] == 1


async def test_create_maintenance_rejects_unknown_room_id(logged_client: AsyncClient):
    payload = {
        "prop_id": 1,
        "room_id": "HR-1-999",
        "task_type": "preventive",
        "title": "Revisión HVAC",
    }
    response = await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json=payload)
    assert response.status_code == 400
    assert "Habitación no encontrada" in response.json().get("detail", "")


async def test_list_maintenance_returns_room_id(logged_client: AsyncClient, room_id: str):
    await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "preventive",
        "title": "Revisión HVAC",
    })

    response = await logged_client.get("/api/housekeeping/maintenance?prop_id=1")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["roomId"] == room_id
    assert item["roomLabel"] == "101"


async def test_update_maintenance_changes_room_id(
    logged_client: AsyncClient, room_id: str, other_room_id: str
):
    create_response = await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "preventive",
        "title": "Revisión HVAC",
    })
    task_id = create_response.json()["id"]

    update_payload = {
        "prop_id": 1,
        "room_id": other_room_id,
        "task_type": "corrective",
        "title": "Revisión HVAC actualizada",
        "description": "Updated description",
        "priority": "urgent",
        "scheduled_date": "2026-07-23",
        "auto_block": False,
        "status": "in_progress",
    }
    response = await logged_client.put(f"/api/housekeeping/maintenance/{task_id}?prop_id=1", json=update_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["roomId"] == other_room_id
    assert data["roomLabel"] == "102"
    assert data["taskType"] == "corrective"
    assert data["priority"] == "urgent"
    assert data["status"] == "in_progress"


async def test_update_maintenance_rejects_invalid_room_id(
    logged_client: AsyncClient, room_id: str
):
    create_response = await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "preventive",
        "title": "Revisión HVAC",
    })
    task_id = create_response.json()["id"]

    response = await logged_client.put(f"/api/housekeeping/maintenance/{task_id}?prop_id=1", json={
        "prop_id": 1,
        "room_id": "HR-1-999",
        "task_type": "preventive",
        "title": "Revisión HVAC",
        "status": "scheduled",
    })
    assert response.status_code == 400
    assert "Habitación no encontrada" in response.json().get("detail", "")


async def test_complete_maintenance(logged_client: AsyncClient, room_id: str):
    create_response = await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "preventive",
        "title": "Revisión HVAC",
    })
    task_id = create_response.json()["id"]

    response = await logged_client.post(f"/api/housekeeping/maintenance/{task_id}/complete?prop_id=1", json={"note": "Done"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["completedAt"] is not None


async def test_delete_maintenance(logged_client: AsyncClient, room_id: str):
    create_response = await logged_client.post("/api/housekeeping/maintenance?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "preventive",
        "title": "Revisión HVAC",
    })
    task_id = create_response.json()["id"]

    response = await logged_client.delete(f"/api/housekeeping/maintenance/{task_id}?prop_id=1")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    list_response = await logged_client.get("/api/housekeeping/maintenance?prop_id=1")
    assert list_response.json()["total"] == 0
