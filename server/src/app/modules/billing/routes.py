from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.modules.billing.constants import DEFAULT_BILLING_PAGE_SIZE
from src.app.modules.billing.schemas import InvoiceCreate, ModuleStatus, PaymentCreate
from src.app.modules.billing.service import (
    add_line_item,
    cancel_invoice,
    close_folio,
    cleanup_expired_folios,
    create_invoice,
    create_payment,
    get_folio,
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
from src.app.modules.billing.service.services import get_billable_services
from src.app.core.types import ObjectIdStr, to_json_safe
from src.app.modules.partner.services.audit import register_action
from src.app.security.dependencies import require_any_permission, require_permission
from src.database.connection import get_database

router = APIRouter(prefix="/modules/billing", tags=["modules-billing"])
api_router = APIRouter(prefix="/api/billing", tags=["billing-api"])



# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ────────────
# All class declarations BELOW this banner must be on their OWN line.
# See knowledge.md → "Anti-pattern: from __future__ + Pydantic + response_model"
# for the failure modes this layout prevents.


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    booking_id: str | None = None
    parent_invoice_id: ObjectIdStr | None = Field(default=None, validation_alias="parent_invoice_id", serialization_alias="parent_invoice_id")
    # Prop_id may be int (legacy) or ObjectId (post-FK migration). Same transitional
    # pattern as BookingResponse.prop_id + LedgerTransactionResponse.prop_id (Fase 5/6).
    prop_id: int | ObjectIdStr | None = Field(
        default=None,
        description=(
            "Property FK reference. May be a legacy integer or a "
            "post-migration ObjectId string."
        ),
    )
    invoice_number: str | None = None
    status: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    taxes: float | None = None
    total: float | None = None
    total_paid_amount: float | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    notes: str | None = None
    source: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    issued_at: str | None = None
    paid_at: str | None = None
    cancelled_at: str | None = None
    line_items: list[Any] = Field(default_factory=list)


class InvoiceListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[InvoiceResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class InvoiceStatsResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    by_status: dict[str, Any] | None = None
    total_invoices: int | None = None
    total_amount: float | None = None
    issued: dict[str, Any] | None = None
    paid: dict[str, Any] | None = None
    cancelled: dict[str, Any] | None = None


# NOTE for future maintainers:
# `id` uses `AliasChoices("_id", "id")` (correct — primary key accepts both
# Mongo `_id` and pre-stringified `id` from legacy callers).
# `invoice_id` is now a strict SINGLE-alias FK (`validation_alias="invoice_id"`)
# so Pydantic v2 cannot ambiguity-match it against `id`'s `_id` chain. This
# closes the alias-collision class that previously caused `invoice_id` to
# inherit the primary key's value through `populate_by_name` fallback.
# Locked-in by the regression test in `tests/test_billing_responses.py`
# (`test_nested_payment_object_id_is_coerced_to_str`).
class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    booking_id: str | None = None
    invoice_id: ObjectIdStr | None = Field(default=None, validation_alias="invoice_id", serialization_alias="invoice_id")
    # Post-FK migration: prop_id may now arrive as ObjectId string. Same transitional
    # pattern as InvoiceResponse.prop_id + BookingResponse.prop_id (Fase 5/6).
    prop_id: int | ObjectIdStr | None = Field(
        default=None,
        description=(
            "Property FK reference. May be a legacy integer or a "
            "post-migration ObjectId string."
        ),
    )
    amount: float | None = None
    currency: str | None = None
    method: str | None = None
    status: str | None = None
    reference: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    paid_at: str | None = None
    refunded_at: str | None = None


class PaymentListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[PaymentResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class FolioResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    booking_id: str | None = None
    # Post-FK migration: prop_id may now arrive as ObjectId string. Same transitional
    # pattern as InvoiceResponse.prop_id + PaymentResponse.prop_id (Fase 5/6).
    prop_id: int | ObjectIdStr | None = Field(
        default=None,
        description=(
            "Property FK reference. May be a legacy integer or a "
            "post-migration ObjectId string."
        ),
    )
    folio_number: str | None = None
    status: str | None = None
    currency: str | None = None
    total_charges: float | None = None
    total_payments: float | None = None
    total_due: float | None = None
    posting_count: int | None = None
    closed_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None
    invoices: list[Any] = Field(default_factory=list)
    postings: list[Any] = Field(default_factory=list)


class FolioListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[FolioResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class BillableServicesResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    categories: list[Any] = Field(default_factory=list)
    chargeable: list[Any] = Field(default_factory=list)
    all_items: list[Any] = Field(default_factory=list)


class CleanupFoliosResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    closed: int = 0


class ActionResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    ok: bool = True
    message: str = ""
    payment: PaymentResponse | None = None
    closed: int | None = None


# Explicit rebuild — `from __future__ import annotations` makes Pydantic resolve
# ObjectIdStr + nested forward refs lazily. Force eager resolution before the
# first @router decorator binds a TypeAdapter.
InvoiceResponse.model_rebuild()
InvoiceListResponse.model_rebuild()
InvoiceStatsResponse.model_rebuild()
PaymentResponse.model_rebuild()
PaymentListResponse.model_rebuild()
FolioResponse.model_rebuild()
FolioListResponse.model_rebuild()
BillableServicesResponse.model_rebuild()
CleanupFoliosResponse.model_rebuild()
ActionResponse.model_rebuild()



@router.get("/status", response_model=ModuleStatus)
def billing_module_status():
    return module_status()


# --- Invoices (admin/staff) ---

@api_router.post("/invoices", status_code=201, response_model=InvoiceResponse)
def create_invoice_api(
    payload: InvoiceCreate = Body(...),
    current_user: dict = Depends(require_any_permission("billing.manage", "check-outs.manage")),
):
    # Checkout can revisit this step after a reload. Reuse the active invoice
    # for the booking instead of creating a duplicate fiscal document.
    db = get_database()
    existing = db.reservation_invoices.find_one(
        {"booking_id": payload.booking_id, "status": {"$ne": "cancelled"}},
        {"_id": 1},
    )
    if existing:
        existing_result = get_invoice(str(existing["_id"]))
        if existing_result is not None:
            return InvoiceResponse.model_validate(to_json_safe(existing_result))

    result = create_invoice(payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la factura (booking inválido)")
    diff = {
        k: {"old": None, "new": v}
        for k, v in result.items()
        if k not in ("id", "created_at", "updated_at", "issued_at", "paid_at") and v is not None
    }
    register_action(
        prop_id=result.get("prop_id") or 0,
        entity_type="billing_invoice",
        entity_id=result.get("id", ""),
        action="create",
        summary=f"Creación de factura {result.get('invoice_number', '')} — {result.get('booking_id', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return InvoiceResponse.model_validate(result)


@api_router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices_api(
    request: Request,
    booking_id: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_permission("billing.read")),
):
    result = list_invoices(
        booking_id=booking_id, prop_id=prop_id, status=status_filter, q=q,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )
    # Belt-and-suspenders: defensive JSON-safe wrap (ObjectId → str, datetime → isoformat)
    # catches anything list_invoices may have left raw (e.g. nested ObjectIds/dates).
    result = to_json_safe(result)
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_invoice",
        entity_id="list",
        action="read",
        summary=f"Listado de facturas (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={
            "booking_id": booking_id,
            "prop_id": prop_id,
            "status": status_filter,
            "q": q,
            "page": page,
            "page_size": page_size,
            "url": str(request.url),
        },
    )
    return InvoiceListResponse.model_validate(to_json_safe(result))


@api_router.get("/invoices/stats", response_model=InvoiceStatsResponse)
def invoice_stats_api(
    request: Request,
    current_user: dict = Depends(require_permission("billing.read")),
):
    """Return aggregate counts and totals grouped by invoice status."""
    result = get_invoice_stats()
    register_action(
        prop_id=0,
        entity_type="billing_invoice",
        entity_id="stats",
        action="read",
        summary="Consulta de estadísticas de facturación",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return InvoiceStatsResponse.model_validate(result)


@api_router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_api(
    request: Request,
    invoice_id: str,
    current_user: dict = Depends(require_permission("billing.read")),
):
    result = get_invoice(invoice_id)
    if result is not None:
        result = to_json_safe(result)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="read",
        summary=f"Consulta de factura {result.get('invoice_number', invoice_id)}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return InvoiceResponse.model_validate(result)


@api_router.post("/invoices/{invoice_id}/items", status_code=201, response_model=InvoiceResponse)
def add_line_item_api(
    invoice_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("billing.manage")),
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
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before_raw = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    except (InvalidId, Exception):
        before_raw = None
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
    diff = {
        "line_items_count": {"old": len(before_raw.get("line_items", [])) if before_raw else 0, "new": len(result.get("line_items", []))},
        "total": {"old": before_raw.get("total") if before_raw else None, "new": result.get("total")},
        "subtotal": {"old": before_raw.get("subtotal") if before_raw else None, "new": result.get("subtotal")},
        "taxes": {"old": before_raw.get("taxes") if before_raw else None, "new": result.get("taxes")},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Agregado de concepto a factura {result.get('invoice_number', invoice_id)}: {payload.get('name', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return InvoiceResponse.model_validate(result)


@api_router.delete("/invoices/{invoice_id}/items/{item_id}", response_model=InvoiceResponse)
def remove_line_item_api(
    invoice_id: str,
    item_id: str,
    current_user: dict = Depends(require_permission("billing.manage")),
):
    """Remove a line item from an invoice (only if status='issued').

    Cannot remove room charge lines (type='room').
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before_raw = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    except (InvalidId, Exception):
        before_raw = None
    result = remove_line_item(invoice_id, item_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar el concepto. Puede ser el cargo de habitación (no removible).",
        )
    diff = {
        "line_items_count": {"old": len(before_raw.get("line_items", [])) if before_raw else 0, "new": len(result.get("line_items", []))},
        "total": {"old": before_raw.get("total") if before_raw else None, "new": result.get("total")},
        "subtotal": {"old": before_raw.get("subtotal") if before_raw else None, "new": result.get("subtotal")},
        "taxes": {"old": before_raw.get("taxes") if before_raw else None, "new": result.get("taxes")},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Eliminación de concepto de factura {result.get('invoice_number', invoice_id)}: item {item_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return InvoiceResponse.model_validate(result)


@api_router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice_api(
    invoice_id: str,
    current_user: dict = Depends(require_permission("billing.manage")),
):
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before_raw = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    except (InvalidId, Exception):
        before_raw = None
    result = cancel_invoice(invoice_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo cancelar la factura")
    diff = {
        "status": {"old": before_raw.get("status") if before_raw else None, "new": "cancelled"},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Cancelación de factura {result.get('invoice_number', invoice_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return InvoiceResponse.model_validate(result)


@api_router.post("/invoices/{invoice_id}/pay", response_model=ActionResponse)
def pay_invoice_api(
    invoice_id: str,
    current_user: dict = Depends(require_permission("billing.manage")),
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

    before = get_invoice(invoice_id)
    pay_payload = PaymentCreate(
        booking_id=str(inv.get("booking_id", "")),
        invoice_id=invoice_id,
        amount=float(inv.get("total", 0)),
        method="simulated",
    )
    result = create_payment(pay_payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo procesar el pago")

    after = get_invoice(invoice_id)
    diff = {
        "status": {"old": before.get("status") if before else None, "new": after.get("status") if after else "paid"},
        "total_paid_amount": {"old": before.get("total_paid_amount") if before else 0.0, "new": after.get("total_paid_amount") if after else float(inv.get("total", 0))},
    }
    register_action(
        prop_id=(inv.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Pago de factura {inv.get('invoice_number', invoice_id)} — ${float(inv.get('total', 0)):,.2f}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return ActionResponse.model_validate({
        "ok": True,
        "message": "Pago procesado exitosamente",
        "payment": result,
    })


@api_router.post("/invoices/{invoice_id}/email", response_model=ActionResponse)
def send_invoice_email_api(
    invoice_id: str,
    current_user: dict = Depends(require_any_permission("billing.manage", "check-outs.manage")),
):
    """Send the invoice to the guest by email."""
    from bson import ObjectId
    from src.app.modules.reservations.notifications.guest import notify_guest_invoice

    db = get_database()
    try:
        inv = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")

    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")

    booking_id = inv.get("booking_id", "")
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1,
         "check_in_date": 1, "check_out_date": 1, "total_nights": 1},
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")

    guest_email = booking.get("guest_email", "")
    if not guest_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El huésped no tiene correo electrónico registrado")

    notify_guest_invoice(
        booking_id=booking_id,
        guest_name=booking.get("guest_name", ""),
        guest_email=guest_email,
        prop_id=int(inv.get("prop_id", 0)),
        check_in_date=booking.get("check_in_date", ""),
        check_out_date=booking.get("check_out_date", ""),
        total_nights=int(booking.get("total_nights", 0)),
        invoice_id=str(inv["_id"]),
        invoice_number=inv.get("invoice_number", ""),
        invoice_total=float(inv.get("total", 0)),
        currency=inv.get("currency", "USD"),
    )
    register_action(
        prop_id=(inv.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="email",
        summary=f"Envío de factura por email {inv.get('invoice_number', invoice_id)} a {guest_email}",
        changed_by=current_user.get("username", "system"),
        metadata={"guest_email": guest_email},
    )
    return ActionResponse.model_validate({
        "ok": True,
        "message": f"Factura enviada a {guest_email}",
    })


# --- Payments (admin/staff) ---

@api_router.post("/payments", status_code=201, response_model=PaymentResponse)
def create_payment_api(
    payload: PaymentCreate = Body(...),
    current_user: dict = Depends(require_permission("payments.manage")),
):
    result = create_payment(payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo registrar el pago (booking inválido)")
    diff = {
        k: {"old": None, "new": v}
        for k, v in result.items()
        if k not in ("id", "created_at", "updated_at", "paid_at") and v is not None
    }
    register_action(
        prop_id=result.get("prop_id") or 0,
        entity_type="billing_payment",
        entity_id=result.get("id", ""),
        action="create",
        summary=f"Registro de pago {result.get('reference', '')} — ${result.get('amount', 0):,.2f}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return PaymentResponse.model_validate(result)


@api_router.get("/payments", response_model=PaymentListResponse)
def list_payments_api(
    request: Request,
    booking_id: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_permission("payments.read")),
):
    result = list_payments(booking_id=booking_id, prop_id=prop_id, page=page, page_size=page_size)
    # Belt-and-suspenders: defensive JSON-safe wrap (same rationale as list_invoices)
    result = to_json_safe(result)
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_payment",
        entity_id="list",
        action="read",
        summary=f"Listado de pagos (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"booking_id": booking_id, "prop_id": prop_id, "page": page, "url": str(request.url)},
    )
    return PaymentListResponse.model_validate(to_json_safe(result))


@api_router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_api(
    request: Request,
    payment_id: str,
    current_user: dict = Depends(require_permission("payments.read")),
):
    result = get_payment(payment_id)
    if result is not None:
        result = to_json_safe(result)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_payment",
        entity_id=payment_id,
        action="read",
        summary=f"Consulta de pago {result.get('reference', payment_id)}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return PaymentResponse.model_validate(result)


@api_router.post("/payments/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment_api(
    payment_id: str,
    current_user: dict = Depends(require_permission("payments.manage")),
):
    before = get_payment(payment_id)
    result = refund_payment(payment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo reembolsar el pago")
    diff = {
        "status": {"old": before.get("status") if before else None, "new": "refunded"},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_payment",
        entity_id=payment_id,
        action="update",
        summary=f"Reembolso de pago {result.get('reference', payment_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return PaymentResponse.model_validate(result)


# --- Client-facing billing endpoints ---

@api_router.get("/my-invoices", response_model=InvoiceListResponse)
def my_invoices_api(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_permission("account.read")),
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
        return InvoiceListResponse.model_validate({
            "items": [], "total": 0, "page": page, "page_size": page_size,
            "has_next": False, "has_prev": False, "total_pages": 1,
        })

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
    register_action(
        prop_id=0,
        entity_type="billing_invoice",
        entity_id="my_invoices",
        action="read",
        summary=f"Mis facturas (total={total}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"user_id": str(user_id), "page": page, "url": str(request.url)},
    )
    return InvoiceListResponse.model_validate({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    })


# ── Billable Services (from amenities catalog) ──


@api_router.get("/services", response_model=BillableServicesResponse)
def billing_services_api(
    request: Request,
    prop_id: int = Query(default=0, ge=0),
    booking_id: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("billing.read")),
):
    """Return billable services for the invoice page.

    Combines hotel-wide amenities with room-type-specific amenities
    (if booking_id is provided), deduplicated by label, grouped by
    category. The frontend uses this to populate the charge categories
    dropdown and quick-charge buttons.
    """
    if not prop_id:
        # Try to derive from booking
        if booking_id:
            db = get_database()
            booking = db.booking_orders.find_one(
                {"booking_id": booking_id},
                {"prop_id": 1, "_id": 0},
            )
            if booking:
                prop_id = int(booking.get("prop_id", 0))
    if not prop_id:
        return BillableServicesResponse.model_validate({"categories": [], "chargeable": [], "all_items": []})

    result = get_billable_services(prop_id, booking_id)
    register_action(
        prop_id=prop_id,
        entity_type="billing_invoice",
        entity_id="services",
        action="read",
        summary=f"Consulta de servicios facturables para propiedad {prop_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "booking_id": booking_id, "url": str(request.url)},
    )
    return BillableServicesResponse.model_validate(result)


# ── Fólios (Guest Folio / Cuenta de Huésped) ──


# Intentional: returns the static `FOLIO_CATEGORIES` constant (Python list), NOT a
# Mongo doc. Future API-boundary sweeps MUST skip this endpoint — wrap a *Response
# here would force a Pydantic enum class for what is a stable, code-defined catalog.
@api_router.get("/folios/categories")
def folio_categories_api(
    request: Request,
    current_user: dict = Depends(require_permission("billing.read")),
):
    """Return the list of available folio posting categories."""
    register_action(
        prop_id=0,
        entity_type="billing_folio",
        entity_id="categories",
        action="read",
        summary="Listado de categorías de folio",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return FOLIO_CATEGORIES


@api_router.get("/folios/{booking_id}", response_model=FolioResponse)
def get_folio_api(
    request: Request,
    booking_id: str,
    current_user: dict = Depends(require_permission("billing.read")),
):
    """Get the folio for a booking."""
    result = get_folio(booking_id)
    if result is not None:
        result = to_json_safe(result)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folio no encontrado para esta reserva")
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_folio",
        entity_id=booking_id,
        action="read",
        summary=f"Consulta de folio para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return FolioResponse.model_validate(result)


@api_router.post("/folios/{booking_id}/post", response_model=FolioResponse)
def post_to_folio_api(
    booking_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("billing.manage")),
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
    before = get_folio(booking_id)
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
    diff = {
        "total_due": {"old": before.get("total_due") if before else None, "new": result.get("total_due")},
        "posting_count": {"old": before.get("posting_count") if before else None, "new": result.get("posting_count")},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_folio",
        entity_id=booking_id,
        action="update",
        summary=f"Posteo a folio {result.get('folio_number', booking_id)}: {payload.get('concept', '')} — ${float(payload.get('amount', 0)):,.2f}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return FolioResponse.model_validate(result)


@api_router.post("/folios/{booking_id}/close", response_model=FolioResponse)
def close_folio_api(
    booking_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("billing.manage")),
):
    """Close a folio at check-out."""
    before = get_folio(booking_id)
    invoice_id = payload.get("invoice_id")
    result = close_folio(
        booking_id,
        invoice_id=invoice_id,
        closed_by=str(current_user.get("_id", "")),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo cerrar el folio")
    diff = {
        "status": {"old": before.get("status") if before else None, "new": "closed"},
        "total_due": {"old": before.get("total_due") if before else None, "new": result.get("total_due")},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_folio",
        entity_id=booking_id,
        action="update",
        summary=f"Cierre de folio {result.get('folio_number', booking_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return FolioResponse.model_validate(result)


@api_router.post("/folios/cleanup-expired", response_model=CleanupFoliosResponse)
def cleanup_expired_folios_api(
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("billing.manage")),
):
    """Close open folios whose check-out date has already passed.

    Payload: {"prop_id": 1}  (optional; if omitted, cleans all properties)
    """
    prop_id = payload.get("prop_id") if payload.get("prop_id") else None
    result = cleanup_expired_folios(prop_id=prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_folio",
        entity_id="cleanup_expired",
        action="update",
        summary=f"Cierre de folios vencidos: {result.get('closed', 0)} cerrados",
        changed_by=current_user.get("username", "system"),
        diff={"closed": {"old": None, "new": result.get("closed", 0)}},
    )
    return CleanupFoliosResponse.model_validate(result)


@api_router.get("/folios", response_model=FolioListResponse)
def list_folios_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_permission("billing.read")),
):
    """List folios with optional property and status filters."""
    result = list_folios(prop_id=prop_id, status=status_filter, page=page, page_size=page_size)
    # Belt-and-suspenders: defensive JSON-safe wrap (same rationale as list_invoices)
    result = to_json_safe(result)
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_folio",
        entity_id="list",
        action="read",
        summary=f"Listado de folios (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "status": status_filter, "page": page, "url": str(request.url)},
    )
    return FolioListResponse.model_validate(result)


@api_router.post("/my-invoices/{invoice_id}/pay", response_model=ActionResponse)
def my_invoice_pay_api(
    invoice_id: str,
    current_user: dict = Depends(require_permission("account.update")),
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

    before = get_invoice(invoice_id)
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

    after = get_invoice(invoice_id)
    diff = {
        "status": {"old": before.get("status") if before else None, "new": after.get("status") if after else "paid"},
        "total_paid_amount": {"old": before.get("total_paid_amount") if before else 0.0, "new": after.get("total_paid_amount") if after else float(inv.get("total", 0))},
    }
    register_action(
        prop_id=(inv.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Pago de factura (cliente) {inv.get('invoice_number', invoice_id)} — ${float(inv.get('total', 0)):,.2f}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return ActionResponse.model_validate({
        "ok": True,
        "message": "Pago procesado exitosamente",
        "payment": result,
    })
