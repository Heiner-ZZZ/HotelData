from __future__ import annotations

from fastapi import Body, HTTPException, Query, status

from fastapi import Depends

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    batch_update_rate_calendar,
    create_rate_plan,
    create_seasonal_rule,
    delete_rate_plan,
    delete_seasonal_rule,
    generate_calendar_from_rules,
    list_partner_hotels,
    list_seasonal_rules,
    partner_hotel_rates,
    save_rate_calendar_entry,
    update_rate_plan,
    update_seasonal_rule,
)
from src.app.modules.revenue.services.promotions import create_promotion_campaign
from src.app.security.dependencies import require_login


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
        "room_types": detail.get("room_types", []),
    }


@api_router.get("/rates/options")
def rates_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    results = list_partner_hotels(q, page=page, page_size=page_size, user=current_user)
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
            room_type_id=str(payload.get("room_type_id") or ""),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.put("/rates/plans/{plan_id}")
def rates_plan_update_api(plan_id: str, payload: dict = Body(...)):
    try:
        saved = update_rate_plan(
            plan_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            base_rate=payload.get("base_rate"),
            currency=str(payload.get("currency") or "USD"),
            room_type_id=str(payload.get("room_type_id") or ""),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate plan not found")
    return saved


@api_router.delete("/rates/plans/{plan_id}")
def rates_plan_delete_api(plan_id: str):
    try:
        result = delete_rate_plan(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate plan not found")
    return result


@api_router.get("/rates/seasonal-rules")
def rates_seasonal_rules_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    rate_plan_id: str | None = Query(default=None),
):
    items = list_seasonal_rules(prop_id=prop_id, rate_plan_id=rate_plan_id)
    return {"items": items, "total": len(items)}


@api_router.post("/rates/seasonal-rules", status_code=201)
def rates_seasonal_rule_create_api(payload: dict = Body(...)):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_seasonal_rule(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            name=str(payload.get("name") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            price_override=payload.get("price_override"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.put("/rates/seasonal-rules/{rule_id}")
def rates_seasonal_rule_update_api(rule_id: str, payload: dict = Body(...)):
    try:
        saved = update_seasonal_rule(
            rule_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            name=str(payload.get("name") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            price_override=payload.get("price_override"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seasonal rule not found")
    return saved


@api_router.delete("/rates/seasonal-rules/{rule_id}")
def rates_seasonal_rule_delete_api(rule_id: str):
    result = delete_seasonal_rule(rule_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seasonal rule not found")
    return result


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


@api_router.post("/rates/calendar/batch")
def rates_calendar_batch_api(payload: dict = Body(...)):
    """Batch update rate calendar for a date range."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        result = batch_update_rate_calendar(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            rate_amount=payload.get("rate_amount"),
            min_stay_nights=payload.get("min_stay_nights"),
            is_closed=payload.get("is_closed"),
            only_weekends=bool(payload.get("only_weekends", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result


@api_router.post("/rates/calendar/generate")
def rates_calendar_generate_api(payload: dict = Body(...)):
    """Generate calendar entries from base_price + seasonal rules."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        result = generate_calendar_from_rules(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or "") or None,
            start_date=str(payload.get("start_date") or "") or None,
            end_date=str(payload.get("end_date") or "") or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result


@api_router.post("/rates/promotions", status_code=201)
def rates_promotion_create_api(payload: dict = Body(...)):
    try:
        saved = create_promotion_campaign(
            prop_id=payload.get("prop_id"),
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            discount_percent=payload.get("discount_percent", 0),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            coupon_code=str(payload.get("coupon_code") or ""),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return saved
