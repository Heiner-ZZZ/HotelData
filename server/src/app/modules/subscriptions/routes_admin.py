"""Fase 4 — Cola de conciliación de suscripciones (admin, gate supervisor).

Endpoints bajo ``/api/admin/subscriptions`` (PLAN_SUSCRIPCION_Y_PAGOS.md §6.2):

- ``GET  /payments``                           → cola de comprobantes (status).
- ``POST /payments/{payment_id}/verify``       → verified + factura paid + suscripción active.
- ``POST /payments/{payment_id}/reject``       → rejected + suscripción → pending_payment (motivo obligatorio).
- ``POST /{prop_id}/override``                 → precio negociado (price_band_override=true, auditado).
- ``POST /{prop_id}/cancel``                   → cancela la suscripción (terminal).

Todas las rutas exigen ``billing.verify`` (``require_permission``). Las
mutaciones añaden el **gate de supervisor** (``require_supervisor_authorization``):
aunque un rol ad-hoc tuviera el código, solo ``gerente_hotel`` /
``admin_sistema`` / ``super_admin`` pueden conciliar dinero o gestionar la
suscripción (defensa en profundidad, mismo patrón que el write-off de folio).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr
from src.app.modules.subscriptions import service
from src.app.security.dependencies import require_permission
from src.app.security.hotel_filter import (
    assigned_hotels_for_user,
    user_can_access_hotel,
)
from src.app.security.permissions import require_supervisor_authorization
from src.database.connection import get_database

BILLING_VERIFY_PERMISSION = "billing.verify"

api_router = APIRouter(prefix="/api/admin/subscriptions", tags=["subscriptions-admin"])


def _require_billing_supervisor(db, user: dict) -> None:
    """Gate de supervisor: rol allow-list + permiso ``billing.verify``."""
    if not require_supervisor_authorization(
        db,
        user,
        permission_code=BILLING_VERIFY_PERMISSION,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Permiso requerido: {BILLING_VERIFY_PERMISSION}. "
                "Solo un supervisor puede conciliar comprobantes o gestionar suscripciones."
            ),
        )


def _require_hotel_in_scope(user: dict, prop_id: int) -> None:
    """Scoping por hotel (plan §6.3): los roles hoteleros (``gerente_hotel``)
    solo operan SU propiedad; los roles no filtrados (super_admin/admin_sistema)
    mantienen la cola cross-hotel. Fuera de alcance → 404 (no filtrar existencia)."""
    if not user_can_access_hotel(user, prop_id):
        raise HTTPException(
            status_code=404,
            detail=f"Suscripción no encontrada para el hotel {prop_id}.",
        )


# ── Pydantic *Response models ─────────────────────────────────────────


class AdminPaymentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    hotel_name: str = ""
    owner_username: str = ""
    method: str
    reference: str = ""
    amount: float
    status: str
    created_at: datetime | None = None


class AdminPaymentListResponse(BaseModel):
    items: list[AdminPaymentResponse]
    total: int
    page: int
    page_size: int


class AdminVerifyResponse(BaseModel):
    ok: bool = True
    payment_id: str
    status: str
    message: str = ""


class AdminRejectRequest(BaseModel):
    reason: str


class AdminRejectResponse(BaseModel):
    ok: bool = True
    payment_id: str
    status: str
    message: str = ""


class AdminOverrideRequest(BaseModel):
    price_band: int | None = None
    price_usd: float | None = None
    notes: str = ""


class AdminOverrideResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ok: bool = True
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    band: int
    band_label: str = ""
    price_usd: float
    price_band_override: bool = False
    pending_price_band: int | None = None
    pending_price_usd: float | None = None
    message: str = ""


class AdminCancelRequest(BaseModel):
    reason: str = ""


class AdminCancelResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ok: bool = True
    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    status: str
    message: str = ""


AdminPaymentResponse.model_rebuild()
AdminPaymentListResponse.model_rebuild()
AdminVerifyResponse.model_rebuild()
AdminRejectResponse.model_rebuild()
AdminOverrideResponse.model_rebuild()
AdminCancelResponse.model_rebuild()


def _enrich_payment(db, pay: dict[str, Any]) -> dict[str, Any]:
    hotel = db.dim_hotels.find_one(
        {"prop_id": pay.get("prop_id")},
        {"hotel_name": 1, "display_name": 1, "owner_username": 1},
    )
    return {
        **pay,
        "hotel_name": (hotel or {}).get("hotel_name") or (hotel or {}).get("display_name") or "",
        "owner_username": (hotel or {}).get("owner_username") or "",
    }


# ── Endpoints ─────────────────────────────────────────────────────────


@api_router.get("/payments", response_model=AdminPaymentListResponse)
def list_pending_payments(
    status: str = "pending_verification",
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_permission(BILLING_VERIFY_PERMISSION)),
) -> AdminPaymentListResponse:
    db = get_database()
    prop_ids = assigned_hotels_for_user(current_user)
    data = service.list_subscription_payments(
        db, status=status, page=page, page_size=page_size, prop_ids=prop_ids
    )
    items = [_enrich_payment(db, p) for p in data["items"]]
    return AdminPaymentListResponse(
        items=[AdminPaymentResponse.model_validate(i) for i in items],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )


@api_router.post("/payments/{payment_id}/verify", response_model=AdminVerifyResponse)
def verify_payment(
    payment_id: str,
    current_user: dict = Depends(require_permission(BILLING_VERIFY_PERMISSION)),
) -> AdminVerifyResponse:
    db = get_database()
    _require_billing_supervisor(db, current_user)
    try:
        result = service.verify_payment(
            db,
            payment_id=payment_id,
            verified_by=(current_user or {}).get("username", "system"),
            allowed_prop_ids=assigned_hotels_for_user(current_user),
        )
    except service.SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except service.SubscriptionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return AdminVerifyResponse(
        ok=True,
        payment_id=str(result["_id"]),
        status=result["status"],
        message="Comprobante verificado. La suscripción quedó activa.",
    )


@api_router.post("/payments/{payment_id}/reject", response_model=AdminRejectResponse)
def reject_payment(
    payment_id: str,
    payload: AdminRejectRequest,
    current_user: dict = Depends(require_permission(BILLING_VERIFY_PERMISSION)),
) -> AdminRejectResponse:
    db = get_database()
    _require_billing_supervisor(db, current_user)
    try:
        result = service.reject_payment(
            db,
            payment_id=payment_id,
            reason=payload.reason,
            rejected_by=(current_user or {}).get("username", "system"),
            allowed_prop_ids=assigned_hotels_for_user(current_user),
        )
    except service.SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except service.SubscriptionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AdminRejectResponse(
        ok=True,
        payment_id=str(result["_id"]),
        status=result["status"],
        message="Comprobante rechazado. La suscripción volvió a pago pendiente.",
    )


@api_router.post("/{prop_id}/override", response_model=AdminOverrideResponse)
def override_subscription(
    prop_id: int,
    payload: AdminOverrideRequest,
    current_user: dict = Depends(require_permission(BILLING_VERIFY_PERMISSION)),
) -> AdminOverrideResponse:
    db = get_database()
    _require_billing_supervisor(db, current_user)
    _require_hotel_in_scope(current_user, prop_id)
    try:
        result = service.override_subscription(
            db,
            prop_id=prop_id,
            price_band=payload.price_band,
            price_usd=payload.price_usd,
            notes=payload.notes,
            changed_by=(current_user or {}).get("username", "system"),
        )
    except service.SubscriptionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    scheduled = result.get("pending_price_band") is not None or result.get(
        "pending_price_usd"
    ) is not None
    message = (
        "Override programado para el siguiente ciclo (preaviso)."
        if scheduled
        else "Override de precio aplicado."
    )
    return AdminOverrideResponse.model_validate(
        {**result, "ok": True, "message": message}
    )


@api_router.post("/{prop_id}/cancel", response_model=AdminCancelResponse)
def cancel_subscription(
    prop_id: int,
    payload: AdminCancelRequest,
    current_user: dict = Depends(require_permission(BILLING_VERIFY_PERMISSION)),
) -> AdminCancelResponse:
    db = get_database()
    _require_billing_supervisor(db, current_user)
    _require_hotel_in_scope(current_user, prop_id)
    sub = service.get_subscription(db, prop_id=prop_id)
    if not sub:
        raise HTTPException(
            status_code=404,
            detail=f"Suscripción no encontrada para el hotel {prop_id}.",
        )
    try:
        result = service.cancel(
            db,
            subscription_id=sub["_id"],
            reason=payload.reason,
            changed_by=(current_user or {}).get("username", "system"),
        )
    except service.SubscriptionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return AdminCancelResponse.model_validate(
        {**result, "ok": True, "message": "Suscripción cancelada."}
    )
