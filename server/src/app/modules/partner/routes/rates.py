"""Partner rates routes — plans, seasonal rules, calendar, promotions, and contracts."""

from __future__ import annotations

from fastapi import Body, Query

from fastapi import Depends

from src.app.modules.partner.routes import api_router
from src.app.security.dependencies import require_permission

from src.app.modules.partner.routes.rates_impl import (
    get_hotel_rates_detail,
    get_rates_options,
    create_plan,
    update_plan,
    delete_plan,
    get_seasonal_rules,
    create_seasonal,
    update_seasonal,
    delete_seasonal,
    update_calendar_entry,
    batch_update_calendar,
    generate_calendar,
    get_contracts,
    create_contract,
    update_contract,
    delete_contract,
    validate_contract,
    create_promotion,
)


@api_router.get("/rates")
def rates_api(prop_id: int = Query(..., ge=1)):
    return get_hotel_rates_detail(prop_id)


@api_router.get("/rates/options")
def rates_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_permission("rates.read")),
):
    return get_rates_options(prop_id, q, page, page_size, current_user)


@api_router.post("/rates/plans", status_code=201)
def rates_plan_create_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.manage")),
):
    return create_plan(payload, current_user)


@api_router.put("/rates/plans/{plan_id}")
def rates_plan_update_api(
    plan_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.update")),
):
    return update_plan(plan_id, payload, current_user)


@api_router.delete("/rates/plans/{plan_id}")
def rates_plan_delete_api(
    plan_id: str,
    current_user: dict = Depends(require_permission("rates.manage")),
):
    return delete_plan(plan_id, current_user)


@api_router.get("/rates/seasonal-rules")
def rates_seasonal_rules_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    rate_plan_id: str | None = Query(default=None),
):
    return get_seasonal_rules(prop_id=prop_id, rate_plan_id=rate_plan_id)


@api_router.post("/rates/seasonal-rules", status_code=201)
def rates_seasonal_rule_create_api(payload: dict = Body(...)):
    return create_seasonal(payload)


@api_router.put("/rates/seasonal-rules/{rule_id}")
def rates_seasonal_rule_update_api(rule_id: str, payload: dict = Body(...)):
    return update_seasonal(rule_id, payload)


@api_router.delete("/rates/seasonal-rules/{rule_id}")
def rates_seasonal_rule_delete_api(rule_id: str):
    return delete_seasonal(rule_id)


@api_router.post("/rates/calendar")
def rates_calendar_update_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.update")),
):
    return update_calendar_entry(payload, current_user)


@api_router.post("/rates/calendar/batch")
def rates_calendar_batch_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.update")),
):
    """Batch update rate calendar for a date range."""
    return batch_update_calendar(payload, current_user)


@api_router.post("/rates/calendar/generate")
def rates_calendar_generate_api(payload: dict = Body(...)):
    """Generate calendar entries from base_price + seasonal rules."""
    return generate_calendar(payload)


@api_router.post("/rates/promotions", status_code=201)
def rates_promotion_create_api(payload: dict = Body(...)):
    return create_promotion(payload)


# ── Corporate contracts ──


@api_router.get("/rates/contracts")
def rates_contracts_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = Query(default=None),
):
    return get_contracts(prop_id=prop_id, is_active=is_active)


@api_router.post("/rates/contracts", status_code=201)
def rates_contract_create_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.manage")),
):
    return create_contract(payload, current_user)


@api_router.put("/rates/contracts/{contract_id}")
def rates_contract_update_api(
    contract_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.update")),
):
    return update_contract(contract_id, payload, current_user)


@api_router.delete("/rates/contracts/{contract_id}")
def rates_contract_delete_api(
    contract_id: str,
    current_user: dict = Depends(require_permission("rates.manage")),
):
    return delete_contract(contract_id, current_user)


@api_router.post("/rates/contracts/validate")
def rates_contract_validate_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rates.read")),
):
    """Validate a corporate contract code for a given property and room type."""
    return validate_contract(payload)
