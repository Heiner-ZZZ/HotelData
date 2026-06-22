from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Body, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from src.app.template_utils import templates

from src.app.modules.billing.schemas import InvoiceCreate, ModuleStatus, PaymentCreate
from src.app.modules.billing.service import (
    cancel_invoice,
    create_invoice,
    create_payment,
    get_invoice,
    get_payment,
    list_invoices,
    list_payments,
    module_status,
    refund_payment,
)

router = APIRouter(prefix="/modules/billing", tags=["modules-billing"])
api_router = APIRouter(prefix="/api/billing", tags=["billing-api"])
web_router = APIRouter(tags=["billing-web"])
def _page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    return f"{request.url.path}?{urlencode(params)}"


@router.get("/status", response_model=ModuleStatus)
def billing_module_status():
    return module_status()


# --- Web routes ---

@web_router.get("/billing")
def billing_list(request: Request, page: int = Query(default=1, ge=1)):
    results = list_invoices(page=page, page_size=20)
    return templates.TemplateResponse(
        request,
        "billing/list.html",
        {
            "results": results,
            "prev_url": _page_url(request, results["page"] - 1) if results["has_prev"] else None,
            "next_url": _page_url(request, results["page"] + 1) if results["has_next"] else None,
        },
    )


@web_router.post("/billing/{invoice_id}/cancel")
def billing_cancel_web(invoice_id: str):
    try:
        result = cancel_invoice(invoice_id)
        if result is None:
            return RedirectResponse(
                f"/billing/{invoice_id}?error=No+se+pudo+cancelar+la+factura",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(f"/billing/{invoice_id}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        return RedirectResponse(
            f"/billing/{invoice_id}?error={exc}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@web_router.get("/billing/{invoice_id}")
def billing_detail(request: Request, invoice_id: str):
    invoice = get_invoice(invoice_id)
    if invoice is None:
        return templates.TemplateResponse(
            request,
            "billing/detail.html",
            {"invoice": None, "payments": []},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    # Note: filtered by booking_id (not invoice_id) for now — captures all
    # payments tied to the reservation, not just ones linked to this invoice.
    payments = list_payments(booking_id=invoice.get("booking_id", ""), page_size=50)
    return templates.TemplateResponse(
        request,
        "billing/detail.html",
        {
            "invoice": invoice,
            "payments": payments["items"],
        },
    )


# --- Invoices ---

@api_router.post("/invoices", status_code=201)
def create_invoice_api(payload: InvoiceCreate = Body(...)):
    result = create_invoice(payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la factura (booking inválido)")
    return result


@api_router.get("/invoices")
def list_invoices_api(
    booking_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return list_invoices(booking_id=booking_id, status=status_filter, page=page, page_size=page_size)


@api_router.get("/invoices/{invoice_id}")
def get_invoice_api(invoice_id: str):
    result = get_invoice(invoice_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return result


@api_router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice_api(invoice_id: str):
    result = cancel_invoice(invoice_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo cancelar la factura")
    return result


# --- Payments ---

@api_router.post("/payments", status_code=201)
def create_payment_api(payload: PaymentCreate = Body(...)):
    result = create_payment(payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo registrar el pago (booking inválido)")
    return result


@api_router.get("/payments")
def list_payments_api(
    booking_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return list_payments(booking_id=booking_id, page=page, page_size=page_size)


@api_router.get("/payments/{payment_id}")
def get_payment_api(payment_id: str):
    result = get_payment(payment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return result


@api_router.post("/payments/{payment_id}/refund")
def refund_payment_api(payment_id: str):
    result = refund_payment(payment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo reembolsar el pago")
    return result
