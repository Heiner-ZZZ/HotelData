from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status as http_status

from src.app.modules.revenue.schemas import ModuleStatus
from src.app.modules.revenue.services import (
    create_promotion_campaign,
    create_rate_plan,
    get_rate_calendar_dashboard,
    get_rate_plan,
    get_room_performance_dashboard,
    hotel_rates_overview,
    list_property_campaigns,
    module_status,
    save_hotel_rate,
    toggle_promotion_campaign,
    update_promotion_campaign,
)

from src.app.security.dependencies import require_permission


router = APIRouter(prefix="/modules/revenue", tags=["modules-revenue"])
api_router = APIRouter(prefix="/api/management", tags=["management-revenue-api"])


@router.get("/status", response_model=ModuleStatus)
def revenue_status() -> ModuleStatus:
    return module_status()


@api_router.get("/rates")
def rates_api(prop_id: int = Query(..., ge=1), current_user: dict = Depends(require_permission("rates.read"))):
    return hotel_rates_overview(prop_id)


@api_router.get("/rates/analytics/room-performance")
def room_performance_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    room_type_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("reports.rates.adr.read")),
):
    """Dashboard táctico R1.2: ADR por fecha, tipo de habitación y canal.

    Lee exclusivamente ``kpi_room_performance_daily`` (agregado por día × hotel
    × tipo × divisa × canal). Devuelve resumen (ADR/RevPAR/ocupación), serie
    diaria y filas paginadas. Filtros de tipo/canal solo afectan la grilla.
    """
    try:
        return get_room_performance_dashboard(
            prop_id=prop_id,
            date_from=date_from,
            date_to=date_to,
            days=days,
            room_type_id=room_type_id,
            channel=channel,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/rates/analytics/rate-calendar")
def rate_calendar_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    plan_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=90, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("reports.rates.calendar.read")),
):
    """Dashboard simple R2.2: días con tarifa vs huecos (Mongo).

    Lee ``hotel_rate_calendar`` + ``rate_plans`` directamente desde Mongo.
    Devuelve resumen (planes, tarifa media, días cerrados, huecos), serie
    diaria y filas paginadas para la grilla del patrón Z.
    """
    try:
        return get_rate_calendar_dashboard(
            prop_id=prop_id,
            plan_id=plan_id,
            date_from=date_from,
            date_to=date_to,
            days=days,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/rates/options")
def rates_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_permission("rates.read")),
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


@api_router.get("/rates/plans/{plan_id}")
def get_rate_plan_api(plan_id: str, current_user: dict = Depends(require_permission("rates.read"))):
    """Get a single rate plan by its rate_plan_id."""
    result = get_rate_plan(plan_id)
    if result is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Plan tarifario no encontrado")
    return result


@api_router.post("/rates/plans", status_code=http_status.HTTP_201_CREATED)
def create_rate_plan_api(payload: dict = Body(...), current_user: dict = Depends(require_permission("rates.manage"))):
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
def save_rate_calendar_api(payload: dict = Body(...), current_user: dict = Depends(require_permission("rates.update"))):
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


# ──────── Promociones (SPEC 021) ────────


@api_router.get("/promotions")
def list_promotions_api(prop_id: int = Query(..., ge=1), current_user: dict = Depends(require_permission("promotions.read"))):
    """RF-004: Listar campañas promocionales por propiedad."""
    try:
        return list_property_campaigns(prop_id)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/promotions", status_code=http_status.HTTP_201_CREATED)
def create_promotion_api(payload: dict = Body(...), current_user: dict = Depends(require_permission("promotions.manage"))):
    """RF-001/RF-002: Crear campaña con N cupones."""
    try:
        return create_promotion_campaign(
            prop_id=payload.get("prop_id"),
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            discount_percent=payload.get("discount_percent"),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            coupon_count=int(payload.get("coupon_count", 10)),
            coupon_code=str(payload.get("coupon_code") or ""),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.put("/promotions/{campaign_id}")
def update_promotion_api(campaign_id: str, payload: dict = Body(...), current_user: dict = Depends(require_permission("promotions.manage"))):
    """RF-006: Editar campaña promocional."""
    try:
        return update_promotion_campaign(
            campaign_id,
            name=payload.get("name"),
            description=payload.get("description"),
            discount_percent=payload.get("discount_percent"),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            is_active=payload.get("is_active"),
            coupon_count=payload.get("coupon_count"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/promotions/{campaign_id}/toggle")
def toggle_promotion_api(campaign_id: str, current_user: dict = Depends(require_permission("promotions.manage"))):
    """RF-003: Activar/desactivar campaña."""
    try:
        return toggle_promotion_campaign(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
