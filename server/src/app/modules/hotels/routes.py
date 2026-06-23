from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status as http_status
from fastapi.responses import RedirectResponse

from src.app.modules.hotels.schemas import ModuleStatus
from src.app.modules.hotels.service import (
    module_status,
    search_hotels,
    hotel_detail,
)
from src.app.modules.hotels.service.availability import search_available_hotels
from src.app.modules.hotels.service.compare import compare_hotels_with_availability
from src.app.modules.hotels.service.similar import similar_hotels


router = APIRouter(prefix="/modules/hotels", tags=["modules-hotels"])
api_router = APIRouter(prefix="/api/hotels", tags=["hotels-api"])


@router.get("/status", response_model=ModuleStatus)
def hotels_status() -> ModuleStatus:
    return module_status()


@api_router.get("/availability")
def availability_search(
    destination: str = "",
    check_in: str = "",
    check_out: str = "",
    adults: int = Query(default=1, ge=1),
    children: int = Query(default=0, ge=0),
    rooms: int = Query(default=1, ge=1),
    amenities: str = "",
    amenities_mode: str = Query(default="or", pattern="^(or|and)$"),
    sort_by: str = Query(default="price", pattern="^(price|rating|stars|name)$"),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    star_rating: float | None = Query(default=None, ge=1, le=5),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=20),
):
    """Public operational availability search.

    Returns hotels with real-time inventory and rate checks.
    No authentication required.
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
        sort_by=sort_by,
        price_min=price_min,
        price_max=price_max,
        star_rating=star_rating,
        page=page,
        page_size=page_size,
    )


@api_router.get("/compare")
def compare_api(
    prop_id: list[int] = Query(default=[]),
    check_in: str = "",
    check_out: str = "",
    adults: int = Query(default=1, ge=1),
    children: int = Query(default=0, ge=0),
):
    """Compare up to 3 hotels side by side with operational data.

    Returns enhanced comparison including rates (when dates provided),
    room types, amenities, and policies for each hotel.
    Public endpoint, no authentication required.
    """
    if not prop_id:
        return {"items": []}
    return compare_hotels_with_availability(
        prop_ids=prop_id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
    )


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


@api_router.get("/{prop_id}/similar")
def similar_api(
    prop_id: int,
    limit: int = Query(default=6, ge=1, le=12),
):
    return similar_hotels(prop_id, limit=limit)


@api_router.get("/{prop_id}")
def detail_api(prop_id: int):
    hotel = hotel_detail(prop_id)
    if hotel is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    return hotel
