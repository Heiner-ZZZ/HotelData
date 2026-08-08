"""Pricing bands by room count (docs/APROBACION_HOTELES_Y_PRICING.md §6).

The ``pricing_plans`` collection is the canonical catalog (seeded idempotently
via ``scripts/seed_pricing_plans.py``, admin-adjustable). ``suggested_band_for``
reads it first and falls back to the documented defaults when the collection is
empty (dev/test or pre-seed) — a GET never writes.
"""

from __future__ import annotations

from typing import Any

# Defaults — recalibrados 2026-08-07 a valores de adopción amigable: anclados al
# benchmark $6-25/hab/mes de la industria pero con montos absolutos bajos para
# el long-tail (Micro $39, Pequeño $89, …). Cada banda expone el pago mensual
# (``monthly_usd``) y la cuota mensual equivalente pagando el año por adelantado
# (``annual_monthly_usd``, ~22–27% de descuento ≈ 3 meses gratis).
DEFAULT_PRICING_PLANS: list[dict[str, Any]] = [
    {"band": 1, "label": "Micro", "min_rooms": 1, "max_rooms": 10, "monthly_usd": 39, "annual_monthly_usd": 29},
    {"band": 2, "label": "Pequeño", "min_rooms": 11, "max_rooms": 25, "monthly_usd": 89, "annual_monthly_usd": 69},
    {"band": 3, "label": "Mediano", "min_rooms": 26, "max_rooms": 50, "monthly_usd": 149, "annual_monthly_usd": 109},
    {"band": 4, "label": "Grande", "min_rooms": 51, "max_rooms": 100, "monthly_usd": 229, "annual_monthly_usd": 169},
    {"band": 5, "label": "Muy grande", "min_rooms": 101, "max_rooms": 300, "monthly_usd": 399, "annual_monthly_usd": 299},
    {"band": 6, "label": "Enterprise", "min_rooms": 301, "max_rooms": 10_000, "monthly_usd": 549, "annual_monthly_usd": 399},
]

# Descuento por pago anual aplicado SOLO como fallback para planes del catálogo
# antiguos sin ``annual_monthly_usd`` explícito (≈25% ≈ 3 meses gratis).
ANNUAL_DISCOUNT_FACTOR: float = 0.75


def _annual_monthly_usd(plan: dict[str, Any]) -> float:
    """Cuota mensual equivalente pagando el año; explícita o fallback ~25% off."""
    explicit = plan.get("annual_monthly_usd")
    if explicit is not None:
        return float(explicit)
    monthly = float(plan.get("monthly_usd", 0))
    return float(round(monthly * ANNUAL_DISCOUNT_FACTOR))


def _plans_from_db(db) -> list[dict[str, Any]]:
    return list(
        db.pricing_plans.find({"is_active": {"$ne": False}}).sort("band", 1)
    )


def available_plans(db) -> list[dict[str, Any]]:
    """Catalog ordered by band — DB first, defaults fallback."""
    plans = _plans_from_db(db)
    if plans:
        return plans
    return [dict(p) for p in DEFAULT_PRICING_PLANS]


def suggested_band_for(db, total_rooms: int) -> dict[str, Any] | None:
    """Resolve the band covering *total_rooms* (1..10000 validated upstream)."""
    try:
        rooms = int(total_rooms)
    except (TypeError, ValueError):
        rooms = 0
    for plan in available_plans(db):
        min_rooms = int(plan.get("min_rooms", 0))
        max_rooms = int(plan.get("max_rooms", 0))
        if min_rooms <= rooms <= max_rooms:
            return {
                "band": int(plan.get("band", 0)),
                "label": plan.get("label", ""),
                "min_rooms": min_rooms,
                "max_rooms": max_rooms,
                "monthly_usd": float(plan.get("monthly_usd", 0)),
                "annual_monthly_usd": _annual_monthly_usd(plan),
            }
    return None
