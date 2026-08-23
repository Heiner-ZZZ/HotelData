"""Tests for housekeeping_tasks CRUD with room_id as foreign key.

Covers create, list, update, complete and delete endpoints under
/api/housekeeping/tasks. Every test uses room_id (hotel_room_id)
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


async def test_create_task_with_room_id(logged_client: AsyncClient, room_id: str):
    payload = {
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "cleaning",
        "assigned_to": "María",
        "priority": "high",
        "note": "Test task",
        "scheduled_date": "2026-07-22",
    }
    response = await logged_client.post("/api/housekeeping/tasks?prop_id=1", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["roomId"] == room_id
    assert data["roomLabel"] == "101"
    assert data["roomNumber"] == "101"
    assert data["roomTypeId"] == "RT-1-standard"
    assert data["taskType"] == "cleaning"
    assert data["status"] == "pending"
    assert data["assignedTo"] == "María"
    assert data["propId"] == 1


async def test_create_task_rejects_unknown_room_id(logged_client: AsyncClient):
    payload = {
        "prop_id": 1,
        "room_id": "HR-1-999",
        "task_type": "cleaning",
    }
    response = await logged_client.post("/api/housekeeping/tasks?prop_id=1", json=payload)
    assert response.status_code == 400
    assert "Habitación no encontrada" in response.json().get("detail", "")


async def test_list_tasks_returns_room_id(logged_client: AsyncClient, room_id: str):
    await logged_client.post("/api/housekeeping/tasks?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "cleaning",
    })

    response = await logged_client.get("/api/housekeeping/tasks?prop_id=1")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["roomId"] == room_id
    assert item["roomLabel"] == "101"


async def test_update_task_changes_room_id(
    logged_client: AsyncClient, room_id: str, other_room_id: str
):
    create_response = await logged_client.post("/api/housekeeping/tasks?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "cleaning",
    })
    task_id = create_response.json()["id"]

    update_payload = {
        "prop_id": 1,
        "room_id": other_room_id,
        "task_type": "deep_clean",
        "assigned_to": "Pedro",
        "priority": "urgent",
        "note": "Updated note",
        "scheduled_date": "2026-07-23",
        "status": "pending",
    }
    response = await logged_client.put(f"/api/housekeeping/tasks/{task_id}?prop_id=1", json=update_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["roomId"] == other_room_id
    assert data["roomLabel"] == "102"
    assert data["taskType"] == "deep_clean"
    assert data["assignedTo"] == "Pedro"
    assert data["priority"] == "urgent"


async def test_update_task_rejects_invalid_room_id(
    logged_client: AsyncClient, room_id: str
):
    create_response = await logged_client.post("/api/housekeeping/tasks?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "cleaning",
    })
    task_id = create_response.json()["id"]

    response = await logged_client.put(f"/api/housekeeping/tasks/{task_id}?prop_id=1", json={
        "prop_id": 1,
        "room_id": "HR-1-999",
        "task_type": "cleaning",
        "status": "pending",
    })
    assert response.status_code == 400
    assert "Habitación no encontrada" in response.json().get("detail", "")


async def test_complete_task(logged_client: AsyncClient, room_id: str):
    create_response = await logged_client.post("/api/housekeeping/tasks?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "cleaning",
    })
    task_id = create_response.json()["id"]

    response = await logged_client.post(f"/api/housekeeping/tasks/{task_id}/complete?prop_id=1", json={"note": "Done"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["completedAt"] is not None


async def test_delete_task(logged_client: AsyncClient, room_id: str):
    create_response = await logged_client.post("/api/housekeeping/tasks?prop_id=1", json={
        "prop_id": 1,
        "room_id": room_id,
        "task_type": "cleaning",
    })
    task_id = create_response.json()["id"]

    response = await logged_client.delete(f"/api/housekeeping/tasks/{task_id}?prop_id=1")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    list_response = await logged_client.get("/api/housekeeping/tasks?prop_id=1")
    assert list_response.json()["total"] == 0
