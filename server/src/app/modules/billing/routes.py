from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.app.modules.billing.schemas import InvoiceCreate, ModuleStatus, PaymentCreate
from src.app.modules.billing.service import (
    add_line_item,
    cancel_invoice,
    close_folio,
    create_folio,
    create_invoice,
    create_payment,
    get_folio,
    get_folio_by_id,
    get_invoice,
    get_invoice_stats,
    get_payment,
    list_folios,
    list_invoices,
    list_payments,
    module_status,
    post_to_folio,
    refund_payment,
    remove_line_item,
    FOLIO_CATEGORIES,
)
from src.app.security.dependencies import require_login
from src.database.connection import get_database

router = APIRouter(prefix="/modules/billing", tags=["modules-billing"])
api_router = APIRouter(prefix="/api/billing", tags=["billing-api"])


@router.get("/status", response_model=ModuleStatus)
def billing_module_status():
    return module_status()


# --- Invoices (admin/staff) ---

@api_router.post("/invoices", status_code=201)
def create_invoice_api(
    payload: InvoiceCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    result = create_invoice(payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la factura (booking inválido)")
    return result


@api_router.get("/invoices")
def list_invoices_api(
    booking_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    return list_invoices(
        booking_id=booking_id, status=status_filter, q=q,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )


@api_router.get("/invoices/stats")
def invoice_stats_api(
    current_user: dict = Depends(require_login),
):
    """Return aggregate counts and totals grouped by invoice status."""
    return get_invoice_stats()


@api_router.get("/invoices/{invoice_id}")
def get_invoice_api(
    invoice_id: str,
    current_user: dict = Depends(require_login),
):
    result = get_invoice(invoice_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return result


@api_router.post("/invoices/{invoice_id}/items", status_code=201)
def add_line_item_api(
    invoice_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Add a line item to an invoice (only if status='issued').

    Payload:
    {
      "name": "Parking",
      "quantity": 1,
      "unit_price": 20.00,
      "category": "parking"
    }
    """
    result = add_line_item(
        invoice_id,
        name=payload.get("name", ""),
        quantity=int(payload.get("quantity", 1)),
        unit_price=float(payload.get("unit_price", 0)),
        category=payload.get("category", "Otros"),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo agregar el concepto. La factura puede no existir o no estar en estado 'issued'.",
        )
    return result


@api_router.delete("/invoices/{invoice_id}/items/{item_id}")
def remove_line_item_api(
    invoice_id: str,
    item_id: str,
    current_user: dict = Depends(require_login),
):
    """Remove a line item from an invoice (only if status='issued').

    Cannot remove room charge lines (type='room').
    """
    result = remove_line_item(invoice_id, item_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar el concepto. Puede ser el cargo de habitación (no removible).",
        )
    return result


@api_router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice_api(
    invoice_id: str,
    current_user: dict = Depends(require_login),
):
    result = cancel_invoice(invoice_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo cancelar la factura")
    return result


@api_router.post("/invoices/{invoice_id}/pay")
def pay_invoice_api(
    invoice_id: str,
    current_user: dict = Depends(require_login),
):
    """Staff-side: simulate payment for any invoice. No ownership check."""
    from src.app.modules.billing.schemas import PaymentCreate
    from bson import ObjectId
    from src.database.connection import get_database

    db = get_database()
    inv = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")

    if inv.get("status") != "issued":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La factura no está pendiente de pago")

    pay_payload = PaymentCreate(
        booking_id=str(inv.get("booking_id", "")),
        invoice_id=invoice_id,
        amount=float(inv.get("total", 0)),
        method="simulated",
    )
    result = create_payment(pay_payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo procesar el pago")
    return {"ok": True, "message": "Pago procesado exitosamente", "payment": result}


# --- Payments (admin/staff) ---

@api_router.post("/payments", status_code=201)
def create_payment_api(
    payload: PaymentCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    result = create_payment(payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo registrar el pago (booking inválido)")
    return result


@api_router.get("/payments")
def list_payments_api(
    booking_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    return list_payments(booking_id=booking_id, page=page, page_size=page_size)


@api_router.get("/payments/{payment_id}")
def get_payment_api(
    payment_id: str,
    current_user: dict = Depends(require_login),
):
    result = get_payment(payment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return result


@api_router.post("/payments/{payment_id}/refund")
def refund_payment_api(
    payment_id: str,
    current_user: dict = Depends(require_login),
):
    result = refund_payment(payment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo reembolsar el pago")
    return result


# --- Client-facing billing endpoints ---

@api_router.get("/my-invoices")
def my_invoices_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """Return invoices associated with the current user's bookings."""
    db = get_database()
    user_id = current_user.get("_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no identificado")
    # Find all bookings for this user
    booking_ids = [
        b["_id"]
        for b in db.booking_orders.find(
            {"user_id": user_id},
            {"_id": 1},
        )
    ]
    if not booking_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "has_next": False, "has_prev": False}

    from src.app.modules.billing.service.lifecycle import _enrich_invoice
    query = {"booking_id": {"$in": booking_ids}}
    total = db.reservation_invoices.count_documents(query)
    cursor = (
        db.reservation_invoices
        .find(query)
        .sort("issued_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_invoice(doc) for doc in cursor]
    import math
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


# ── Fólios (Guest Folio / Cuenta de Huésped) ──


@api_router.get("/folios/categories")
def folio_categories_api(
    current_user: dict = Depends(require_login),
):
    """Return the list of available folio posting categories."""
    return FOLIO_CATEGORIES


@api_router.get("/folios/{booking_id}")
def get_folio_api(
    booking_id: str,
    current_user: dict = Depends(require_login),
):
    """Get the folio for a booking."""
    result = get_folio(booking_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folio no encontrado para esta reserva")
    return result


@api_router.post("/folios/{booking_id}/post")
def post_to_folio_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Post a transaction to the guest's folio.

    Payload:
    {
      "posting_type": "charge" | "discount" | "payment" | "adjustment",
      "category": "restaurante" | "minibar" | "spa" | ...,
      "concept": "Masaje relajante",
      "amount": 40.00,
      "quantity": 1,
      "reference_id": "optional",
      "reference_type": "additional_charge"
    }
    """
    result = post_to_folio(
        booking_id,
        posting_type=payload.get("posting_type", "charge"),
        category=payload.get("category", "Otros"),
        concept=payload.get("concept", ""),
        amount=float(payload.get("amount", 0)),
        quantity=int(payload.get("quantity", 1)),
        reference_id=payload.get("reference_id", ""),
        reference_type=payload.get("reference_type", "manual"),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folio no encontrado")
    return result


@api_router.post("/folios/{booking_id}/close")
def close_folio_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Close a folio at check-out."""
    invoice_id = payload.get("invoice_id")
    result = close_folio(
        booking_id,
        invoice_id=invoice_id,
        closed_by=str(current_user.get("_id", "")),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo cerrar el folio")
    return result


@api_router.get("/folios")
def list_folios_api(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List folios with optional property and status filters."""
    return list_folios(prop_id=prop_id, status=status_filter, page=page, page_size=page_size)


@api_router.post("/my-invoices/{invoice_id}/pay")
def my_invoice_pay_api(
    invoice_id: str,
    current_user: dict = Depends(require_login),
):
    """Simulate payment for an invoice (client-facing). Generates a realistic payment record."""
    from src.app.modules.billing.schemas import PaymentCreate
    db = get_database()
    from bson import ObjectId

    inv = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")

    # Verify the invoice belongs to a booking owned by this user
    user_id = current_user.get("_id")
    booking = db.booking_orders.find_one({"_id": inv["booking_id"], "user_id": user_id})
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta factura no pertenece al usuario actual")

    if inv.get("status") != "issued":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La factura no está pendiente de pago")

    # Create the payment
    pay_payload = PaymentCreate(
        booking_id=str(inv["booking_id"]),
        invoice_id=invoice_id,
        amount=float(inv.get("total", 0)),
        method="bank_transfer",
    )
    result = create_payment(pay_payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo procesar el pago")
    return {"ok": True, "message": "Pago procesado exitosamente", "payment": result}
