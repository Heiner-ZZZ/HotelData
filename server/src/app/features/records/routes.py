from __future__ import annotations

from fastapi import APIRouter, Query

from src.app.features.records.service import find_hotels


router = APIRouter()


@router.get("/records")
def records(
    q: str = "",
    destination: str = "",
    country: str = "",
    city: str = "",
    county: str = "",
    min_rating: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1),
):
    parsed_min_rating = None
    if min_rating.strip():
        try:
            parsed_min_rating = float(min_rating)
        except ValueError:
            parsed_min_rating = None

    effective_destination = destination or city
    effective_country = country or county

    results = find_hotels(q, effective_destination, effective_country, parsed_min_rating, page, page_size)
    return results
