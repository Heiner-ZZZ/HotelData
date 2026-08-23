"""Routes for hotel products, add-on line items on bookings, and platform earnings."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services._reports import (
    compute_cogs_report,
    compute_margin_report,
    compute_stock_value_report,
)
from src.app.modules.partner.services.hotel_products import (
    add_booking_line_item,
    create_hotel_product,
    delete_hotel_product,
    get_platform_earnings_summary,
    get_weekly_earnings,
    list_booking_line_items,
    list_hotel_products,
    list_platform_earnings,
    mark_commission_paid,
    remove_booking_line_item,
    restock_product,
    update_hotel_product,
)
from src.app.security.dependencies import require_permission, require_prop_permission
from src.database.connection import get_database

router = APIRouter(prefix="/api/management", tags=["products"])


class HotelProductResponse(BaseModel):
    """Wire-level response model for a hotel product.

    Maps the MongoDB ``_id`` field to the JSON ``id`` field and uses
    ``ObjectIdStr`` to coerce ObjectId to a plain string. The
    ``populate_by_name=True`` config lets the model accept both
    ``_id`` (MongoDB shape) and ``id`` (already-stringified) inputs.
    """

    model_config = ConfigDict(populate_by_name=True)

    # FastAPI's jsonable_encoder uses by_alias=True by default, so the
    # serialization_alias must be set explicitly to emit ``id`` on the
    # wire even though the MongoDB field is ``_id``.
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    hotel_id: ObjectIdStr | None = None
    product_id: str
    name: str
    description: str = ""
    category: str = "Otros"
    type: str = "retail"
    cost_price: float = 0.0
    unit_price: float = 0.0
    quantity_available: int = 0
    default_supplier: str | None = None
    supplier_sku: str | None = None
    par_level: int | None = None
    is_active: bool = True
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ─── Report: Margin ───────────────────────────────────────────────────────


class MarginSummaryResponse(BaseModel):
    """Mirror of ``compute_margin_report()`` summary dict in
    ``server/src/app/modules/partner/services/_reports.py`` — KEEP IN SYNC.

    ``active_products`` was intentionally dropped: the report filter already
    excludes archived + inactive, so the count would be redundant with
    ``total_products``. If a separate inactive counter becomes useful,
    compute it against the unfiltered query.

    Frontend mirror: ``frontend/src/app/features/products/models/products-report.dto.ts``
    → ``MarginSummaryDto``. If you add / remove / rename a field here,
    update the TS interface in the same commit.
    """
    total_products: int
    total_margin_abs: float
    total_unit_price: float
    global_margin_pct: float


class MarginReportItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    product_id: str
    name: str
    category: str
    type: str
    cost_price: float
    unit_price: float
    margin_abs: float
    margin_pct: float
    quantity_available: int


class MarginReportResponse(BaseModel):
    summary: MarginSummaryResponse
    items: list[MarginReportItemResponse]


# ─── Report: COGS ─────────────────────────────────────────────────────────

class CogsSummaryResponse(BaseModel):
    total_cogs: float
    units_sold: int
    distinct_products_sold: int
    # Sum (across products) of units that could not be matched to a layer.
    # Non-zero means either the backfill migration hasn't run yet, or some
    # products are over-sold vs the available layer history.
    fallback_units_across_products: int = 0


class LayerBreakdownItemResponse(BaseModel):
    """One layer-touched entry inside a product's COGS row.

    Populated only when ``method in (fifo, lifo)``. For ``approx`` the
    single breakdown entry uses ``source="approx_fallback"`` and an
    empty ``layer_id`` since there is no layer traversal.

    For ``source == "fallback_layer_missing"`` indicates the product ran
    out of layers mid-period; cost was imputed from the current
    ``hotel_products.cost_price``. This is the "Fase 5 last-purchase
    approximation" mapped onto the new wire shape.
    """
    layer_id: str | None = None
    units_consumed: float
    cost_per_unit: float
    source: str  # "layer" | "approx_fallback" | "fallback_layer_missing"


class CogsReportItemResponse(BaseModel):
    """Per-product COGS row.

    Intentionally omits ``id`` (Mongo ``_id``) — the COGS aggregation joins
    semantically on ``product_id`` (the line_items.product_id from
    booking_orders), not on the catalog's ObjectId. The catalog reuses
    ``product_id`` as the stable cross-collection reference, so emitting
    the raw ``_id`` here would either be redundant or misleading (it would
    be the "synthetic row id" of the aggregation, not the product's id).

    If a future drill-down needs the catalog ObjectId, fetch it from
    ``hotel_products.find_one({"product_id": row.product_id})``.
    """
    product_id: str
    name: str
    category: str
    units_sold: int
    avg_unit_cost: float
    cogs: float
    layer_breakdown: list[LayerBreakdownItemResponse] = []


class CogsReportResponse(BaseModel):
    # Echo of the requested method (fifo|lifo|approx). Useful for clients
    # that cache the response by URL but want to confirm which method
    # produced the breakdown they are rendering.
    method: str
    period: str
    period_start: str
    period_end: str
    summary: CogsSummaryResponse
    items: list[CogsReportItemResponse]  


# ─── Report: Stock Value ──────────────────────────────────────────────────


class StockValueSummaryResponse(BaseModel):
    total_stock_value: float
    total_units: int
    distinct_products: int


class StockCategorySummary(BaseModel):
    category: str
    total_value: float
    units: int
    products: int


class StockValueItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    product_id: str
    name: str
    category: str
    quantity_available: int
    cost_price: float
    stock_value: float


class StockValueReportResponse(BaseModel):
    as_of: str
    summary: StockValueSummaryResponse
    by_category: list[StockCategorySummary]
    items: list[StockValueItemResponse]  # côdigo de mediciones


# Rebuild Pydantic v2 models to resolve string-lazy annotations from
# ``from __future__ import annotations``. Without this explicit rebuild,
# FastAPI's ``TypeAdapter`` binding at ``response_model=…`` raises
# ``pydantic.errors.PydanticUserError`` (``TypeAdapter[…CogsReportResponse…]
# is not fully defined``) on the first request to ANY of these endpoints.
# Each model carries an ``id: ObjectIdStr = Field(validation_alias="_id")``
# whose annotation is a ``typing.Annotated`` forward ref — Pydantic v2 cannot
# resolve those lazily.
HotelProductResponse.model_rebuild()
MarginReportResponse.model_rebuild()
CogsReportResponse.model_rebuild()
StockValueReportResponse.model_rebuild()


# ─── Hotel Products CRUD ───────────────────────────────────────────────


@router.get("/products/hotels/{prop_id}")
def list_products(
    prop_id: int,
    current_user: dict = Depends(require_prop_permission("properties.read")),
):
    return {"items": list_hotel_products(require_prop_id(prop_id))}


@router.post("/products/hotels/{prop_id}", response_model=HotelProductResponse)
def create_product(
    prop_id: int,
    payload: dict[str, Any] = Body(...),
    current_user: dict = Depends(require_prop_permission("properties.update")),
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
    current_user: dict = Depends(require_prop_permission("properties.update")),
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
    current_user: dict = Depends(require_prop_permission("properties.update")),
):
    ok = delete_hotel_product(require_prop_id(prop_id), product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}


@router.post("/products/hotels/{prop_id}/{product_id}/restock")
def restock(
    prop_id: int,
    product_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: dict = Depends(require_prop_permission("inventory.products.cost.manage")),
):
    """Registra reposición manual de stock con costo + posting al ledger.

    Body fields:
      qty (float, required)           — units to add; must be > 0.
      unit_cost (float, required)     — wholesale cost per unit; must be >= 0.
      supplier_name (str, optional)   — overrides hotel_products.default_supplier.
      invoice_ref (str, optional)     — free-text bill/receipt number (legacy).
      invoice_id (str, optional)      — expense invoice ObjectId; resolves the
                                        invoice for this prop and stores its
                                        ``_id`` as the reference (real FK).
                                        Preferred over invoice_ref. Unknown or
                                        cross-property ids → 400.
                                      If neither is provided, a manual marker
                                      is generated.

    Side effects:
      1. Increments hotel_products.quantity_available by qty.
      2. Sets hotel_products.cost_price = unit_cost (last-purchase model).
      3. Records last_purchase_at / last_purchase_qty / last_purchase_invoice_ref.
      4. Posts balanced DR 1050 (Inventario) / CR 2010 (Ctas por Pagar Proveedores).
      5. Writes audit_log row via outbox.

    Permission: ``inventory.products.cost.manage`` (gerente_hotel only).
    Receptionists (``recepcionista``) cannot call this endpoint.
    """
    try:
        result = restock_product(
            require_prop_id(prop_id),
            product_id,
            qty=float(payload.get("qty", 0)),
            unit_cost=float(payload.get("unit_cost", 0)),
            supplier_name=str(payload.get("supplier_name", "")),
            invoice_ref=str(payload.get("invoice_ref", "")),
            invoice_id=str(payload.get("invoice_id", "")),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result


# ─── Reports (manager-only: cost_price is gated) ──────────────────────────


@router.get("/products/reports/margin", response_model=MarginReportResponse)
def get_margin_report(
    prop_id: int,
    current_user: dict = Depends(require_prop_permission("inventory.products.cost.read")),
):
    """Return the margin report for a hotel: per-product margin %/abs + summary."""
    return compute_margin_report(require_prop_id(prop_id))


@router.get("/products/reports/cogs", response_model=CogsReportResponse)
def get_cogs_report(
    prop_id: int,
    period: str = Query(default="month", pattern="^(month|week|year|all)$"),
    method: str = Query(
        default="fifo",
        pattern="^(fifo|lifo|approx)$",
        description=(
            "Layer drain strategy. ``fifo`` (GAAP-aligned, default) drains "
            "oldest layers first; ``lifo`` drains newest first; ``approx`` "
            "multiplies by the current ``hotel_products.cost_price`` snapshot "
            "(backwards-compatible with Fase 5, useful before the inventory "
            "layers migration is run)."
        ),
    ),
    current_user: dict = Depends(require_prop_permission("inventory.products.cost.read")),
):
    """Return the Cost of Goods Sold report for a period.

    Fase 6: layer-aware drain via ``drain_layers_for_sale``. Method param
    selects drain order; period selects the date window of line items
    considered. Default ``fifo`` matches GAAP inventory cost flow.
    """
    return compute_cogs_report(
        require_prop_id(prop_id),
        period,
        method=method,
    )


@router.get("/products/reports/stock-value", response_model=StockValueReportResponse)
def get_stock_value_report(
    prop_id: int,
    current_user: dict = Depends(require_prop_permission("inventory.products.cost.read")),
):
    """Return the current stock value (Σ qty × cost_price) per category."""
    return compute_stock_value_report(require_prop_id(prop_id))


# ─── Booking Line Items (add-on products) ──────────────────────────────


def _require_booking_same_hotel(db, booking_id: str, prop_id: int | None) -> None:
    """404 (no 403) si el booking no pertenece al hotel pedido — deny cross-hotel.

    Migración E: los line-items de reserva se resuelven por booking_id; el
    hotel viene del query y el booking debe pertenecerle.
    """
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id}, {"prop_id": 1}
    )
    if not booking or booking.get("prop_id") != prop_id:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")


@router.get("/products/bookings/{booking_id}/line-items")
def get_line_items(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    return {"items": list_booking_line_items(booking_id)}


@router.post("/products/bookings/{booking_id}/line-items")
def add_line_item(
    booking_id: str,
    payload: dict[str, Any] = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
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
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
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


@router.get("/products/earnings/weekly")
def earnings_weekly(
    weeks: int = Query(default=12, ge=4, le=52),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Weekly earnings aggregation for charting.

    Supports date range filtering via start_date / end_date (ISO format).
    Falls back to last N weeks if no dates provided.
    """
    from datetime import datetime

    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD).")

    return {"items": get_weekly_earnings(weeks=weeks, start_date=start_dt, end_date=end_dt)}


@router.put("/products/earnings/{booking_id}/pay")
def mark_paid(
    booking_id: str,
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Mark a pending commission as paid."""
    result = mark_commission_paid(booking_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Comisión no encontrada o ya fue pagada.",
        )
    return result
