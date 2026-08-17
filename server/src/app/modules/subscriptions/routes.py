"""Endpoints del dueño de suscripción (Fase 3 — PLAN_SUSCRIPCION_Y_PAGOS.md §6.1).

Rutas bajo ``/api/billing/subscriptions/me``:

- ``GET  /me``           → suscripción + plan + estado + próxima factura + métodos.
- ``POST /me/choose``    → confirma banda derivada + ciclo + método de pago.
- ``POST /me/pay``       → registra comprobante (``pending_verification``).
- ``GET  /me/invoices``  → historial de facturas.

Gate: ``require_login`` + pertenencia estricta — el dueño solo ve SU
suscripción, resuelta por ``dim_hotels.owner_user_id`` (deny-by-default
estructural; no hay ``prop_id`` en el path que un dueño pueda manipular).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr
from src.app.modules.subscriptions import service
from src.app.modules.subscriptions.payment_methods import available_payment_methods
from src.app.security.dependencies import require_login
from src.database.connection import get_database

api_router = APIRouter(prefix="/api/billing/subscriptions", tags=["subscriptions"])


def _require_owner_subscription(db, user) -> dict[str, Any]:
    """Resuelve la suscripción del dueño logueado (pertenencia estricta)."""
    hotel = db.dim_hotels.find_one({"owner_user_id": user["_id"]})
    if not hotel:
        raise HTTPException(
            status_code=404, detail="No hay un alojamiento asociado a esta cuenta."
        )
    sub = db.subscriptions.find_one({"prop_id": hotel.get("prop_id")})
    if not sub:
        raise HTTPException(
            status_code=404, detail="Tu alojamiento aún no tiene una suscripción."
        )
    return sub


# ── Pydantic *Response models ─────────────────────────────────────────


class SubscriptionInvoiceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    invoice_number: str = ""
    period_start: datetime | None = None
    period_end: datetime | None = None
    amount_usd: float
    currency: str = "USD"
    status: str
    due_date: datetime | None = None
    paid_at: datetime | None = None


class SubscriptionMeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    band: int
    band_label: str = ""
    billing_cycle: str
    price_usd: float
    currency: str = "USD"
    payment_method: str | None = None
    status: str
    renews_at: datetime | None = None
    current_period_end: datetime | None = None
    next_invoice: SubscriptionInvoiceResponse | None = None
    payment_methods: list[dict] = []


class InvoiceListResponse(BaseModel):
    items: list[SubscriptionInvoiceResponse]


class ChooseRequest(BaseModel):
    band: int
    billing_cycle: str = "monthly"
    payment_method: str


class ChooseResponse(BaseModel):
    ok: bool = True
    band: int
    billing_cycle: str
    payment_method: str
    price_usd: float
    message: str = ""


class PayRequest(BaseModel):
    invoice_id: str
    method: str
    reference: str = ""
    amount: float


class PayResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ok: bool = True
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    status: str
    message: str = ""


SubscriptionMeResponse.model_rebuild()
SubscriptionInvoiceResponse.model_rebuild()
InvoiceListResponse.model_rebuild()
PayResponse.model_rebuild()


# ── Endpoints ─────────────────────────────────────────────────────────


@api_router.get("/me", response_model=SubscriptionMeResponse)
def get_my_subscription(current_user: dict = Depends(require_login)):
    db = get_database()
    sub = _require_owner_subscription(db, current_user)
    inv = db.subscription_invoices.find_one(
        {"subscription_id": sub["_id"]},
        sort=[("created_at", -1)],
    )
    methods = [
        {k: v for k, v in m.items() if k != "_id"}
        for m in available_payment_methods(db)
    ]
    return SubscriptionMeResponse.model_validate(
        {**sub, "next_invoice": inv, "payment_methods": methods}
    )


@api_router.get("/me/invoices", response_model=InvoiceListResponse)
def list_my_invoices(current_user: dict = Depends(require_login)):
    db = get_database()
    sub = _require_owner_subscription(db, current_user)
    invoices = list(
        db.subscription_invoices.find({"subscription_id": sub["_id"]}).sort(
            "created_at", -1
        )
    )
    return InvoiceListResponse(
        items=[SubscriptionInvoiceResponse.model_validate(i) for i in invoices]
    )


@api_router.post("/me/choose", response_model=ChooseResponse)
def choose_my_subscription(
    payload: ChooseRequest,
    current_user: dict = Depends(require_login),
):
    db = get_database()
    sub = _require_owner_subscription(db, current_user)
    try:
        updated = service.choose_subscription(
            db,
            subscription_id=sub["_id"],
            band=payload.band,
            billing_cycle=payload.billing_cycle,
            payment_method=payload.payment_method,
            changed_by=(current_user or {}).get("username", "system"),
        )
    except service.SubscriptionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChooseResponse(
        ok=True,
        band=updated["band"],
        billing_cycle=updated["billing_cycle"],
        payment_method=updated["payment_method"] or "",
        price_usd=updated["price_usd"],
        message="Plan actualizado.",
    )


@api_router.post("/me/pay", response_model=PayResponse)
def pay_my_subscription(
    payload: PayRequest,
    current_user: dict = Depends(require_login),
):
    db = get_database()
    sub = _require_owner_subscription(db, current_user)
    try:
        pay = service.submit_payment(
            db,
            subscription_id=sub["_id"],
            invoice_id=payload.invoice_id,
            method=payload.method,
            reference=payload.reference,
            amount=payload.amount,
            changed_by=(current_user or {}).get("username", "system"),
        )
    except service.SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except service.SubscriptionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except service.SubscriptionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PayResponse.model_validate(
        {
            **pay,
            "ok": True,
            "message": "Comprobante registrado. Está pendiente de verificación.",
        }
    )
