"""Actualización masiva de calendario (POST /api/management/rates/calendar/batch).

Reglas bajo prueba:
- ``dry_run`` cuenta los días afectados (respetando el filtro de fines de
  semana) SIN escribir en ``hotel_rate_calendar`` — el modal de confirmación
  del frontend muestra el conteo exacto antes de aplicar.
- Sin ``dry_run``, aplica (upsert) la tarifa a todos los días del rango.
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


def _batch(client: AsyncClient, prop_id: int, **extra) -> dict:
    payload = {"prop_id": prop_id, **extra}
    return client.post("/api/management/rates/calendar/batch", json=payload)


async def test_batch_dry_run_counts_without_writing(client: AsyncClient, db, admin_user):
    """dry_run=True devuelve los días afectados y no toca la colección."""
    prop_id = 9201
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)
    # Entrada preexistente en el rango — no debe modificarse en dry-run
    db.hotel_rate_calendar.insert_one(
        {"prop_id": prop_id, "rate_plan_id": "RP-FLEX", "date": "2026-09-02", "rate_amount": 90.0}
    )
    before = db.hotel_rate_calendar.count_documents({"prop_id": prop_id})

    resp = await _batch(
        client, prop_id,
        rate_plan_id="RP-FLEX", start_date="2026-09-01", end_date="2026-09-05",
        rate_amount=120, dry_run=True,
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["affected_days"] == 5
    assert db.hotel_rate_calendar.count_documents({"prop_id": prop_id}) == before

    existing = db.hotel_rate_calendar.find_one({"prop_id": prop_id, "date": "2026-09-02"})
    assert existing["rate_amount"] == 90.0  # no se pisó


async def test_batch_dry_run_respects_weekend_filter(client: AsyncClient, db, admin_user):
    """Con only_weekends, el conteo solo incluye sábados y domingos."""
    prop_id = 9202
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)

    # 2026-09-01 (mar) → 2026-09-07 (lun): fines de semana = 05 (sáb) y 06 (dom)
    resp = await _batch(
        client, prop_id,
        rate_plan_id="RP-FLEX", start_date="2026-09-01", end_date="2026-09-07",
        rate_amount=120, only_weekends=True, dry_run=True,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["affected_days"] == 2
    assert db.hotel_rate_calendar.count_documents({"prop_id": prop_id}) == 0


async def test_batch_writes_entries_without_dry_run(client: AsyncClient, db, admin_user):
    """Sin dry_run aplica (upsert) la tarifa a todos los días del rango."""
    prop_id = 9203
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)

    resp = await _batch(
        client, prop_id,
        rate_plan_id="RP-FLEX", start_date="2026-09-01", end_date="2026-09-03",
        rate_amount=120,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["affected_days"] == 3

    docs = list(db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0}).sort("date", 1))
    assert [d["date"] for d in docs] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert all(d["rate_amount"] == 120.0 for d in docs)


async def test_batch_requires_plan_and_dates(client: AsyncClient, db, admin_user):
    """Sin rate_plan_id (o fechas) → 400, no se escribe nada."""
    prop_id = 9204
    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    _seed_hotel(db, prop_id)
    _seed_plan(db, prop_id)

    resp = await _batch(client, prop_id, start_date="2026-09-01", end_date="2026-09-03", rate_amount=120)
    assert resp.status_code == 400, resp.text
    assert db.hotel_rate_calendar.count_documents({"prop_id": prop_id}) == 0
