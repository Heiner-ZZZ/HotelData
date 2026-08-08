"""Pricing bands — catálogo canónico + descuento por pago anual.

Spec: `docs/APROBACION_HOTELES_Y_PRICING.md` §6 (recalibrado 2026-08-07 a
valores de adopción amigable). Cada banda expone:

- ``monthly_usd`` — cuota mensual estándar (pago mes a mes).
- ``annual_monthly_usd`` — cuota mensual equivalente pagando el año por
  adelantado (~22–27% de descuento ≈ 3 meses gratis).

El catálogo canónico vive en ``DEFAULT_PRICING_PLANS`` (fallback sin DB) y se
sembra en ``pricing_plans`` vía ``scripts/seed_pricing_plans.py`` (idempotente).
"""
from __future__ import annotations

import pytest

from src.app.modules.property_approval.pricing import (
    DEFAULT_PRICING_PLANS,
    suggested_band_for,
)

pytestmark = pytest.mark.asyncio


def _default_for(band: int) -> dict:
    return next(p for p in DEFAULT_PRICING_PLANS if p["band"] == band)


# ── Catálogo canónico ──────────────────────────────────────────────────


async def test_defaults_are_adoption_friendly_and_have_annual_price():
    """Toda banda tiene precio mensual recalibrado + anual; el anual siempre es menor."""
    for plan in DEFAULT_PRICING_PLANS:
        assert plan["monthly_usd"] > 0
        assert plan["annual_monthly_usd"] is not None
        assert plan["annual_monthly_usd"] < plan["monthly_usd"]


async def test_micro_and_pequeno_match_requested_ranges():
    """Micro $29–39 y Pequeño $69–89 (rango pedido por el usuario: anual–mensual)."""
    assert _default_for(1)["monthly_usd"] == 39
    assert _default_for(1)["annual_monthly_usd"] == 29
    assert _default_for(2)["monthly_usd"] == 89
    assert _default_for(2)["annual_monthly_usd"] == 69


async def test_bands_are_ordered_and_cover_all_rooms():
    """Las 6 bandas cubren 1..10000 sin huecos ni solapamientos."""
    bands = sorted(DEFAULT_PRICING_PLANS, key=lambda p: p["band"])
    assert [p["band"] for p in bands] == [1, 2, 3, 4, 5, 6]
    prev_max = 0
    for plan in bands:
        assert plan["min_rooms"] == prev_max + 1
        prev_max = plan["max_rooms"]
    assert prev_max >= 10_000


# ── Resolución (suggested_band_for) ────────────────────────────────────


async def test_suggested_band_for_exposes_annual_price(db):
    """Sin catálogo en DB, la banda sugerida usa los defaults e incluye el anual."""
    band = suggested_band_for(db, 12)  # Pequeño (11–25)
    assert band is not None
    assert band["label"] == "Pequeño"
    assert band["monthly_usd"] == 89
    assert band["annual_monthly_usd"] == 69


async def test_catalog_plan_explicit_annual_wins(db):
    """Un plan del catálogo con annual_monthly_usd explícito manda sobre el fallback."""
    db.pricing_plans.insert_one(
        {
            "band": 1,
            "label": "Micro",
            "min_rooms": 1,
            "max_rooms": 10,
            "monthly_usd": 39,
            "annual_monthly_usd": 25,
            "is_active": True,
        }
    )
    band = suggested_band_for(db, 5)
    assert band["monthly_usd"] == 39
    assert band["annual_monthly_usd"] == 25


async def test_catalog_plan_without_annual_falls_back_to_discount(db):
    """Planes del catálogo sin el campo anual (pre-recalibración) → ~25% off."""
    db.pricing_plans.insert_one(
        {
            "band": 2,
            "label": "Pequeño",
            "min_rooms": 11,
            "max_rooms": 25,
            "monthly_usd": 89,
            "is_active": True,
        }
    )
    band = suggested_band_for(db, 20)
    assert band["annual_monthly_usd"] == round(89 * 0.75)


# ── Seed script (scripts/seed_pricing_plans.py) ────────────────────────


async def test_seed_script_upserts_idempotently(db):
    """El seed es idempotente: re-correr no duplica y refresca los valores
    canónicos (upsert $set, nunca delete)."""
    from scripts.seed_pricing_plans import seed_pricing_plans

    first = seed_pricing_plans(db)
    assert first["total"] == len(DEFAULT_PRICING_PLANS)
    assert first["inserted"] == len(DEFAULT_PRICING_PLANS)

    second = seed_pricing_plans(db)
    assert second["total"] == len(DEFAULT_PRICING_PLANS)
    assert second["inserted"] == 0  # re-run no duplica
    assert second["updated"] == len(DEFAULT_PRICING_PLANS)

    # Valores del catálogo == canónico (upsert $set).
    plan = db.pricing_plans.find_one({"band": 2})
    assert plan["monthly_usd"] == 89
    assert plan["annual_monthly_usd"] == 69
    assert plan["is_active"] is True


async def test_seed_script_dry_run_does_not_write(db):
    from scripts.seed_pricing_plans import seed_pricing_plans

    result = seed_pricing_plans(db, dry_run=True)
    assert result["inserted"] == len(DEFAULT_PRICING_PLANS)
    assert db.pricing_plans.count_documents({}) == 0
