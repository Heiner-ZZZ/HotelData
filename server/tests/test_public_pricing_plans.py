"""GET /api/public/pricing-plans — catálogo público de bandas (wizard de onboarding).

El paso "confirma tu plan" del onboarding necesita derivar la banda en el
cliente SIN hardcodear precios: lee el catálogo público y busca la banda que
cubre `total_rooms`. Este endpoint expone solo bandas activas y hace fallback a
los defaults documentados cuando el catálogo está vacío (un GET nunca escribe).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


def _seed_plans(db) -> None:
    db.pricing_plans.insert_many(
        [
            {"band": 1, "label": "Micro", "min_rooms": 1, "max_rooms": 10,
             "monthly_usd": 39, "annual_monthly_usd": 29, "is_active": True},
            {"band": 2, "label": "Pequeño", "min_rooms": 11, "max_rooms": 25,
             "monthly_usd": 89, "annual_monthly_usd": 69, "is_active": True},
            {"band": 3, "label": "Inactivo", "min_rooms": 26, "max_rooms": 50,
             "monthly_usd": 149, "annual_monthly_usd": 109, "is_active": False},
        ]
    )


async def test_public_pricing_plans_returns_only_active_bands(client, db):
    _seed_plans(db)
    resp = await client.get("/api/public/pricing-plans")
    assert resp.status_code == 200, resp.text
    plans = resp.json()["plans"]
    assert {p["band"] for p in plans} == {1, 2}  # la inactiva no se expone

    plan2 = next(p for p in plans if p["band"] == 2)
    assert plan2["label"] == "Pequeño"
    assert plan2["min_rooms"] == 11
    assert plan2["max_rooms"] == 25
    assert plan2["monthly_usd"] == 89
    assert plan2["annual_monthly_usd"] == 69


async def test_public_pricing_plans_falls_back_to_defaults_when_empty(client, db):
    # Catálogo vacío (conftest limpia `pricing_plans`) → fallback a defaults,
    # nunca 404 ni lista vacía (el wizard no debe bloquearse).
    resp = await client.get("/api/public/pricing-plans")
    assert resp.status_code == 200, resp.text
    plans = resp.json()["plans"]
    assert len(plans) >= 6
    bands = {p["band"] for p in plans}
    assert {1, 2, 3, 4, 5, 6} <= bands
    # La banda pequeña (1-25 hab) mantiene la calibración canónica.
    small = next(p for p in plans if p["band"] == 2)
    assert small["label"] == "Pequeño"
    assert small["monthly_usd"] == 89
