"""Guard: GET /api/reviews no expone filtros de staff ni salta el RBAC por hotel.

Antes del endurecimiento (auditoría de aislamiento my-*):
1. ``user_id`` y ``moderation_status`` eran filtros de staff alcanzables por
   cualquier usuario logueado (``require_login`` a secas): un cliente podía
   enumerar las reseñas de cualquier usuario por su id y ver estados de
   moderación (pending/rejected) que la vista pública no expone.
2. El ``prop_id`` explícito sobreescribía el filtro RBAC de
   ``hotel_filter_from_user``: un hotel_partner del hotel A podía consultar
   las reseñas del hotel B (cross-hotel).

Endurecimiento (rutas de reviews):
- ``user_id`` / ``moderation_status`` → exigen ``reviews.read`` (403 si no).
- ``prop_id`` → validado contra ``user_can_access_hotel`` (403 fuera de alcance),
  nunca reemplaza el alcance RBAC.
- Sin permiso staff y sin ``moderation_status`` → solo reseñas ``approved``
  (paridad con GET /api/hotels/{prop_id}/reviews).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId
from passlib.context import CryptContext

from src.app.modules.reservations.service._helpers import utc_now

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_PROP = 999


def _seed_extra_user(db, *, username: str, role: str, assigned_hotels: list[int] | None = None) -> dict:
    """Seed an extra user (beyond conftest's cliente_user/admin_user)."""
    user_id = db.users.insert_one({
        "username": username,
        "email": f"{username}@example.com",
        "display_name": username.replace("_", " ").title(),
        "password_hash": _pwd.hash("Extra123!"),
        "primary_role": role,
        "is_active": True,
        "assigned_hotels": assigned_hotels or [],
        "created_at": datetime.now(timezone.utc),
    }).inserted_id
    return {
        "user_id": str(user_id),
        "username": username,
        "email": f"{username}@example.com",
        "password": "Extra123!",
        "primary_role": role,
    }


def _seed_role(db, *, role_name: str, permissions: list[str]) -> None:
    db.roles.insert_one({
        "role_name": role_name,
        "display_name": role_name.replace("_", " ").title(),
        "permissions": permissions,
        "is_system": True,
    })


@pytest.fixture
def reviews_data(db, cliente_user):
    """Seed one approved + one pending review for TEST_PROP."""
    db.reviews.insert_one({
        "prop_id": TEST_PROP,
        "user_id": ObjectId(cliente_user["user_id"]),
        "rating": 5,
        "title": "Excelente",
        "comment": "Buen servicio",
        "moderation_status": "approved",
        "created_at": utc_now(),
    })
    db.reviews.insert_one({
        "prop_id": TEST_PROP,
        "user_id": ObjectId(cliente_user["user_id"]),
        "rating": 2,
        "title": "Mala",
        "comment": "Ruido",
        "moderation_status": "pending",
        "created_at": utc_now(),
    })


@pytest.mark.asyncio
async def test_client_cannot_filter_by_user_id(client, db, cliente_user, reviews_data):
    """Un cliente (sin reviews.read) no puede filtrar por user_id ajeno."""
    lr = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert lr.status_code == 200, lr.text

    resp = await client.get("/api/reviews", params={"user_id": cliente_user["user_id"]})
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_client_cannot_filter_by_moderation_status(client, db, cliente_user, reviews_data):
    """Un cliente no puede filtrar por estado de moderación (staff-only)."""
    lr = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert lr.status_code == 200, lr.text

    resp = await client.get("/api/reviews", params={"moderation_status": "pending"})
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_client_cannot_filter_by_empty_user_id(client, db, cliente_user, reviews_data):
    """El parámetro user_id vacío también es un filtro de staff (403)."""
    lr = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert lr.status_code == 200, lr.text

    resp = await client.get("/api/reviews", params={"user_id": ""})
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_restricted_partner_cannot_query_prop_outside_scope(client, db, reviews_data):
    """hotel_partner del hotel A no puede saltar el RBAC con prop_id del hotel B."""
    partner = _seed_extra_user(db, username="partner_test", role="hotel_partner", assigned_hotels=[1])

    lr = await client.post(
        "/api/auth/login",
        json={"identifier": partner["username"], "password": partner["password"]},
    )
    assert lr.status_code == 200, lr.text

    # prop_id=TEST_PROP (999) NO está en assigned_hotels=[1] → 403
    resp = await client.get("/api/reviews", params={"prop_id": TEST_PROP})
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_client_sees_only_approved_reviews(client, db, cliente_user, reviews_data):
    """Un cliente sin moderación explícita ve SOLO reseñas aprobadas (paridad pública)."""
    lr = await client.post(
        "/api/auth/login",
        json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
    )
    assert lr.status_code == 200, lr.text

    resp = await client.get("/api/reviews", params={"prop_id": TEST_PROP})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1, f"El cliente no debe ver la reseña pending, vio: {body}"
    assert body["items"][0]["moderation_status"] == "approved"


@pytest.mark.asyncio
async def test_staff_with_reviews_read_can_filter_by_moderation(client, db, reviews_data):
    """marketing_hotelero (reviews.read + alcance al hotel) filtra por moderación."""
    _seed_role(db, role_name="marketing_hotelero", permissions=["reviews.read", "reviews.moderate"])
    marketing = _seed_extra_user(
        db, username="marketing_test", role="marketing_hotelero", assigned_hotels=[TEST_PROP]
    )
    # Migración E: asignación por-hotel para que el gate prop de reseñas pase.
    hotel_role_id = db.hotel_roles.insert_one({
        "prop_id": TEST_PROP,
        "name": "marketing_hotelero",
        "display_name": "Marketing Hotelero",
        "permissions": ["reviews.read", "reviews.moderate"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }).inserted_id
    db.role_assignments.insert_one({
        "user_id": ObjectId(marketing["user_id"]),
        "role_id": hotel_role_id,
        "prop_id": TEST_PROP,
    })

    lr = await client.post(
        "/api/auth/login",
        json={"identifier": marketing["username"], "password": marketing["password"]},
    )
    assert lr.status_code == 200, lr.text

    resp = await client.get(
        "/api/reviews", params={"prop_id": TEST_PROP, "moderation_status": "pending"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["moderation_status"] == "pending"


@pytest.mark.asyncio
async def test_super_admin_can_query_any_prop(client, db, admin_user, reviews_data):
    """super_admin (rol sin filtro) conserva acceso a cualquier prop_id."""
    lr = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    assert lr.status_code == 200, lr.text

    resp = await client.get("/api/reviews", params={"prop_id": TEST_PROP})
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 2  # ve todas (approved + pending), es staff
