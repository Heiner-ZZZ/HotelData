from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.modules.billing.constants import DEFAULT_BILLING_PAGE_SIZE
from src.app.modules.billing.schemas import InvoiceCreate, ModuleStatus, PaymentCreate
from src.app.modules.billing.service import (
    add_line_item,
    cancel_invoice,
    close_folio,
    reopen_folio_with_balance,
    settle_folio,
    is_historical_cash_shift_eligible,
    cleanup_expired_folios,
    create_invoice,
    create_complement_invoice,
    create_payment,
    classify_failed_payment_informational,
    get_folio,
    get_invoice,
    get_invoice_stats,
    get_payment,
    list_folios,
    list_invoices,
    list_payments,
    link_payment_to_shift,
    module_status,
    post_to_folio,
    refund_payment,
    remove_line_item,
    repair_cancelled_or_refunded_invoice,
    create_credit_note_for_invoice,
    FOLIO_CATEGORIES,
)
from src.app.modules.billing.service.services import get_billable_services
from src.app.core.types import ObjectIdStr, to_json_safe
from src.app.modules.partner.services.audit import (
    register_action,
    register_shift_attribution_access,
)
from src.app.modules.reception import (
    ShiftExpiredError,
    ensure_shift_not_expired,
    get_active_shift_id,
    get_shift_attribution,
    list_shifts,
)
from src.app.security.dependencies import require_permission, require_prop_permission, require_any_prop_permission
from src.app.security.permissions import (
    FOLIO_ADJUST_APPROVAL_PERMISSION,
    require_supervisor_authorization,
    user_has_permission,
)
from src.database.connection import get_database

router = APIRouter(prefix="/modules/billing", tags=["modules-billing"])
api_router = APIRouter(prefix="/api/billing", tags=["billing-api"])


def _require_billing_scope(value: Any) -> int:
    """Fail closed when a legacy billing read omits its hotel scope."""
    from fastapi.params import Param

    if isinstance(value, Param):
        value = value.default
    try:
        prop_id = int(value)
    except (TypeError, ValueError):
        prop_id = 0
    if prop_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prop_id es obligatorio para consultar datos de Guest AR del hotel",
        )
    return prop_id


def _require_active_shift_for_money(prop_id: int) -> str:
    """Require an open (non-expired) cash shift before a money operation.

    Every front-desk operation that moves money — payments of ANY method,
    refunds, invoice payment, folio settlement and folio postings — must be
    attributable to the cashier on duty, so the resulting document is stamped
    with the shift and its employee. Returns the active shift id, or raises
    HTTP 409 (missing / expired shift).
    """
    shift_id = get_active_shift_id(prop_id)
    if shift_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No hay un turno de caja activo para esta propiedad. "
                "Abre un turno primero en Cajas y Turnos antes de registrar "
                "operaciones de dinero."
            ),
        )
    try:
        ensure_shift_not_expired(prop_id)
    except ShiftExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return shift_id



def _scoped_invoice(invoice_id: str, prop_id: int | None) -> dict[str, Any]:
    """Load a Guest AR invoice only inside the requested hotel scope."""
    prop_id = _require_billing_scope(prop_id)
    try:
        oid = ObjectId(invoice_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la factura. Verificá el identificador de la factura e intentá de nuevo.",
        ) from exc
    invoice = get_database().reservation_invoices.find_one({"_id": oid, "prop_id": prop_id})
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No se encontró la factura en este hotel. Verificá que la factura pertenezca al hotel "
                "seleccionado e intentá de nuevo."
            ),
        )
    return invoice


def _scoped_payment(payment_id: str, prop_id: int | None) -> dict[str, Any]:
    """Load a Guest AR payment only inside the requested hotel scope."""
    prop_id = _require_billing_scope(prop_id)
    payment = get_payment(payment_id)
    if not payment or int(payment.get("prop_id", 0) or 0) != prop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No se encontró el pago en este hotel. Verificá que el pago pertenezca al hotel "
                "seleccionado e intentá de nuevo."
            ),
        )
    return payment


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
    original_total: float | None = None
    recognized_total: float | None = None
    net_total: float | None = None
    accounting_status: str | None = None
    ledger_posting_status: str | None = None
    ledger_posting_error: str | None = None
    ledger_references: list[str] = Field(default_factory=list)
    accounting_reversal_journal_id: str | None = None
    credit_note_id: ObjectIdStr | None = None
    credit_note_number: str | None = None
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
    refund_id: str | None = None
    refund_document_id: ObjectIdStr | None = None
    refund_document_number: str | None = None
    reconciliation_status: str | None = None
    reconciliation_reason: str | None = None
    evidence_type: str | None = None
    evidence_reference: str | None = None
    payment_source: str | None = None
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


class FolioSettlementRequest(BaseModel):
    settlement_type: str
    idempotency_key: str = Field(min_length=1)
    amount: float | None = Field(default=None, gt=0)
    method: str | None = None
    reason: str | None = None
    approval_reference: str | None = None
    external_reference: str | None = None
    settlement_at: datetime | None = None
    evidence_type: str | None = None
    evidence_reference: str | None = None


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
    total_room: float | None = None
    total_charges: float | None = None
    total_discounts: float | None = None
    total_payments: float | None = None
    total_due: float | None = None
    invoice_number: str | None = None
    invoice_status: str | None = None
    invoice_subtotal: float | None = None
    invoice_covered_subtotal: float | None = None
    reopened_at: str | None = None
    reopened_by: str | None = None
    posting_count: int | None = None
    closed_by: str | None = None
    settlement_type: str | None = None
    settlement_amount: float | None = None
    settlement_reason: str | None = None
    approval_reference: str | None = None
    external_reference: str | None = None
    settlement_evidence_type: str | None = None
    settlement_evidence_reference: str | None = None
    settlement_payment_id: ObjectIdStr | None = None
    settlement_payment_ids: list[ObjectIdStr] = Field(default_factory=list)
    settlement_event_id: ObjectIdStr | None = None
    settlement_event_ids: list[ObjectIdStr] = Field(default_factory=list)
    settlement_shift_id: ObjectIdStr | None = None
    settlement_shift_ids: list[ObjectIdStr] = Field(default_factory=list)
    settlement_invoice_id: ObjectIdStr | None = None
    settled_at: str | None = None
    settled_recorded_at: str | None = None
    settled_by: str | None = None
    settled_by_user_id: ObjectIdStr | None = None
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
FolioSettlementRequest.model_rebuild()
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
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("billing.manage", "check-outs.manage")),
):
    db = get_database()
    # Issuing a fiscal document is a money operation: it must be attributable
    # to the cashier on duty, so the whole fiscal cycle (emisión → pago →
    # anulación) requires an open shift. The checkout flow reuses this route
    # and already opens a shift, so this gate does not break it.
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id}, {"prop_id": 1})
    shift_id = None
    if booking is not None:
        shift_id = _require_active_shift_for_money(int(booking.get("prop_id") or 0))

    # Checkout can revisit this step after a reload. Reuse the active invoice
    # for the booking instead of creating a duplicate fiscal document.
    existing = db.reservation_invoices.find_one(
        {"booking_id": payload.booking_id, "status": {"$ne": "cancelled"}},
        {"_id": 1},
    )
    if existing:
        existing_result = get_invoice(str(existing["_id"]))
        if existing_result is not None:
            return InvoiceResponse.model_validate(to_json_safe(existing_result))

    result = create_invoice(
        payload,
        shift_id=shift_id,
        shift_attribution=get_shift_attribution(shift_id) if shift_id else None,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo crear la factura: la reserva es inválida o no tiene importe que facturar. "
                "Verificá que la reserva esté confirmada y tenga cargos pendientes, e intentá de nuevo."
            ),
        )
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
    # Belt-and-suspenders (same rationale as close_folio_api): create_invoice
    # returns raw datetimes (issued_at/created_at); to_json_safe normalizes
    # them to ISO before the *Response wire validation.
    return InvoiceResponse.model_validate(to_json_safe(result))


@api_router.post("/invoices/complement", status_code=201, response_model=InvoiceResponse)
def create_complement_invoice_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("billing.manage", "check-outs.manage")),
):
    """Emit a complementary invoice for the un-invoiced gap ("factura corta").

    Cuando una factura emitida no cubre los cargos adicionales actuales
    (cargos registrados después de facturar), esta acción emite una factura
    complementaria de consumos por EXACTAMENTE el gap: los cargos activos que
    no figuran en la factura principal. Idempotente por snapshot: una segunda
    llamada con la misma snapshot devuelve la complementaria existente.
    """
    booking_id = str(payload.get("booking_id") or "").strip()
    if not booking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="booking_id es obligatorio: indicá el identificador de la reserva e intentá de nuevo.",
        )
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1})
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.",
        )
    # Misma política fiscal que create_invoice_api: emitir un documento de
    # dinero exige un turno de caja activo para atribuir la operación.
    _require_active_shift_for_money(int(booking.get("prop_id") or 0))

    result = create_complement_invoice(
        booking_id,
        changed_by=current_user.get("username", "system"),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No hay cargos sin facturar: la factura cubre la liquidación actual. "
                "Si la factura quedó corta, registrá primero los cargos adicionales."
            ),
        )
    register_action(
        prop_id=int(booking.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=result.get("id", ""),
        action="create",
        summary=(
            f"Factura complementaria {result.get('invoice_number', '')} — "
            f"{booking_id} (gap de cargos sin facturar)"
        ),
        changed_by=current_user.get("username", "system"),
    )
    return InvoiceResponse.model_validate(to_json_safe(result))


@api_router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices_api(
    request: Request,
    booking_id: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    shift_id: str | None = Query(default=None, alias="turno"),
    employee: str | None = Query(default=None, alias="cajero"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_prop_permission("billing.read")),
):
    prop_id = _require_billing_scope(prop_id)
    result = list_invoices(
        booking_id=booking_id, prop_id=prop_id, status=status_filter, q=q,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
        shift_id=shift_id, employee=employee,
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
            "shift_id": shift_id,
            "employee": employee,
            "page": page,
            "page_size": page_size,
            "url": str(request.url),
        },
    )
    return InvoiceListResponse.model_validate(to_json_safe(result))


@api_router.get("/analytics/invoices")
def invoice_dashboard_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_prop_permission("reports.billing.invoices.read")),
):
    """Dashboard táctico F1.4: monto facturado por período (ClickHouse).


    Lee exclusivamente ``kpi_invoice_daily`` (agregado por día × hotel ×
    estado). Devuelve resumen, evolución diaria y filas paginadas.
    """
    prop_id = _require_billing_scope(prop_id)
    from src.app.modules.billing.service.lifecycle.analytics import get_invoice_dashboard

    try:
        result = get_invoice_dashboard(
            prop_id=prop_id,
            date_from=date_from,
            date_to=date_to,
            days=days,
            status=status,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_invoice",
        entity_id="analytics",
        action="read",
        summary="Consulta del dashboard táctico de facturación (F1.4)",
        changed_by=current_user.get("username", "system"),
        metadata={
            "prop_id": prop_id, "date_from": date_from, "date_to": date_to,
            "days": days, "status": status, "page": page, "page_size": page_size,
            "url": str(request.url),
        },
    )
    return result


@api_router.get("/analytics/payments")
def payments_dashboard_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    method: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_BILLING_PAGE_SIZE, ge=1, le=100),
    current_user: dict = Depends(require_prop_permission("reports.billing.payments.read")),
):
    """Dashboard táctico F1.5: pagos por método/estado y saldo pendiente.


    Lee ``kpi_payment_daily`` (agregado por día × hotel × método × estado) que
    ya incluye el cruce facturado/cobrado. El saldo pendiente nunca se calcula
    solo con pagos: ``invoiced_amount`` proviene de las facturas no anuladas.
    """
    prop_id = _require_billing_scope(prop_id)
    from src.app.modules.billing.service.lifecycle.analytics import get_payments_dashboard

    try:
        result = get_payments_dashboard(
            prop_id=prop_id,
            date_from=date_from,
            date_to=date_to,
            days=days,
            method=method,
            status=status,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_payment",
        entity_id="analytics",
        action="read",
        summary="Consulta del dashboard táctico de pagos (F1.5)",
        changed_by=current_user.get("username", "system"),
        metadata={
            "prop_id": prop_id, "date_from": date_from, "date_to": date_to,
            "days": days, "method": method, "status": status,
            "page": page, "page_size": page_size, "url": str(request.url),
        },
    )
    return result


@api_router.get("/invoices/stats", response_model=InvoiceStatsResponse)
def invoice_stats_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("billing.read")),
):
    """Return aggregate counts and totals grouped by invoice status."""
    prop_id = _require_billing_scope(prop_id)
    result = get_invoice_stats(prop_id=prop_id)
    register_action(
        prop_id=prop_id,
        entity_type="billing_invoice",
        entity_id="stats",
        action="read",
        summary="Consulta de estadísticas de facturación",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return InvoiceStatsResponse.model_validate(result)


@api_router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_api(
    request: Request,
    invoice_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("billing.read")),
):
    prop_id = _require_billing_scope(prop_id)
    result = get_invoice(invoice_id)
    if result is not None:
        result = to_json_safe(result)
    if result is None or int(result.get("prop_id", 0) or 0) != prop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No se encontró la factura en este hotel. Verificá que la factura pertenezca al hotel "
                "seleccionado e intentá de nuevo."
            ),
        )
    register_action(
        prop_id=prop_id,
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
    prop_id: int | None = Query(default=None, ge=1),
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
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
    before_raw = _scoped_invoice(invoice_id, prop_id)
    # An added charge moves money on the invoice: attributable to the cashier
    # on duty, so it also requires an open (non-expired) shift for the hotel.
    _require_active_shift_for_money(int((before_raw or {}).get("prop_id") or 0))
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
            detail=(
                "No se pudo agregar el concepto. Verificá que la factura esté emitida y sin pagos "
                "confirmados, e intentá de nuevo."
            ),
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
    # Belt-and-suspenders (same rationale as cancel_invoice_api): add_line_item
    # returns created_at/updated_at as raw datetimes; to_json_safe normalizes
    # them to ISO before the *Response wire validation.
    return InvoiceResponse.model_validate(to_json_safe(result))


@api_router.delete("/invoices/{invoice_id}/items/{item_id}", response_model=InvoiceResponse)
def remove_line_item_api(
    invoice_id: str,
    item_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
):
    """Remove a line item from an invoice (only if status='issued').

    Cannot remove room charge lines (type='room').
    """
    from bson import ObjectId
    from bson.errors import InvalidId
    before_raw = _scoped_invoice(invoice_id, prop_id)
    result = remove_line_item(invoice_id, item_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo eliminar el concepto: el cargo de habitación no se puede remover. "
                "Elegí un concepto adicional e intentá de nuevo."
            ),
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


@api_router.post("/invoices/{invoice_id}/repair-settlement", response_model=InvoiceResponse)
def repair_invoice_settlement_api(
    invoice_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
):
    """Reconcile a cancelled/refunded invoice without erasing its original value."""
    _scoped_invoice(invoice_id, prop_id)
    result = repair_cancelled_or_refunded_invoice(
        invoice_id,
        changed_by=str(current_user.get("_id", current_user.get("username", "system"))),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se pudo reparar la factura: no es reparable o no tiene importe positivo. "
                "Verificá que esté anulada o reembolsada y que su total sea mayor a cero, e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="repair",
        summary=f"Conciliación de factura anulada/reembolsada {result.get('invoice_number', invoice_id)}",
        changed_by=current_user.get("username", "system"),
        diff={"recognized_total": {"old": None, "new": result.get("recognized_total", 0)}},
    )
    return InvoiceResponse.model_validate(result)


@api_router.post("/invoices/{invoice_id}/credit-note", response_model=InvoiceResponse)
def create_credit_note_api(
    invoice_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
):
    """Issue/reuse the formal credit note for a cancelled/refunded invoice."""
    invoice = _scoped_invoice(invoice_id, prop_id)
    # A credit note reverses money on a fiscal document: the whole fiscal
    # cycle must be attributable to the cashier on duty, so emission also
    # requires an open (non-expired) shift for the hotel, and the shift +
    # employee are stamped on the refund document at write time.
    shift_id = _require_active_shift_for_money(int((invoice or {}).get("prop_id") or 0))
    result = create_credit_note_for_invoice(
        invoice_id,
        changed_by=str(current_user.get("_id", current_user.get("username", "system"))),
        shift_id=shift_id,
        shift_attribution=get_shift_attribution(shift_id) if shift_id else None,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se pudo emitir el documento compensatorio: la factura no tiene un reverso contable "
                "válido. Verificá que esté anulada o reembolsada y que haya un turno de caja activo, "
                "e intentá de nuevo."
            ),
        )
    invoice = get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la factura. Verificá el identificador de la factura e intentá de nuevo.",
        )
    invoice = to_json_safe(invoice)
    register_action(
        prop_id=invoice.get("prop_id") or 0,
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="repair",
        summary=f"Documento compensatorio emitido {result.get('document_number', '')}",
        changed_by=current_user.get("username", "system"),
        diff={"credit_note_number": {"old": None, "new": result.get("document_number")}},
    )
    return InvoiceResponse.model_validate(invoice)


@api_router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice_api(
    invoice_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
):
    before_raw = _scoped_invoice(invoice_id, prop_id)
    # Voiding a fiscal document reverses money: the whole fiscal cycle must be
    # attributable to the cashier on duty, so cancellation also requires an
    # open (non-expired) shift for the hotel.
    cancel_shift_id = _require_active_shift_for_money(int((before_raw or {}).get("prop_id") or 0))
    if not isinstance(payload, dict):
        payload = {}
    cancel_reason = str(payload.get("reason") or "").strip() or None
    result = cancel_invoice(
        invoice_id,
        cancel_reason=cancel_reason,
        cancelled_by=str(current_user.get("username", "system")),
        shift_id=cancel_shift_id,
        shift_attribution=get_shift_attribution(cancel_shift_id) if cancel_shift_id else None,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo cancelar la factura. Verificá que esté pendiente de pago y sin pagos "
                "confirmados, e intentá de nuevo."
            ),
        )
    diff = {
        "status": {"old": before_raw.get("status") if before_raw else None, "new": "cancelled"},
        "cancel_reason": {"old": before_raw.get("cancel_reason") if before_raw else None, "new": cancel_reason},
    }
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Cancelación de factura {result.get('invoice_number', invoice_id)}"
        + (f" — {cancel_reason}" if cancel_reason else ""),
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    # Belt-and-suspenders (same rationale as close_folio_api): cancel_invoice
    # sets cancelled_at as a raw datetime; to_json_safe normalizes it to ISO
    # before the *Response wire validation.
    return InvoiceResponse.model_validate(to_json_safe(result))


@api_router.post("/invoices/{invoice_id}/pay", response_model=ActionResponse)
def pay_invoice_api(
    invoice_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
):
    """Staff-side: simulate payment for any invoice. No ownership check."""
    from src.app.modules.billing.schemas import PaymentCreate
    from bson import ObjectId
    from src.database.connection import get_database

    inv = _scoped_invoice(invoice_id, prop_id)

    if inv.get("status") != "issued":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La factura no está pendiente de pago. Solo se pueden pagar facturas emitidas sin pagos "
                "confirmados; verificá el estado de la factura e intentá de nuevo."
            ),
        )

    # Staff invoice payment is a money operation: attribute it to the shift.
    shift_id = _require_active_shift_for_money(int((inv.get("prop_id") or 0)))

    before = get_invoice(invoice_id)
    pay_payload = PaymentCreate(
        booking_id=str(inv.get("booking_id", "")),
        invoice_id=invoice_id,
        amount=float(inv.get("total", 0)),
        method="simulated",
    )
    try:
        result = create_payment(pay_payload, shift_id=shift_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo procesar el pago. Verificá el importe, el método de pago y que haya un "
                "turno de caja activo, e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)

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
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_any_prop_permission("billing.manage", "check-outs.manage")),
):
    """Send the invoice to the guest by email."""
    from bson import ObjectId
    from src.app.modules.reservations.notifications.guest import notify_guest_invoice

    inv = _scoped_invoice(invoice_id, prop_id)
    db = get_database()

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
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("payments.manage")),
):
    # Every payment at the front desk — cash, card, transfer or gateway — is a
    # money operation that must be attributable to the cashier on duty. The
    # shift id (and its employee) are stamped on the payment at write time so
    # the close-of-shift reconciliation is FK-driven, not window-guessed.
    booking_doc = get_database().booking_orders.find_one(
        {"booking_id": payload.booking_id},
        {"prop_id": 1},
    )
    prop_id = int((booking_doc or {}).get("prop_id", 0))
    shift_id = _require_active_shift_for_money(prop_id)

    try:
        result = create_payment(payload, shift_id=shift_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se encontró la reserva indicada (booking_id inválido). Verificá el número de reserva "
                "e intentá de nuevo."
            ),
        )
    # JSON-safe wrap (ObjectId → str, datetime → isoformat): same rationale as
    # list/get routes. PaymentResponse declares created_at/paid_at as strings.
    result = to_json_safe(result)
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
    sin_turno: bool = Query(default=False, alias="sin_turno"),
    shift_id: str | None = Query(default=None, alias="turno"),
    employee: str | None = Query(default=None, alias="cajero"),
    current_user: dict = Depends(require_prop_permission("payments.read")),
):
    prop_id = _require_billing_scope(prop_id)
    result = list_payments(booking_id=booking_id, prop_id=prop_id, page=page, page_size=page_size, sin_turno=sin_turno, shift_id=shift_id, employee=employee)
    # Belt-and-suspenders: defensive JSON-safe wrap (same rationale as list_invoices)
    result = to_json_safe(result)
    register_action(
        prop_id=prop_id or 0,
        entity_type="billing_payment",
        entity_id="list",
        action="read",
        summary=f"Listado de pagos (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={
            "booking_id": booking_id,
            "prop_id": prop_id,
            "shift_id": shift_id,
            "employee": employee,
            "page": page,
            "url": str(request.url),
        },
    )
    return PaymentListResponse.model_validate(to_json_safe(result))


@api_router.post("/payments/{payment_id}/classify-informational", response_model=PaymentResponse)
def classify_failed_payment_informational_api(
    payment_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("payments.manage")),
):
    """Mark a failed payment without invoice as an informational attempt."""
    _scoped_payment(payment_id, prop_id)
    result = classify_failed_payment_informational(
        payment_id,
        changed_by=str(current_user.get("_id", current_user.get("username", "system"))),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se pudo clasificar el pago como informativo: solo los intentos fallidos sin factura "
                "pueden marcarse así. Verificá el estado del pago e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)
    register_action(
        prop_id=result.get("prop_id") or 0,
        entity_type="billing_payment",
        entity_id=payment_id,
        action="repair",
        summary=f"Pago fallido clasificado como informativo {result.get('reference', payment_id)}",
        changed_by=current_user.get("username", "system"),
    )
    return PaymentResponse.model_validate(result)


@api_router.get("/payments/{payment_id}/link-candidates")
def payment_link_candidates_api(
    payment_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("payments.manage")),
):
    """Candidate shifts of the payment's property for linking a legacy payment."""
    payment = _scoped_payment(payment_id, prop_id)
    shifts = list_shifts(prop_id=int(payment.get("prop_id", 0) or 0), limit=50)
    return {"payment": payment, "shifts": shifts}


@api_router.post("/payments/{payment_id}/link-shift", response_model=PaymentResponse)
def link_payment_shift_api(
    payment_id: str,
    payload: dict = Body(default={}),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("payments.manage")),
):
    """Link a legacy payment (without shift) to the responsible shift.

    Stamps the shift FK + denormalized employee/opener on the payment and its
    fact mirror. The shift must belong to the same hotel as the payment.
    """
    _scoped_payment(payment_id, prop_id)
    shift_id = (payload or {}).get("shift_id")
    if not shift_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="shift_id es obligatorio: indicá el turno de caja e intentá de nuevo.",
        )
    try:
        result = link_payment_to_shift(
            payment_id,
            str(shift_id),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "payment_already_linked":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El pago ya está vinculado a un turno: no hace falta volver a vincularlo.",
            ) from exc
        if code == "shift_prop_mismatch":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "El turno pertenece a otro hotel. Elegí un turno abierto del hotel del pago e intentá "
                    "de nuevo."
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el pago o el turno. Verificá los identificadores e intentá de nuevo.",
        ) from exc
    result = to_json_safe(result)
    register_action(
        prop_id=int(result.get("prop_id") or 0),
        entity_type="billing_payment",
        entity_id=payment_id,
        action="link_shift",
        summary=f"Pago {result.get('reference', payment_id)} vinculado al turno {shift_id}",
        changed_by=current_user.get("username", "system"),
    )
    return PaymentResponse.model_validate(result)


@api_router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_api(
    request: Request,
    payment_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("payments.read")),
):
    prop_id = _require_billing_scope(prop_id)
    result = get_payment(payment_id)
    if result is not None:
        result = to_json_safe(result)
    if result is None or int(result.get("prop_id", 0) or 0) != prop_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado en este hotel")
    register_action(
        prop_id=prop_id,
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
    prop_id: int | None = Query(default=None, ge=1),
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_prop_permission("payments.manage")),
):
    before = _scoped_payment(payment_id, prop_id)
    if not isinstance(payload, dict):
        payload = {}
    # A refund moves money back to the guest — it must be attributable to the
    # cashier on duty, same as any other cash movement.
    refund_prop_id = int((before or {}).get("prop_id", 0) or 0)
    shift_id = _require_active_shift_for_money(refund_prop_id)
    refund_id = str(payload.get("refund_id") or "").strip() or None
    refund_reason = str(payload.get("reason") or "").strip() or None
    result = refund_payment(
        payment_id,
        refund_id=refund_id,
        refund_reason=refund_reason,
        changed_by=str(current_user.get("username", "system")),
        shift_id=shift_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo reembolsar el pago. Verificá que el pago esté confirmado y que haya un turno "
                "de caja activo, e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)
    diff = {
        "status": {"old": before.get("status") if before else None, "new": "refunded"},
        "refund_reason": {"old": before.get("refund_reason") if before else None, "new": refund_reason},
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
    # Auth middleware hands a BSON ObjectId; harden against a legacy hex-string
    # _id so the ObjectId filter still matches (same pattern as queries.py).
    if isinstance(user_id, str) and ObjectId.is_valid(user_id):
        user_id = ObjectId(user_id)
    # Find all bookings for this user. The join key is the BUSINESS
    # ``booking_id`` (``BK-…``, fecha + ticket) — ``reservation_invoices``
    # stores that string, NOT the Mongo ``_id``. Joining with ``_id``
    # (ObjectId) silently returns zero invoices.
    booking_ids = [
        b["booking_id"]
        for b in db.booking_orders.find(
            {"user_id": user_id},
            {"booking_id": 1, "_id": 0},
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
    # Belt-and-suspenders: ``_enrich_invoice`` formats issued_at/paid_at but
    # leaves created_at/updated_at as raw datetimes; ``to_json_safe`` handles
    # the rest (datetime → ISO, nested ObjectId → str) before the wire model.
    items = [to_json_safe(_enrich_invoice(doc)) for doc in cursor]
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
    current_user: dict = Depends(require_prop_permission("billing.read")),
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
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("billing.read")),
):
    """Get the folio for a booking."""
    result = get_folio(booking_id)
    if result is not None:
        result = to_json_safe(result)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un folio para esta reserva. Verificá el número de reserva e intentá de nuevo.",
        )
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_folio",
        entity_id=booking_id,
        action="read",
        summary=f"Consulta de folio para reserva {booking_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    # Traza de acceso a datos sensibles: quién consultó la atribución de
    # turno (turno que abrió el folio + cajero responsable).
    if result.get("created_shift") or result.get("shift_id"):
        register_shift_attribution_access(
            prop_id=(result.get("prop_id") or 0),
            entity_id=booking_id,
            source="folio",
            shift_id=result.get("shift_id"),
            shift=result.get("created_shift"),
            changed_by=current_user.get("username", "system"),
            url=str(request.url),
        )
    return FolioResponse.model_validate(result)


@api_router.post("/folios/{booking_id}/post", response_model=FolioResponse)
def post_to_folio_api(
    booking_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
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
    # Folio postings (charges/discounts/payments) are money operations: the
    # responsible shift and cashier are stamped on every posting entry.
    post_prop_id = int((before or {}).get("prop_id", 0) or 0)
    shift_id = _require_active_shift_for_money(post_prop_id)
    shift_attribution = get_shift_attribution(shift_id)
    result = post_to_folio(
        booking_id,
        posting_type=payload.get("posting_type", "charge"),
        category=payload.get("category", "Otros"),
        concept=payload.get("concept", ""),
        amount=float(payload.get("amount", 0)),
        quantity=int(payload.get("quantity", 1)),
        reference_id=payload.get("reference_id", ""),
        reference_type=payload.get("reference_type", "manual"),
        shift_id=shift_id,
        shift_attribution=shift_attribution,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el folio. Verificá el número de reserva e intentá de nuevo.",
        )
    # Belt-and-suspenders (same rationale as close_folio_api): post_to_folio
    # returns the raw Mongo doc; _enrich_folio ISO-formats the top-level
    # timestamps but nested postings still carry raw datetimes/ObjectIds.
    result = to_json_safe(result)
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


@api_router.post("/folios/{booking_id}/reopen", response_model=FolioResponse)
def reopen_folio_api(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("billing.manage")),
):
    """Reopen a closed folio with a collectible positive balance."""
    result = reopen_folio_with_balance(
        booking_id,
        changed_by=str(current_user.get("_id", current_user.get("username", "system"))),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El folio no tiene un saldo positivo cobrable o no existe. Verificá que el folio esté "
                "cerrado con saldo pendiente e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_folio",
        entity_id=booking_id,
        action="repair",
        summary=f"Reapertura de folio cobrable {result.get('folio_number', booking_id)}",
        changed_by=current_user.get("username", "system"),
        diff={"status": {"old": "closed", "new": result.get("status")}},
    )
    return FolioResponse.model_validate(result)


@api_router.post("/folios/{booking_id}/settle", response_model=FolioResponse)
def settle_folio_api(
    booking_id: str,
    payload: FolioSettlementRequest = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(
        require_any_prop_permission("billing.manage", FOLIO_ADJUST_APPROVAL_PERMISSION)
    ),
):
    """Resolve a folio balance with a payment or an approved exception."""
    settlement_type = payload.settlement_type.strip().lower()
    if settlement_type in {"write_off", "external_settlement"}:
        if not require_supervisor_authorization(
            get_database(),
            current_user,
            permission_code=FOLIO_ADJUST_APPROVAL_PERMISSION,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permiso requerido: {FOLIO_ADJUST_APPROVAL_PERMISSION}. "
                    "Solo un supervisor puede aprobar un write-off o una liquidación externa."
                ),
            )
    elif settlement_type == "payment" and not user_has_permission(
        get_database(), current_user, "billing.manage"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso requerido: billing.manage",
        )

    settlement_shift_id: str | None = None
    if settlement_type == "payment":
        db = get_database()
        booking = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1, "shift_id": 1})
        prop_id = int((booking or {}).get("prop_id", 0) or 0)
        if payload.settlement_at is not None:
            # Historical cash may use only the reconstructed closed shift tied
            # to this booking; it must never be redirected to today's drawer.
            historical_shift_id = booking.get("shift_id") if booking else None
            try:
                historical_shift = db.reception_shifts.find_one({"_id": historical_shift_id, "prop_id": prop_id}) if historical_shift_id else None
            except Exception:
                historical_shift = None
            if not is_historical_cash_shift_eligible(historical_shift or {}, booking_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "El pago histórico requiere el turno reconstruido del checkout. Reconstruí el "
                        "turno del checkout o contactá a un supervisor e intentá de nuevo."
                    ),
                )
            settlement_shift_id = str(historical_shift["_id"])
        else:
            # Every settlement is a money operation — cash, card or transfer —
            # and must be attributable to the cashier on duty.
            settlement_shift_id = _require_active_shift_for_money(prop_id)
    try:
        result = settle_folio(
            booking_id,
            payload.model_dump(exclude_none=True),
            changed_by=current_user.get("username", "system"),
            actor_user_id=current_user.get("_id"),
            shift_id=settlement_shift_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El folio no está abierto con saldo cobrable. Verificá que el folio esté abierto y tenga "
                "saldo pendiente, e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)
    register_action(
        prop_id=(result.get("prop_id") or 0),
        entity_type="billing_folio",
        entity_id=booking_id,
        action="settle",
        summary=f"Liquidación explícita de folio {result.get('folio_number', booking_id)} ({result.get('settlement_type', '')})",
        changed_by=current_user.get("username", "system"),
        diff={
            "status": {"old": "open", "new": result.get("status")},
            "total_due": {"old": None, "new": result.get("total_due")},
        },
        metadata={
            "settlement_type": result.get("settlement_type"),
            "settlement_amount": result.get("settlement_amount"),
            "idempotency_key": payload.idempotency_key,
            "actor_user_id": str(current_user.get("_id")) if current_user.get("_id") else None,
        },
    )
    return FolioResponse.model_validate(result)


@api_router.post("/folios/{booking_id}/close", response_model=FolioResponse)
def close_folio_api(
    booking_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(
        require_any_prop_permission("billing.manage", FOLIO_ADJUST_APPROVAL_PERMISSION)
    ),
):
    """Close a folio at check-out."""
    before = get_folio(booking_id)
    invoice_id = payload.get("invoice_id")
    close_reason = payload.get("close_reason")
    # Cerrar un folio CON SALDO mediante una excepción (write-off, cortesía o
    # settlement externo) es un ajuste financiero: la recepción tiene
    # ``billing.manage`` pero NO puede condonar saldos sin aprobación de
    # supervisor (mismo patrón del gate gerencial unificado, allow-list
    # ``SUPERVISOR_AUTHORIZATION_ROLES``).
    exception_reasons = {"approved_write_off", "complimentary_stay", "approved_external_settlement"}
    reason_code = str(close_reason or "").strip().split(":", 1)[0].strip().lower()
    if reason_code in exception_reasons and not require_supervisor_authorization(
        get_database(),
        current_user,
        permission_code=FOLIO_ADJUST_APPROVAL_PERMISSION,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Permiso requerido: {FOLIO_ADJUST_APPROVAL_PERMISSION}. "
                "Solo un supervisor (gerente de hotel, admin de sistema o super_admin) "
                "puede cerrar un folio con saldo mediante write-off, cortesía o settlement externo: "
                "pedile a un supervisor que autorice el cierre."
            ),
        )
    result = close_folio(
        booking_id,
        invoice_id=invoice_id,
        closed_by=str(current_user.get("_id", "")),
        close_reason=close_reason,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede cerrar un folio con saldo sin un close_reason de excepción aprobado. "
                "Registrá el pago del saldo o, si aplica un write-off / cortesía / settlement externo, "
                "pedile a un supervisor que autorice el cierre."
            ),
        )
    # Belt-and-suspenders: defensive JSON-safe wrap (ObjectId → str, datetime →
    # ISO) before the wire model — close_folio returns the raw Mongo doc whose
    # updated_at/closed_at are native datetimes and invoice_id is an ObjectId.
    result = to_json_safe(result)
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
    current_user: dict = Depends(require_prop_permission("billing.read")),
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


@api_router.get("/my-invoices/{invoice_id}", response_model=InvoiceResponse)
def my_invoice_detail_api(
    invoice_id: str,
    current_user: dict = Depends(require_permission("account.read")),
):
    """Self-service detail of an invoice owned by the current user.

    Excepción global documentada (mismo patrón que ``my_invoices_api``): el
    huésped NO tiene contexto de hotel; la factura se resuelve y el acceso
    se auto-escopa por ``user_id`` vía ``booking_orders`` (403 si la factura
    no pertenece al usuario actual).
    """
    db = get_database()
    from bson import ObjectId

    inv = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la factura. Verificá el identificador de la factura e intentá de nuevo.",
        )
    # Ownership check — join por el booking_id de NEGOCIO (``BK-…``), que es
    # lo que ``reservation_invoices.booking_id`` almacena (no el ``_id``).
    user_id = current_user.get("_id")
    if isinstance(user_id, str) and ObjectId.is_valid(user_id):
        user_id = ObjectId(user_id)
    booking = db.booking_orders.find_one({"booking_id": inv["booking_id"], "user_id": user_id})
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Esta factura no pertenece al usuario actual. Verificá que estés iniciando sesión con "
                "la cuenta que hizo la reserva e intentá de nuevo."
            ),
        )
    result = get_invoice(invoice_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la factura. Verificá el identificador de la factura e intentá de nuevo.",
        )
    result = to_json_safe(result)
    register_action(
        prop_id=(inv.get("prop_id") or 0),
        entity_type="billing_invoice",
        entity_id=invoice_id,
        action="read",
        summary=f"Detalle de mi factura {result.get('invoice_number', invoice_id)} (self-service)",
        changed_by=current_user.get("username", "system"),
        metadata={
            "user_id": str(user_id),
            "source": "my-invoices",
            "url": f"/api/billing/my-invoices/{invoice_id}",
        },
    )
    return InvoiceResponse.model_validate(result)


@api_router.post("/my-invoices/{invoice_id}/pay", response_model=ActionResponse)
def my_invoice_pay_api(
    invoice_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("account.update")),
):
    """Simulate payment for an invoice (client-facing). Generates a realistic payment record.

    Acepta un ``amount`` opcional en el body para pagos parciales: debe ser
    mayor a 0 y no exceder el saldo pendiente (total − pagos confirmados). Si
    no se envía, paga el saldo restante completo. El gate es
    ``require_permission("account.update")`` — autoservicio del huésped, SIN
    ``require_prop_permission``/prop_id.
    """
    from src.app.modules.billing.schemas import PaymentCreate
    db = get_database()
    from bson import ObjectId

    inv = db.reservation_invoices.find_one({"_id": ObjectId(invoice_id)})
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la factura. Verificá el identificador de la factura e intentá de nuevo.",
        )

    # Verify the invoice belongs to a booking owned by this user. The
    # ownership check joins by the BUSINESS ``booking_id`` (``BK-…``, fecha +
    # ticket), which is what ``reservation_invoices.booking_id`` stores —
    # not the Mongo ``_id``.
    user_id = current_user.get("_id")
    # Same defensive hex-string normalization as ``my_invoices_api`` (auth
    # middleware hands ObjectId; legacy _id strings are normalized to match).
    if isinstance(user_id, str) and ObjectId.is_valid(user_id):
        user_id = ObjectId(user_id)
    booking = db.booking_orders.find_one({"booking_id": inv["booking_id"], "user_id": user_id})
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Esta factura no pertenece al usuario actual. Verificá que estés iniciando sesión con "
                "la cuenta que hizo la reserva e intentá de nuevo."
            ),
        )

    if inv.get("status") != "issued":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La factura no está pendiente de pago. Solo se pueden pagar facturas emitidas sin pagos "
                "confirmados; verificá el estado de la factura e intentá de nuevo."
            ),
        )

    # Saldo pendiente de ESTA factura = total − pagos confirmados sobre ella.
    # Soporta pagos parciales (la cascade en create_payment marca la factura
    # como ``partially_paid`` hasta cubrirla).
    invoice_total = float(inv.get("total", 0) or 0)
    confirmed_paid = sum(
        float(r.get("amount", 0) or 0)
        for r in db.reservation_payments.find(
            {"invoice_id": ObjectId(invoice_id), "status": "confirmed"},
            {"amount": 1},
        )
    )
    remaining = round(invoice_total - confirmed_paid, 2)

    raw_amount = payload.get("amount")
    if raw_amount is None:
        amount = remaining
    else:
        try:
            amount = round(float(raw_amount), 2)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monto inválido: ingresá un número válido.",
            ) from None
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El monto a pagar debe ser mayor a cero.",
            )
        if amount > remaining + 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El pago excede el saldo pendiente de la factura.",
            )
        if amount > remaining:
            amount = remaining  # clamp el centavo de tolerancia

    before = get_invoice(invoice_id)
    # Create the payment
    pay_payload = PaymentCreate(
        booking_id=str(inv["booking_id"]),
        invoice_id=invoice_id,
        amount=amount,
        method="bank_transfer",
    )
    try:
        result = create_payment(pay_payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No se pudo procesar el pago. Verificá el importe, el método de pago y que haya un "
                "turno de caja activo, e intentá de nuevo."
            ),
        )
    result = to_json_safe(result)

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
