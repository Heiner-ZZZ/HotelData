"""Generación de calendario de tarifas (POST /api/management/rates/calendar/generate).

Reglas bajo prueba:
- Las fechas de inicio y fin son OBLIGATORIAS (ya no existe el default de
  "hoy → hoy + 90 días").
- ``dry_run`` cuenta las entradas que se crearían (saltando las existentes)
  SIN escribir en ``hotel_rate_calendar`` — lo usa el modal de confirmación
  del frontend para mostrar el conteo exacto antes de generar.
- Sin ``dry_run``, genera (upsert) las entradas del rango para el plan.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login

pytestmark = pytest.mark.asyncio


def _seed_hotel(db, prop_id: int) -> None:
    db.dim_hotels.insert_one(
        {
            "prop_id": prop_id,
            "hotel_name": f"Hotel {prop_id}",
            "display_name": f"Hotel {prop_id}",
            "prop_starrating": 4.0,
            "prop_review_score": 8.0,
        }
    )


def _seed_plan(db, prop_id: int, plan_id: str = "RP-FLEX") -> None:
    db.rate_plans.insert_one(
        {
            "prop_id": prop_id,
            "rate_plan_id": plan_id,
            "name": "Flexible",
            "base_rate": 100.0,
        }
    )


def _generate(client: AsyncClient, prop_id: int, **extra) -> dict:
    payload = {"prop_id": prop_id, **extra}
    return client.post(f"/api/management/rates/calendar/generate?prop_id={prop_id}", json=payload)


async def test_generate_requires_start_and_end_dates(client: AsyncClient, db, admin_user):
    """Sin fechas (o con solo una) → 400. Ya no hay default de hoy → +90 días."""
    prop_id = 9101
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)

    resp = await _generate(client, prop_id)
    assert resp.status_code == 400, resp.text
    assert "fecha" in resp.json()["detail"].lower()

    resp = await _generate(client, prop_id, start_date="2026-09-01")
    assert resp.status_code == 400, resp.text
    assert "fecha" in resp.json()["detail"].lower()


async def test_generate_dry_run_counts_without_writing(client: AsyncClient, db, admin_user):
    """dry_run=True devuelve el conteo exacto (salta lo existente) y no escribe nada."""
    prop_id = 9102
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)
    # Una entrada ya existente en el rango (no debe contarse ni reescribirse)
    db.hotel_rate_calendar.insert_one(
        {"prop_id": prop_id, "rate_plan_id": "RP-FLEX", "date": "2026-09-02", "rate_amount": 90.0}
    )
    before = db.hotel_rate_calendar.count_documents({"prop_id": prop_id})

    resp = await _generate(
        client, prop_id,
        rate_plan_id="RP-FLEX", start_date="2026-09-01", end_date="2026-09-05", dry_run=True,
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    # Rango de 5 noches, 1 ya existe → 4 nuevas
    assert result["entries_generated"] == 4
    assert db.hotel_rate_calendar.count_documents({"prop_id": prop_id}) == before

    # La entrada existente sigue intacta (no se pisó con la base 100)
    existing = db.hotel_rate_calendar.find_one({"prop_id": prop_id, "date": "2026-09-02"})
    assert existing["rate_amount"] == 90.0


async def test_generate_writes_entries_without_dry_run(client: AsyncClient, db, admin_user):
    """Sin dry_run genera (upsert) las entradas del rango para el plan."""
    prop_id = 9103
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)

    resp = await _generate(
        client, prop_id,
        rate_plan_id="RP-FLEX", start_date="2026-09-01", end_date="2026-09-03",
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["entries_generated"] == 3
    assert result["start_date"] == "2026-09-01"
    assert result["end_date"] == "2026-09-03"

    docs = list(db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0}).sort("date", 1))
    assert [d["date"] for d in docs] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert all(d["rate_amount"] == 100.0 and d["source"] == "generated" for d in docs)


async def test_generate_without_plans_returns_zero(client: AsyncClient, db, admin_user):
    """Sin planes tarifarios (o sin base_rate > 0) → 0 entradas, sin error."""
    prop_id = 9104
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)

    resp = await _generate(client, prop_id, start_date="2026-09-01", end_date="2026-09-03")
    assert resp.status_code == 200, resp.text
    assert resp.json()["entries_generated"] == 0
