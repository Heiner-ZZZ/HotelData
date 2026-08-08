"""Extensión del gate operativo a rutas management legadas (query param).

Design: `docs/APROBACION_HOTELES_Y_PRICING.md` §4 + §9. Las rutas modernas
del partner/management pasan por ``require_prop_permission`` (que ya rechaza
hoteles no publicados con 403 "no está operativo"). Pero las rutas LEGADAS
(billing, reservations, instay, housekeeping, expenses, ...) reciben
``prop_id`` como QUERY PARAM bajo ``require_permission`` GLOBAL — no pasaban
por ese gate.

Este test verifica el gate a nivel MIDDLEWARE: cualquier request autenticado
con ``?prop_id=X`` donde la fila de ``dim_hotels`` EXISTE con
``published=false`` explícito → 403 "no está operativo".

Backward compat (misma regla que el dependency):
- Hotel legado SIN el campo ``published`` → accesible (campo ausente = publicado).
- Fila de ``dim_hotels`` ausente → comportamiento previo (200).
- La cola del admin (``/api/admin/property-registrations``) y los flujos del
  dueño (``/api/auth/*``) operan EXACTAMENTE sobre hoteles no operativos →
  exentos del gate.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tests.conftest import login

pytestmark = pytest.mark.asyncio


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_hotel(db, *, prop_id: int, name: str, published=None) -> None:
    """Seed a dim_hotels row. `published=None` simula un hotel legado (sin campo)."""
    doc: dict = {
        "prop_id": prop_id,
        "hotel_name": name,
        "display_name": name,
        "created_at": _now(),
    }
    if published is not None:
        doc["published"] = published
    db.dim_hotels.insert_one(doc)


async def _login_admin(client) -> None:
    assert await login(client, "admin_test", "AdminPass123!") == 200


# ── 403 para hoteles existentes pero NO operativos (published=false) ──────


async def test_billing_list_403_for_unpublished_hotel(client, db, admin_user):
    """`/api/billing/invoices?prop_id=...` (billing.read global) → 403 operativo."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    await _login_admin(client)

    resp = await client.get("/api/billing/invoices", params={"prop_id": 9002})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


async def test_reservations_list_403_for_unpublished_hotel(client, db, admin_user):
    """`/api/reservations?prop_id=...` (reservations.read global) → 403 operativo."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    await _login_admin(client)

    resp = await client.get("/api/reservations", params={"prop_id": 9002})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


async def test_instay_sessions_403_for_unpublished_hotel(client, db, admin_user):
    """`/api/stay/sessions?prop_id=...` (instay staff) → 403 operativo."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    await _login_admin(client)

    resp = await client.get("/api/stay/sessions", params={"prop_id": 9002})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


async def test_management_checkin_dates_403_for_unpublished_hotel(client, db, admin_user):
    """`/api/management/check-ins/dates?prop_id=...` → 403 operativo."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    await _login_admin(client)

    resp = await client.get("/api/management/check-ins/dates", params={"prop_id": 9002})
    assert resp.status_code == 403
    assert "no está operativo" in resp.json()["detail"]


# ── Backward compat: operativo/publicado/ausente NO se bloquean ───────────


async def test_legacy_route_ok_for_published_hotel(client, db, admin_user):
    """Control: hotel publicado → la ruta legada responde 200."""
    _seed_hotel(db, prop_id=9001, name="Hotel Publicado", published=True)
    await _login_admin(client)

    resp = await client.get("/api/billing/invoices", params={"prop_id": 9001})
    assert resp.status_code == 200
    assert resp.json().get("items") == []


async def test_legacy_route_ok_for_hotel_without_published_field(client, db, admin_user):
    """Backward compat: legado sin el campo `published` sigue accesible."""
    _seed_hotel(db, prop_id=9001, name="Hotel Legado")  # sin published
    await _login_admin(client)

    resp = await client.get("/api/reservations", params={"prop_id": 9001})
    assert resp.status_code == 200


async def test_legacy_route_ok_when_hotel_row_missing(client, db, admin_user):
    """Fila de dim_hotels ausente → comportamiento previo (no se bloquea)."""
    await _login_admin(client)

    resp = await client.get("/api/stay/sessions", params={"prop_id": 9999})
    assert resp.status_code == 200


# ── Exenciones del gate (flujos que operan sobre hoteles no operativos) ───


async def test_approval_queue_not_blocked_by_operational_gate(client, db, admin_user):
    """La cola del admin opera SOBRE hoteles pendientes: el gate no aplica."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    await _login_admin(client)

    # prop_id en query (sintético — el listado de la cola no lo acepta como
    # param, FastAPI lo ignora) + hotel pendiente sembrado: el middleware
    # debe eximir el prefijo y dejar pasar al endpoint (200, sin registros).
    resp = await client.get(
        "/api/admin/property-registrations",
        params={"status": "pending_approval", "prop_id": 9002},
    )
    assert resp.status_code == 200
    assert "no está operativo" not in resp.text


async def test_auth_prefix_not_blocked_by_operational_gate(client, db, admin_user):
    """`/api/auth/*` (estado/edición del dueño) queda exento del gate operativo."""
    _seed_hotel(db, prop_id=9002, name="Hotel Pendiente", published=False)
    await _login_admin(client)

    # PATCH /api/auth/register-property/me con prop_id en query: para un
    # usuario aprobado el endpoint responde 400 (solo pending/changes_requested
    # editan). Lo que importa: NUNCA debe llegar el 403 operativo del
    # middleware — la exención del prefijo /api/auth/ lo impide.
    resp = await client.patch(
        "/api/auth/register-property/me",
        params={"prop_id": 9002},
        json={"hotel_name": "Hotel Corregido"},
    )
    # El estado exacto (400/409/422) depende de la cuenta del actor; lo que
    # verifica este test es que la exención del prefijo impide el 403
    # operativo del middleware pase lo que pase.
    assert "no está operativo" not in resp.text
