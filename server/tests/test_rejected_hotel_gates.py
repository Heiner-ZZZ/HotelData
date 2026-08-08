"""Invariante del hotel rechazado: fuera de búsqueda pública y operaciones
durante la gracia de 7 días (docs/APROBACION_HOTELES_Y_PRICING.md §2/§9).

Un hotel rechazado es TERMINAL: debe quedar fuera de toda superficie pública
(búsqueda, detalle) y de toda operación (middleware + require_prop_permission)
INCLUSO mientras la cuenta del dueño sigue activa (gracia de
``REJECTION_GRACE_DAYS``, para que pueda ver el motivo en la app antes de la
desactivación).

El gate se apoya en ``published=false`` (mismo campo del gate operativo).
Este test fija el invariante: el ``reject`` debe FORZAR
``published=false`` / ``is_operational=false`` en ``dim_hotels``, sin depender
de que el onboarding los haya escrito — una regresión futura del onboarding
(que dejara la fila publicada) no puede dejar un hotel rechazado visible.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.hotels.service.search import search_hotels
from tests.conftest import login

pytestmark = pytest.mark.asyncio

_PENDING = "pending_approval"
_REJECTED = "rejected"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_registration(
    db,
    *,
    prop_id: int,
    hotel_status: str,
    published: bool,
    is_operational: bool,
) -> dict:
    """Siembra una fila de dim_hotels + su dueño (estado de aprobación alineado)."""
    owner_id = db.users.insert_one(
        {
            "username": f"dueno{prop_id}",
            "email": f"dueno{prop_id}@hotel.local",
            "display_name": f"Dueño {prop_id}",
            "password_hash": "unused",
            "primary_role": "hotel_partner",
            "role_ids": [],
            "assigned_hotels": [prop_id],
            "is_active": True,  # durante la gracia el dueño sigue activo
            "approval_status": hotel_status,
            "rejected_at": _now() if hotel_status == _REJECTED else None,
            "created_at": _now(),
        }
    ).inserted_id
    db.dim_hotels.insert_one(
        {
            "prop_id": prop_id,
            "hotel_name": f"Hotel {prop_id}",
            "display_name": f"Hotel {prop_id}",
            "prop_starrating": 3.5,
            "prop_review_score": 7.0,
            "owner_user_id": owner_id,
            "approval_status": hotel_status,
            "published": published,
            "is_operational": is_operational,
            "created_at": _now(),
        }
    )
    return {"owner_id": owner_id, "prop_id": prop_id}


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


async def _login_super_admin(client) -> None:
    assert await login(client, "admin_test", "AdminPass123!") == 200


# ── Estado del hotel rechazado durante la gracia (cuenta del dueño activa) ─


async def test_rejected_hotel_unpublished_while_owner_stays_active(client, db, admin_user):
    """El rechazo deja el hotel no publicado y no operativo MIENTRAS el dueño
    conserva is_active=true (gracia) — el gate no depende de la cuenta."""
    _seed_registration(
        db,
        prop_id=9102,
        hotel_status=_REJECTED,
        published=False,
        is_operational=False,
    )

    hotel = db.dim_hotels.find_one({"prop_id": 9102})
    assert hotel["approval_status"] == _REJECTED
    assert hotel["published"] is False
    assert hotel["is_operational"] is False
    owner = db.users.find_one({"_id": hotel["owner_user_id"]})
    assert owner["approval_status"] == _REJECTED
    assert owner["is_active"] is True  # gracia: puede ver el motivo


async def test_rejected_hotel_excluded_from_public_search(client, db, admin_user):
    """Búsqueda pública: el hotel rechazado (published=false) no aparece."""
    _seed_registration(
        db, prop_id=9102, hotel_status=_REJECTED, published=False, is_operational=False
    )
    _seed_registration(
        db, prop_id=9101, hotel_status="approved", published=True, is_operational=True
    )
    _seed_fact(db, 9102)
    _seed_fact(db, 9101)

    result = search_hotels({}, page=1, page_size=10)
    prop_ids = [item["prop_id"] for item in result["items"]]
    assert 9101 in prop_ids
    assert 9102 not in prop_ids


async def test_rejected_hotel_detail_returns_404(client, db, admin_user):
    """Detalle público: hotel rechazado → 404 (no filtra la existencia)."""
    _seed_registration(
        db, prop_id=9102, hotel_status=_REJECTED, published=False, is_operational=False
    )

    resp = await client.get("/api/hotels/9102")
    assert resp.status_code == 404


async def test_rejected_hotel_operations_403_during_grace(client, db, admin_user):
    """Operaciones legadas (query param, middleware): 403 "no está operativo"
    incluso para super admin y mientras la cuenta del dueño sigue activa."""
    _seed_registration(
        db, prop_id=9102, hotel_status=_REJECTED, published=False, is_operational=False
    )
    await _login_super_admin(client)

    resp = await client.get("/api/billing/invoices", params={"prop_id": 9102})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]

    resp = await client.get("/api/reservations", params={"prop_id": 9102})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


# ── Invariante de estado: el reject FUERZA published=false ────────────────


async def test_reject_forces_unpublish_even_if_registration_was_published(
    client, db, admin_user
):
    """RED: si una fila pendiente llegara al reject con published=true (p. ej.
    regresión futura del onboarding), el reject debe forzarla a false — un
    hotel rechazado NUNCA puede quedar visible/operativo."""
    _seed_registration(
        db,
        prop_id=9103,
        hotel_status=_PENDING,
        published=True,  # escenario de regresión: la fila nació publicada
        is_operational=True,
    )
    await _login_super_admin(client)

    resp = await client.post(
        "/api/admin/property-registrations/9103/reject",
        json={"reason": "Datos no verificables"},
    )
    assert resp.status_code == 200, resp.text

    hotel = db.dim_hotels.find_one({"prop_id": 9103})
    assert hotel["approval_status"] == _REJECTED
    assert hotel["published"] is False
    assert hotel["is_operational"] is False
