from __future__ import annotations

from fastapi import APIRouter, Query

from src.app.modules.partner.services.currencies import list_currencies

public_router = APIRouter(prefix="/api/public", tags=["public"])


@public_router.get("/currencies")
def public_list_currencies_api(
    active_only: bool = Query(default=True),
) -> dict:
    """Return active system currencies for public landing surfaces.

    Public — no auth required. Currencies are non-sensitive reference data
    used by the B2C landing page (welcome) to drive the lang/currency chip
    and price formatting across the Booking-flow preview.
    """
    currencies = list_currencies(active_only=active_only)
    return {"currencies": currencies}
