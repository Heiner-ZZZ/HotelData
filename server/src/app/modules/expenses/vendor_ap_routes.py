"""Hotel-scoped Vendor AP routes, separate from Guest AR billing routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from src.app.modules.expenses.schemas import VendorBillListResponse, VendorBillResponse
from src.app.modules.expenses.service.vendor_ap import (
    get_vendor_bill,
    list_vendor_bills,
    vendor_ap_summary,
)
from src.app.security.dependencies import require_prop_permission

api_router = APIRouter(
    prefix="/api/hotels/{prop_id}/vendor-ap",
    tags=["vendor-ap"],
)

_require_vendor_ap_read = require_prop_permission("revenue.read")

VendorBillResponse.model_rebuild()
VendorBillListResponse.model_rebuild()


@api_router.get("/invoices", response_model=VendorBillListResponse)
def list_vendor_ap_invoices(
    prop_id: int = Path(..., ge=1),
    status: str | None = Query(default=None),
    vendor: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_require_vendor_ap_read),  # noqa: B008
) -> VendorBillListResponse:
    try:
        return VendorBillListResponse.model_validate(list_vendor_bills(
            prop_id=prop_id,
            status=status,
            vendor=vendor,
            page=page,
            page_size=page_size,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.get("/invoices/{invoice_id}", response_model=VendorBillResponse)
def get_vendor_ap_invoice(
    prop_id: int = Path(..., ge=1),
    invoice_id: str = Path(...),
    current_user: dict = Depends(_require_vendor_ap_read),  # noqa: B008
) -> VendorBillResponse:
    result = get_vendor_bill(prop_id=prop_id, invoice_id=invoice_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Factura de proveedor no encontrada en este hotel")
    return VendorBillResponse.model_validate(result)


@api_router.get("/summary")
def get_vendor_ap_summary(
    prop_id: int = Path(..., ge=1),
    current_user: dict = Depends(_require_vendor_ap_read),  # noqa: B008
) -> dict[str, Any]:
    return vendor_ap_summary(prop_id)
