"""Fase A — Gates operativos del hotel pendiente de aprobación.

Design: `docs/APROBACION_HOTELES_Y_PRICING.md` §4. Un hotel creado por el
onboarding público nace con ``published=false`` / ``is_operational=false``
hasta que el super admin lo aprueba en la cola. Estas pruebas verifican que:

1. La búsqueda pública (`/api/hotels/search`) NO incluye hoteles no publicados.
2. La búsqueda de disponibilidad pública NO los incluye.
3. El detalle público devuelve 404 para un hotel no publicado (no filtra su
   existencia).
4. ``similar`` y ``compare`` públicos tampoco los exponen.
5. Las operaciones autenticadas por prop_id (``require_prop_permission``)
   devuelven 403 si el hotel existe pero NO está operativo.

Backward compat: los hoteles legados SIN el campo ``published`` siguen
visibles (el campo ausente se trata como publicado).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from passlib.context import CryptContext

from src.app.modules.hotels.service.availability import search_available_hotels
from src.app.modules.hotels.service.search import search_hotels

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_hotel(db, *, prop_id: int, name: str, published=None) -> None:
    """Seed a dim_hotels row. `published=None` simula un hotel legado (sin campo)."""
    doc: dict = {
        "prop_id": prop_id,
        "hotel_name": name,
        "display_name": name,
        "prop_starrating": 4.0,
        "prop_review_score": 8.5,
        "created_at": _now(),
    }
    if published is not None:
        doc["published"] = published
    db.dim_hotels.insert_one(doc)


def _seed_fact(db, prop_id: int) -> None:
    db.fact_hotel_reservations.insert_one(
        {
            "prop_id": prop_id,
            "price_usd": 100.0,
            "click_bool": 1,
            "reserva_bool": 1,
            "promotion_flag": 0,
        }
    )


# ── Búsqueda pública /api/hotels/search ──────────────────────────────


async def test_search_excludes_unpublished_hotel(db):
    """Un hotel published=false no aparece en la búsqueda pública."""
    _seed_hotel(db, prop_id=9001, name="Hotel Publicado", published=True)
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    _seed_fact(db, 9001)
    _seed_fact(db, 9002)

    result = search_hotels({}, page=1, page_size=10)
    prop_ids = [item["prop_id"] for item in result["items"]]
    assert 9001 in prop_ids
    assert 9002 not in prop_ids


async def test_search_legacy_hotel_without_published_field_still_visible(db):
    """Backward compat: un hotel legado sin el campo `published` sigue visible."""
    _seed_hotel(db, prop_id=9001, name="Hotel Legado")  # sin published
    _seed_fact(db, 9001)

    result = search_hotels({}, page=1, page_size=10)
    assert 9001 in [item["prop_id"] for item in result["items"]]


async def test_search_empty_when_no_published_hotels(db):
    """Si el único hotel con datos es no publicado, la búsqueda queda vacía."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    _seed_fact(db, 9002)

    result = search_hotels({}, page=1, page_size=10)
    assert result["total"] == 0
    assert result["items"] == []


# ── Búsqueda de disponibilidad /api/hotels/availability ──────────────


async def test_availability_excludes_unpublished_hotel(db):
    """La búsqueda de disponibilidad (sin fechas) excluye hoteles no publicados."""
    _seed_hotel(db, prop_id=9001, name="Hotel Publicado", published=True)
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)

    result = search_available_hotels()
    prop_ids = [item["prop_id"] for item in result["items"]]
    assert 9001 in prop_ids
    assert 9002 not in prop_ids


# ── Detalle público /api/hotels/{prop_id} ────────────────────────────


async def test_detail_returns_200_for_published_hotel(client: AsyncClient, db):
    _seed_hotel(db, prop_id=9001, name="Hotel Publicado", published=True)
    resp = await client.get("/api/hotels/9001")
    assert resp.status_code == 200


async def test_detail_returns_404_for_unpublished_hotel(client: AsyncClient, db):
    """404 (no filtra la existencia): un hotel pendiente no es consultable en público."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    resp = await client.get("/api/hotels/9002")
    assert resp.status_code == 404


# ── Similar /api/hotels/{prop_id}/similar ────────────────────────────


async def test_similar_empty_for_unpublished_source(client: AsyncClient, db):
    """El hotel fuente no publicado no genera recomendaciones."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    _seed_hotel(db, prop_id=9001, name="Hotel Publicado", published=True)

    resp = await client.get("/api/hotels/9002/similar")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── Compare /api/hotels/compare ──────────────────────────────────────


async def test_compare_excludes_unpublished_hotel(client: AsyncClient, db):
    _seed_hotel(db, prop_id=9001, name="Hotel Publicado", published=True)
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)

    resp = await client.get(
        "/api/hotels/compare",
        params=[("prop_id", "9001"), ("prop_id", "9002")],
    )
    assert resp.status_code == 200
    prop_ids = [item["prop_id"] for item in resp.json()["items"]]
    assert 9001 in prop_ids
    assert 9002 not in prop_ids


# ── Operaciones autenticadas por prop_id (require_prop_permission) ───


async def test_prop_permission_403_for_unpublished_hotel(client: AsyncClient, db):
    """Operar sobre un hotel existente pero NO operativo → 403 con mensaje claro."""
    prop_id = 9002
    _seed_hotel(db, prop_id=prop_id, name="Hotel Pendiente", published=False)

    # Catálogo + plantilla + rol de hotel (misma forma que test_hotel_permissions_api).
    db.permissions.insert_one(
        {
            "permission_code": "hotel.manage_roles",
            "description": "hotel.manage_roles",
            "is_system": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    template_id = db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": ["hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    hotel_role_id = db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": "gerente_hotel",
            "display_name": "Gerente Hotel 9002",
            "permissions": ["hotel.manage_roles"],
            "based_on_role_id": template_id,
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    user_id = db.users.insert_one(
        {
            "username": "gerente9002",
            "email": "gerente9002@hotel.local",
            "display_name": "Gerente 9002",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "gerente_hotel",
            "role_ids": [],
            "assigned_hotels": [prop_id],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": prop_id,
            "role_id": hotel_role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )

    resp = await client.post(
        "/api/auth/login", json={"identifier": "gerente9002", "password": "Pass123!"}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/management/hotels/{prop_id}/roles")
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


async def test_prop_permission_ok_for_operational_hotel(client: AsyncClient, db):
    """Control: un hotel operativo (publicado) sí admite operaciones."""
    prop_id = 9001
    _seed_hotel(db, prop_id=prop_id, name="Hotel Publicado", published=True)

    db.permissions.insert_one(
        {
            "permission_code": "hotel.manage_roles",
            "description": "hotel.manage_roles",
            "is_system": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    template_id = db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": ["hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    hotel_role_id = db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": "gerente_hotel",
            "display_name": "Gerente Hotel 9001",
            "permissions": ["hotel.manage_roles"],
            "based_on_role_id": template_id,
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    user_id = db.users.insert_one(
        {
            "username": "gerente9001",
            "email": "gerente9001@hotel.local",
            "display_name": "Gerente 9001",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "gerente_hotel",
            "role_ids": [],
            "assigned_hotels": [prop_id],
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": prop_id,
            "role_id": hotel_role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )

    resp = await client.post(
        "/api/auth/login", json={"identifier": "gerente9001", "password": "Pass123!"}
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/management/hotels/{prop_id}/roles")
    assert resp.status_code == 200
