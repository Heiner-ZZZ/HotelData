"""Routes for hotel products, add-on line items on bookings, and platform earnings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services.hotel_products import (
    add_booking_line_item,
    create_hotel_product,
    delete_hotel_product,
    get_platform_earnings_summary,
    list_booking_line_items,
    list_hotel_products,
    list_platform_earnings,
    record_platform_earnings,
    remove_booking_line_item,
    update_hotel_product,
)
from src.app.security.dependencies import require_login, require_permission

router = APIRouter(prefix="/api/management", tags=["products"])


# ─── Hotel Products CRUD ───────────────────────────────────────────────


@router.get("/products/hotels/{prop_id}")
def list_products(
    prop_id: int,
    current_user: dict = Depends(require_login),
):
    return {"items": list_hotel_products(require_prop_id(prop_id))}


@router.post("/products/hotels/{prop_id}")
def create_product(
    prop_id: int,
    payload: dict[str, Any] = Body(...),
    current_user: dict = Depends(require_login),
):
    try:
        result = create_hotel_product(
            require_prop_id(prop_id),
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            unit_price=float(payload.get("unit_price", 0)),
            quantity_available=int(payload.get("quantity_available", 0)),
            category=str(payload.get("category", "Otros")),
            is_active=bool(payload.get("is_active", True)),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.put("/products/hotels/{prop_id}/{product_id}")
def update_product(
    prop_id: int,
    product_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: dict = Depends(require_login),
):
    result = update_hotel_product(
        require_prop_id(prop_id),
        product_id,
        name=payload.get("name"),
        description=payload.get("description"),
        unit_price=payload.get("unit_price"),
        quantity_available=payload.get("quantity_available"),
        category=payload.get("category"),
        is_active=payload.get("is_active"),
        changed_by=current_user.get("username", "system"),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.delete("/products/hotels/{prop_id}/{product_id}")
def delete_product(
    prop_id: int,
    product_id: str,
    current_user: dict = Depends(require_login),
):
    ok = delete_hotel_product(require_prop_id(prop_id), product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}


# ─── Booking Line Items (add-on products) ──────────────────────────────


@router.get("/products/bookings/{booking_id}/line-items")
def get_line_items(
    booking_id: str,
    current_user: dict = Depends(require_login),
):
    return {"items": list_booking_line_items(booking_id)}


@router.post("/products/bookings/{booking_id}/line-items")
def add_line_item(
    booking_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: dict = Depends(require_login),
):
    product_id = str(payload.get("product_id", ""))
    name = str(payload.get("name", ""))
    unit_price = float(payload.get("unit_price", 0))
    quantity = int(payload.get("quantity", 1))

    if not product_id or not name:
        raise HTTPException(status_code=400, detail="product_id and name are required")

    result = add_booking_line_item(
        booking_id,
        product_id=product_id,
        name=name,
        unit_price=unit_price,
        quantity=quantity,
        changed_by=current_user.get("username", "system"),
    )
    if result is None:
        raise HTTPException(status_code=400, detail="Booking not found or not in active status")
    return result


@router.delete("/products/bookings/{booking_id}/line-items/{item_id}")
def remove_line_item(
    booking_id: str,
    item_id: str,
    current_user: dict = Depends(require_login),
):
    ok = remove_booking_line_item(
        booking_id,
        item_id,
        changed_by=current_user.get("username", "system"),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Line item not found")
    return {"ok": True}


# ─── Platform Earnings ─────────────────────────────────────────────────


@router.get("/products/earnings/summary")
def earnings_summary(current_user: dict = Depends(require_permission("users.manage"))):
    return get_platform_earnings_summary()


@router.get("/products/earnings")
def earnings_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("users.manage")),
):
    return list_platform_earnings(page=page, page_size=page_size)
