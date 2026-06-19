from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, status as http_status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.app.modules.hotels.schemas import ModuleStatus
from src.app.modules.hotels.service import compare_hotel_options, compare_hotels, hotel_detail, module_status, search_hotels


router = APIRouter(prefix="/modules/hotels", tags=["modules-hotels"])
web_router = APIRouter(tags=["hotels"])
api_router = APIRouter(prefix="/api/hotels", tags=["hotels-api"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/status", response_model=ModuleStatus)
def hotels_status() -> ModuleStatus:
    return module_status()


def _page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    return f"{request.url.path}?{urlencode(params)}"


@web_router.get("/hotels/search")
def search(
    request: Request,
    destination: str = "",
    min_price: str = "",
    max_price: str = "",
    min_stars: str = "",
    promotion: str = "",
    adults: str = "",
    children: str = "",
    rooms: str = "",
    page: int = Query(default=1, ge=1),
):
    filters = {
        "destination": destination,
        "min_price": min_price,
        "max_price": max_price,
        "min_stars": min_stars,
        "promotion": promotion,
        "adults": adults,
        "children": children,
        "rooms": rooms,
    }
    results = search_hotels(filters, page=page, page_size=10)
    return templates.TemplateResponse(
        request,
        "hotels/search.html",
        {
            "results": results,
            "prev_url": _page_url(request, results["page"] - 1) if results["has_prev"] else None,
            "next_url": _page_url(request, results["page"] + 1) if results["has_next"] else None,
        },
    )


@web_router.get("/hotels/compare")
def compare(request: Request, prop_id: list[str] = Query(default=[])):
    parsed_prop_ids: list[int] = []
    for value in prop_id:
        text = str(value).strip()
        if not text:
            continue
        try:
            parsed_prop_ids.append(int(text))
        except ValueError:
            continue
    comparison = compare_hotels(parsed_prop_ids)
    options = compare_hotel_options()
    return templates.TemplateResponse(
        request,
        "hotels/compare.html",
        {"comparison": comparison, "prop_id_values": parsed_prop_ids[:3], "hotel_options": options},
    )


@web_router.get("/hotels/{prop_id}")
def detail(request: Request, prop_id: int):
    hotel = hotel_detail(prop_id)
    if hotel is None:
        return RedirectResponse(url="/hotels/search", status_code=303)
    return templates.TemplateResponse(request, "hotels/detail.html", {"hotel": hotel})


@api_router.get("/search")
def search_api(
    destination: str = "",
    min_price: str = "",
    max_price: str = "",
    min_stars: str = "",
    promotion: str = "",
    adults: str = "",
    children: str = "",
    rooms: str = "",
    page: int = Query(default=1, ge=1),
):
    filters = {
        "destination": destination,
        "min_price": min_price,
        "max_price": max_price,
        "min_stars": min_stars,
        "promotion": promotion,
        "adults": adults,
        "children": children,
        "rooms": rooms,
    }
    return search_hotels(filters, page=page, page_size=10)


@api_router.get("/{prop_id}")
def detail_api(prop_id: int):
    hotel = hotel_detail(prop_id)
    if hotel is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    return hotel
