from __future__ import annotations

from fastapi import APIRouter, Body, Form, HTTPException, Query, Request, status as http_status
from fastapi.responses import JSONResponse, RedirectResponse

from src.app.modules.revenue.schemas import ModuleStatus
from src.app.modules.revenue.services import (
    conversion_overview,
    create_promotion_campaign,
    create_rate_plan,
    hotel_rates_overview,
    module_status,
    promotions_management_overview,
    promotions_overview,
    rate_plans_overview,
    reservations_overview,
    revenue_overview,
    save_hotel_rate,
    visitor_markets_overview,
)


router = APIRouter(prefix="/modules/revenue", tags=["modules-revenue"])
api_router = APIRouter(prefix="/api/management", tags=["management-revenue-api"])


@router.get("/status", response_model=ModuleStatus)
def revenue_status() -> ModuleStatus:
    return module_status()


@api_router.get("/rates")
def rates_api(prop_id: int = Query(..., ge=1)):
    return hotel_rates_overview(prop_id)


@api_router.get("/rates/options")
def rates_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    from src.app.modules.partner.services import list_partner_hotels

    results = list_partner_hotels(q, page=page, page_size=page_size)
    response: dict[str, object] = {
        "properties": [
            {
                "prop_id": item["prop_id"],
                "display_name": item.get("display_name") or item.get("hotel_name") or f"Hotel {item['prop_id']}",
            }
            for item in results["items"]
        ],
        "total": results["total"],
        "page": results["page"],
        "page_size": results["page_size"],
        "has_next": results["has_next"],
    }
    if prop_id:
        overview = hotel_rates_overview(prop_id)
        response["rate_plans"] = overview.get("rate_plans", [])
    return response


@api_router.post("/rates/plans", status_code=http_status.HTTP_201_CREATED)
def create_rate_plan_api(payload: dict = Body(...)):
    try:
        return create_rate_plan(
            prop_id=payload.get("prop_id"),
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            base_rate=payload.get("base_rate"),
            currency=str(payload.get("currency") or "USD"),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/rates/calendar")
def save_rate_calendar_api(payload: dict = Body(...)):
    try:
        return save_hotel_rate(
            prop_id=int(payload.get("prop_id") or 0),
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            date=str(payload.get("date") or ""),
            rate_amount=payload.get("rate_amount"),
            min_stay_nights=payload.get("min_stay_nights"),
            is_closed=payload.get("is_closed", False),
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
