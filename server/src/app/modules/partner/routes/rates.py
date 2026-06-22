from __future__ import annotations

from fastapi import Body, HTTPException, Query, status

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_rate_plan,
    list_partner_hotels,
    partner_hotel_rates,
    save_rate_calendar_entry,
)


@api_router.get("/rates")
def rates_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_rates(require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return {
        "prop_id": detail["hotel"]["prop_id"],
        "hotel_label": detail["hotel"]["display_name"],
        "manual_override": detail["hotel"].get("manual_override", False),
        "profile_badge": detail["hotel"].get("profile_badge"),
        "rate_plans": detail.get("rate_plans", []),
        "calendar": detail.get("calendar", []),
        "rate_rules": detail.get("rate_rules", []),
        "promotions": detail.get("promotions", []),
        "coupon_codes": detail.get("coupon_codes", []),
    }


@api_router.get("/rates/options")
def rates_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    results = list_partner_hotels(q, page=page, page_size=page_size)
    response: dict[str, object] = {
        "properties": [
            {
                "prop_id": item["prop_id"],
                "display_name": item.get("display_name") or f"Hotel {item['prop_id']}",
            }
            for item in results["items"]
        ],
        "total": results["total"],
        "page": results["page"],
        "page_size": results["page_size"],
        "has_next": results["has_next"],
    }
    if prop_id:
        detail = partner_hotel_rates(require_prop_id(prop_id))
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        response["rate_plans"] = [
            {
                "rate_plan_id": item["rate_plan_id"],
                "name": item.get("name") or item["rate_plan_id"],
            }
            for item in detail.get("rate_plans", [])
        ]
    return response


@api_router.post("/rates/plans", status_code=201)
def rates_plan_create_api(payload: dict = Body(...)):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_rate_plan(
            prop_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            base_rate=payload.get("base_rate"),
            currency=str(payload.get("currency") or "USD"),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/rates/calendar")
def rates_calendar_update_api(payload: dict = Body(...)):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = save_rate_calendar_entry(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            date=str(payload.get("date") or ""),
            rate_amount=payload.get("rate_amount"),
            min_stay_nights=payload.get("min_stay_nights"),
            is_closed=payload.get("is_closed", False),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved
