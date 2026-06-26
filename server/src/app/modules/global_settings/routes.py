from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.app.modules.global_settings.service import (
    delete_commission_rate,
    delete_tax_rate,
    get_hotel_global_data,
    get_platform_config,
    list_commission_rates,
    list_global_hotels,
    list_tax_rates,
    update_hotel_global_data,
    update_platform_config,
    upsert_commission_rate,
    upsert_tax_rate,
)
from src.app.security.dependencies import require_permission

api_router = APIRouter(prefix="/api/admin/global-settings", tags=["admin-global"])


# ─── Platform Config ────────────────────────────────────────────────────


@api_router.get("/config")
def get_config(current_user: dict = Depends(require_permission("users.manage"))):
    return get_platform_config()


@api_router.put("/config")
def update_config(
    body: dict[str, Any],
    current_user: dict = Depends(require_permission("users.manage")),
):
    default_commission_pct = body.get("default_commission_pct")
    default_iva_pct = body.get("default_iva_pct")
    username = current_user.get("username") or current_user.get("display_name") or "admin"
    return update_platform_config(
        default_commission_pct=default_commission_pct,
        default_iva_pct=default_iva_pct,
        updated_by=username,
    )


# ─── Hotels Global Data ─────────────────────────────────────────────────


@api_router.get("/hotels")
def list_hotels(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_permission("users.manage")),
):
    return list_global_hotels(q=q, page=page, page_size=page_size)


@api_router.get("/hotels/{prop_id}")
def get_hotel(
    prop_id: int,
    current_user: dict = Depends(require_permission("users.manage")),
):
    data = get_hotel_global_data(prop_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Hotel no encontrado")
    return data


@api_router.put("/hotels/{prop_id}")
def update_hotel(
    prop_id: int,
    body: dict[str, Any],
    current_user: dict = Depends(require_permission("users.manage")),
):
    username = current_user.get("username") or current_user.get("display_name") or "admin"
    data = update_hotel_global_data(
        prop_id=prop_id,
        country_name=body.get("country_name"),
        city=body.get("city"),
        province=body.get("province"),
        hotel_group=body.get("hotel_group"),
        updated_by=username,
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Hotel no encontrado")
    return {"ok": True, "hotel": data}


# ─── Tax Rates (IVA per country) ────────────────────────────────────────


@api_router.get("/tax-rates")
def list_taxes(current_user: dict = Depends(require_permission("users.manage"))):
    return {"items": list_tax_rates()}


@api_router.post("/tax-rates")
def create_tax_rate(
    body: dict[str, Any],
    current_user: dict = Depends(require_permission("users.manage")),
):
    country_id = body.get("country_id")
    iva_pct = body.get("iva_pct")
    if country_id is None or iva_pct is None:
        raise HTTPException(status_code=400, detail="country_id e iva_pct son requeridos")
    username = current_user.get("username") or "admin"
    result = upsert_tax_rate(
        country_id=int(country_id),
        iva_pct=float(iva_pct),
        country_name=str(body.get("country_name", "")),
        updated_by=username,
    )
    return {"ok": True, "tax_rate": result}


@api_router.put("/tax-rates/{country_id}")
def update_tax_rate(
    country_id: int,
    body: dict[str, Any],
    current_user: dict = Depends(require_permission("users.manage")),
):
    iva_pct = body.get("iva_pct")
    if iva_pct is None:
        raise HTTPException(status_code=400, detail="iva_pct es requerido")
    username = current_user.get("username") or "admin"
    result = upsert_tax_rate(
        country_id=country_id,
        iva_pct=float(iva_pct),
        country_name=str(body.get("country_name", "")),
        updated_by=username,
    )
    return {"ok": True, "tax_rate": result}


@api_router.delete("/tax-rates/{country_id}")
def remove_tax_rate(
    country_id: int,
    current_user: dict = Depends(require_permission("users.manage")),
):
    deleted = delete_tax_rate(country_id)
    return {"ok": deleted, "message": "Tasa de IVA eliminada" if deleted else "No se encontró la tasa de IVA"}


# ─── Commission Rates (per hotel override) ──────────────────────────────


@api_router.get("/commission-rates")
def list_commissions(current_user: dict = Depends(require_permission("users.manage"))):
    return {"items": list_commission_rates()}


@api_router.post("/commission-rates")
def create_commission_rate(
    body: dict[str, Any],
    current_user: dict = Depends(require_permission("users.manage")),
):
    prop_id = body.get("prop_id")
    commission_pct = body.get("commission_pct")
    if prop_id is None or commission_pct is None:
        raise HTTPException(status_code=400, detail="prop_id y commission_pct son requeridos")
    username = current_user.get("username") or "admin"
    result = upsert_commission_rate(
        prop_id=int(prop_id),
        commission_pct=float(commission_pct),
        updated_by=username,
    )
    return {"ok": True, "commission": result}


@api_router.put("/commission-rates/{prop_id}")
def update_commission_rate(
    prop_id: int,
    body: dict[str, Any],
    current_user: dict = Depends(require_permission("users.manage")),
):
    commission_pct = body.get("commission_pct")
    if commission_pct is None:
        raise HTTPException(status_code=400, detail="commission_pct es requerido")
    username = current_user.get("username") or "admin"
    result = upsert_commission_rate(
        prop_id=prop_id,
        commission_pct=float(commission_pct),
        updated_by=username,
    )
    return {"ok": True, "commission": result}


@api_router.delete("/commission-rates/{prop_id}")
def remove_commission_rate(
    prop_id: int,
    current_user: dict = Depends(require_permission("users.manage")),
):
    deleted = delete_commission_rate(prop_id)
    return {"ok": deleted, "message": "Comisión eliminada" if deleted else "No se encontró la comisión"}
