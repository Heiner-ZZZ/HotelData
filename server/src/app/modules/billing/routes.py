from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query, status

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


@router.get("/status", response_model=ModuleStatus)
def billing_module_status():
    return module_status()


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
