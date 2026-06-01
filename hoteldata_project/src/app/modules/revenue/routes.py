from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.app.modules.revenue.schemas import ModuleStatus
from src.app.modules.revenue.service import (
    conversion_overview,
    create_promotion_campaign,
    create_rate_plan,
    ensure_revenue_collections,
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
web_router = APIRouter(prefix="/analytics", tags=["analytics"])
ops_router = APIRouter(prefix="/revenue", tags=["revenue"])
api_router = APIRouter(prefix="/api/management", tags=["management-revenue-api"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    ensure_revenue_collections()
    return module_status()


@web_router.get("/reservations")
def reservations(request: Request):
    return templates.TemplateResponse(request, "analytics/reservations.html", {"overview": reservations_overview()})


@web_router.get("/conversion")
def conversion(request: Request):
    return templates.TemplateResponse(request, "analytics/conversion.html", {"overview": conversion_overview()})


@web_router.get("/revenue")
def revenue(request: Request):
    return templates.TemplateResponse(request, "analytics/revenue.html", {"overview": revenue_overview()})


@web_router.get("/promotions")
def promotions(request: Request):
    return templates.TemplateResponse(request, "analytics/promotions.html", {"overview": promotions_overview()})


@web_router.get("/visitor-markets")
def visitor_markets(request: Request):
    return templates.TemplateResponse(request, "analytics/visitor_markets.html", {"overview": visitor_markets_overview()})


@ops_router.get("/rate-plans")
def rate_plans(request: Request):
    context = rate_plans_overview()
    context["message"] = request.query_params.get("message")
    context["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "revenue/rate_plans.html", context)


@ops_router.get("/rate-plans/new")
def rate_plans_new(request: Request):
    return templates.TemplateResponse(
        request,
        "revenue/rate_plans_new.html",
        {
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
            "form_values": {
                "prop_id": "",
                "name": "",
                "description": "",
                "base_rate": "",
                "currency": "USD",
                "is_active": True,
            },
        },
    )


@ops_router.post("/rate-plans/new")
def rate_plans_new_submit(
    request: Request,
    prop_id: int = Form(...),
    name: str = Form(default=""),
    description: str = Form(default=""),
    base_rate: float = Form(default=0.0),
    currency: str = Form(default="USD"),
    is_active: str = Form(default="on"),
):
    try:
        create_rate_plan(
            prop_id=prop_id,
            name=name,
            description=description,
            base_rate=base_rate,
            currency=currency,
            is_active=is_active,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/revenue/rate-plans/new?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    return RedirectResponse(url="/revenue/rate-plans?message=Plan+tarifario+registrado", status_code=303)


@ops_router.get("/hotel/{prop_id}/rates")
def hotel_rates(request: Request, prop_id: int):
    context = hotel_rates_overview(prop_id)
    context["message"] = request.query_params.get("message")
    context["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "revenue/hotel_rates.html", context)


@ops_router.post("/hotel/{prop_id}/rates")
def hotel_rates_submit(
    request: Request,
    prop_id: int,
    rate_plan_id: str = Form(default=""),
    date: str = Form(default=""),
    rate_amount: float = Form(default=0.0),
    min_stay_nights: int = Form(default=1),
    is_closed: str = Form(default=""),
):
    try:
        save_hotel_rate(
            prop_id=prop_id,
            rate_plan_id=rate_plan_id,
            date=date,
            rate_amount=rate_amount,
            min_stay_nights=min_stay_nights,
            is_closed=is_closed,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/revenue/hotel/{prop_id}/rates?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/revenue/hotel/{prop_id}/rates?message=Tarifa+actualizada", status_code=303)


@ops_router.get("/promotions")
def promotions_management(request: Request):
    context = promotions_management_overview()
    context["message"] = request.query_params.get("message")
    context["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "revenue/promotions.html", context)


@ops_router.get("/promotions/new")
def promotions_new(request: Request):
    return templates.TemplateResponse(
        request,
        "revenue/promotions_new.html",
        {
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
            "form_values": {
                "prop_id": "",
                "name": "",
                "description": "",
                "discount_percent": "",
                "start_date": "",
                "end_date": "",
                "coupon_code": "",
                "is_active": True,
            },
        },
    )


@ops_router.post("/promotions/new")
def promotions_new_submit(
    request: Request,
    prop_id: int = Form(...),
    name: str = Form(default=""),
    description: str = Form(default=""),
    discount_percent: int = Form(default=0),
    start_date: str = Form(default=""),
    end_date: str = Form(default=""),
    coupon_code: str = Form(default=""),
    is_active: str = Form(default="on"),
):
    try:
        create_promotion_campaign(
            prop_id=prop_id,
            name=name,
            description=description,
            discount_percent=discount_percent,
            start_date=start_date,
            end_date=end_date,
            coupon_code=coupon_code,
            is_active=is_active,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/revenue/promotions/new?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    return RedirectResponse(url="/revenue/promotions?message=Promocion+registrada", status_code=303)


@api_router.get("/rates")
def rates_api(prop_id: int = Query(..., ge=1)):
    return hotel_rates_overview(prop_id)


@api_router.post("/rates/plans", status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
