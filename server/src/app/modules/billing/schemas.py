from __future__ import annotations

from datetime import datetime, timezone


from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class InvoiceCreate(BaseModel):
    booking_id: str
    subtotal: float
    taxes: float = 0.0
    notes: str = ""


class InvoiceResponse(BaseModel):
    id: str = Field(alias="_id")
    booking_id: str
    invoice_number: str
    subtotal: float
    taxes: float
    total: float
    status: str
    issued_at: str
    paid_at: str | None = None
    notes: str | None = None
    # Cashier attribution: the shift that issued the fiscal document and the
    # one that cancelled it (null for legacy docs).
    shift_id: str | None = None
    shift_employee: str | None = None
    shift_opened_by: str | None = None
    shift_type: str | None = None
    cancelled_shift_id: str | None = None
    cancelled_shift_employee: str | None = None
    cancelled_shift_opened_by: str | None = None
    cancelled_shift_type: str | None = None


class PaymentCreate(BaseModel):
    booking_id: str
    invoice_id: str = ""
    amount: float
    method: str = "simulated"
    # Estado inicial del pago. "confirmed" es el flujo normal; un gateway puede
    # registrar "failed"/"rejected"/"declined"/"error" sin marcar la factura
    # como pagada (F1.5 mide pagos fallidos).
    status: str = "confirmed"


class PaymentResponse(BaseModel):
    id: str = Field(alias="_id")
    booking_id: str
    invoice_id: str | None = None
    amount: float
    method: str
    status: str
    reference: str | None = None
    paid_at: str
    # Cashier attribution: the shift that handled this payment and the
    # employee/opener stamped on it at write time (null for legacy docs).
    shift_id: str | None = None
    shift_employee: str | None = None
    shift_opened_by: str | None = None
    shift_type: str | None = None
    # Refund-side attribution (who authorized the money back).
    refund_shift_id: str | None = None
    refund_shift_employee: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
