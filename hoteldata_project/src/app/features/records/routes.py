from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.app.features.records.service import find_hotels


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


@router.get("/records")
def records(
    request: Request,
    q: str = "",
    destination: str = "",
    country: str = "",
    city: str = "",
    county: str = "",
    min_rating: str = "",
    page: int = 1,
    page_size: int = 25,
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
    return templates.TemplateResponse(
        request,
        "records/index.html",
        {
            "query": q,
            "destination": effective_destination,
            "country": effective_country,
            "min_rating": parsed_min_rating,
            "page": page,
            "page_size": results["page_size"],
            "results": results,
            "hotels": results["items"],
            "display_columns": results["display_columns"],
        },
    )
