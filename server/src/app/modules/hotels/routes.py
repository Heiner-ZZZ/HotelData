from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, status as http_status
from fastapi.responses import RedirectResponse
from src.app.template_utils import templates

from src.app.modules.hotels.schemas import ModuleStatus
from src.app.modules.hotels.service import compare_hotel_options, compare_hotels, hotel_detail, module_status, search_hotels
from src.app.modules.hotels.service.availability import search_available_hotels


router = APIRouter(prefix="/modules/hotels", tags=["modules-hotels"])
web_router = APIRouter(tags=["hotels"])
api_router = APIRouter(prefix="/api/hotels", tags=["hotels-api"])


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
    amenities: str = "",
    amenities_mode: str = "or",
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
        "amenities": amenities,
        "amenities_mode": amenities_mode,
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


@api_router.get("/compare")
def compare_api(prop_id: list[int] = Query(default=[])):
    """Compare up to 3 hotels side by side (JSON)."""
    comparison = compare_hotels(prop_id)
    return comparison


@api_router.get("/availability")
def availability_search(
    destination: str = "",
    check_in: str = "",
    check_out: str = "",
    adults: int = 1,
    children: int = 0,
    rooms: int = 1,
    amenities: str = "",
    amenities_mode: str = "or",
    page: int = Query(default=1, ge=1),
):
    """Operational search: find hotels with real-time availability for
    the given dates, guest count, and destination.

    Checks `room_inventory_calendar` for available rooms and
    `hotel_rate_calendar` for nightly rates.
    """
    return search_available_hotels(
        destination=destination,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        rooms=rooms,
        amenities=amenities,
        amenities_mode=amenities_mode,
        page=page,
        page_size=10,
    )


@api_router.get("/search")
def search_api(
    destination: str = "",
    min_price: str = "",
    max_price: str = "",
    min_stars: str = "",
    promotion: str = "",
    amenities: str = "",
    amenities_mode: str = "or",
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
        "amenities": amenities,
        "amenities_mode": amenities_mode,
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
