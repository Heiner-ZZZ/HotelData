"""Partner rates routes — plans, seasonal rules, calendar, promotions, and contracts.

Migración E (2026-08): toda ruta de OPERACIÓN de tarifas gatea con
``require_prop_permission`` (deny-by-default por hotel: sin role_assignment
→ 403; sin ``prop_id`` → 400; documento de otro hotel → 404). Solo el picker
multi-hotel ``GET /rates/options`` queda global (vista de gerencia
multi-hotel: lista los hoteles accesibles del usuario, sin operar uno
concreto).
"""

from __future__ import annotations

from fastapi import Body, Depends, HTTPException, Query

from src.app.modules.partner.routes import api_router
from src.app.security.dependencies import require_permission, require_prop_permission

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


def _check_body_prop_id(query_prop_id: int | None, payload: dict) -> None:
    """Consistencia gate(query) ↔ body: el prop_id del query es autoritativo."""
    try:
        body_prop_id = int(str(payload.get("prop_id") or 0))
    except (TypeError, ValueError):
        body_prop_id = 0
    if query_prop_id is not None and body_prop_id != query_prop_id:
        raise HTTPException(status_code=400, detail="prop_id del query y del body no coinciden")


def _require_same_hotel(db, collection: str, query: dict, prop_id: int | None) -> None:
    """404 (no 403) si el documento pertenece a otro hotel — deny cross-hotel.

    El gate ya validó que el usuario opera el hotel ``prop_id``; este chequeo
    evita que un id de otro hotel devuelva 404/409/200 sobre datos ajenos.
    """
    doc = db[collection].find_one(query, {"prop_id": 1})
    if doc is None or doc.get("prop_id") != prop_id:
        raise HTTPException(status_code=404, detail="Registro no encontrado")


@api_router.get("/rates")
def rates_api(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_prop_permission("rates.read")),
):
    return get_hotel_rates_detail(prop_id)


@api_router.get("/rates/options")
def rates_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_permission("rates.read")),
):
    """Vista MULTI-HOTEL del picker de Tarifas (excepción global documentada).

    Sin ``prop_id`` lista los hoteles accesibles del usuario (filtrado por
    ``list_partner_hotels(user=...)``) — no opera un hotel concreto. Con
    ``prop_id`` añade los rate plans del hotel para el selector de planes.
    """
    return get_rates_options(prop_id, q, page, page_size, current_user)


@api_router.post("/rates/plans", status_code=201)
def rates_plan_create_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    _check_body_prop_id(query_prop_id, payload)
    return create_plan(payload, current_user)


@api_router.put("/rates/plans/{plan_id}")
def rates_plan_update_api(
    plan_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.update")),
):
    from src.database.connection import get_database
    _require_same_hotel(get_database(), "rate_plans", {"rate_plan_id": plan_id}, query_prop_id)
    return update_plan(plan_id, payload, current_user)


@api_router.delete("/rates/plans/{plan_id}")
def rates_plan_delete_api(
    plan_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    from src.database.connection import get_database
    _require_same_hotel(get_database(), "rate_plans", {"rate_plan_id": plan_id}, query_prop_id)
    return delete_plan(plan_id, current_user)


@api_router.get("/rates/seasonal-rules")
def rates_seasonal_rules_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    rate_plan_id: str | None = Query(default=None),
    current_user: dict = Depends(require_prop_permission("rates.read")),
):
    return get_seasonal_rules(prop_id=prop_id, rate_plan_id=rate_plan_id)


@api_router.post("/rates/seasonal-rules", status_code=201)
def rates_seasonal_rule_create_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    _check_body_prop_id(query_prop_id, payload)
    return create_seasonal(payload)


@api_router.put("/rates/seasonal-rules/{rule_id}")
def rates_seasonal_rule_update_api(
    rule_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    from src.database.connection import get_database
    _require_same_hotel(get_database(), "rate_rules", {"rule_id": rule_id}, query_prop_id)
    return update_seasonal(rule_id, payload)


@api_router.delete("/rates/seasonal-rules/{rule_id}")
def rates_seasonal_rule_delete_api(
    rule_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    from src.database.connection import get_database
    _require_same_hotel(get_database(), "rate_rules", {"rule_id": rule_id}, query_prop_id)
    return delete_seasonal(rule_id)


@api_router.post("/rates/calendar")
def rates_calendar_update_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.update")),
):
    _check_body_prop_id(query_prop_id, payload)
    return update_calendar_entry(payload, current_user)


@api_router.post("/rates/calendar/batch")
def rates_calendar_batch_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.update")),
):
    """Batch update rate calendar for a date range."""
    _check_body_prop_id(query_prop_id, payload)
    return batch_update_calendar(payload, current_user)


@api_router.post("/rates/calendar/generate")
def rates_calendar_generate_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    """Generate calendar entries from base_price + seasonal rules."""
    _check_body_prop_id(query_prop_id, payload)
    return generate_calendar(payload)


@api_router.post("/rates/promotions", status_code=201)
def rates_promotion_create_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    """Alias legacy del form de Tarifas (el CRUD canónico vive en revenue)."""
    _check_body_prop_id(query_prop_id, payload)
    return create_promotion(payload)


# ── Corporate contracts ──


@api_router.get("/rates/contracts")
def rates_contracts_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = Query(default=None),
    current_user: dict = Depends(require_prop_permission("rates.read")),
):
    return get_contracts(prop_id=prop_id, is_active=is_active)


@api_router.post("/rates/contracts", status_code=201)
def rates_contract_create_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    _check_body_prop_id(query_prop_id, payload)
    return create_contract(payload, current_user)


@api_router.put("/rates/contracts/{contract_id}")
def rates_contract_update_api(
    contract_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.update")),
):
    from src.database.connection import get_database
    _require_same_hotel(get_database(), "corporate_contracts", {"contract_id": contract_id}, query_prop_id)
    return update_contract(contract_id, payload, current_user)


@api_router.delete("/rates/contracts/{contract_id}")
def rates_contract_delete_api(
    contract_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.manage")),
):
    from src.database.connection import get_database
    _require_same_hotel(get_database(), "corporate_contracts", {"contract_id": contract_id}, query_prop_id)
    return delete_contract(contract_id, current_user)


@api_router.post("/rates/contracts/validate")
def rates_contract_validate_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("rates.read")),
):
    """Validate a corporate contract code for a given property and room type."""
    _check_body_prop_id(query_prop_id, payload)
    return validate_contract(payload)
