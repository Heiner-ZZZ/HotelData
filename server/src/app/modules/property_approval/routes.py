"""Fase 1 — Cola de aprobación de hoteles (admin).

Endpoints under ``/api/admin/property-registrations``:

- ``GET  /``                          → list registrations (filter by status).
- ``GET  /{prop_id}``                 → detail of one registration.
- ``POST /{prop_id}/approve``         → activate hotel + clone gerente role +
                                        assign owner (reuses Fase 2).

Every endpoint is gated by ``require_permission("properties.approve")`` (new
catalog code; super_admin has the ``*.*`` bypass, and admin_sistema +
gerente_hotel hold it in the canonical role map and sync map). The queue is
cross-hotel by design — it is NOT scoped by ``user_can_access_hotel``.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.app.modules.property_approval import service
from src.app.modules.property_approval.service import ConflictError
from src.app.security.dependencies import require_permission
from src.app.security.role_helpers import is_super_admin
from src.database.connection import get_database

api_router = APIRouter(prefix="/api/admin/property-registrations", tags=["property-approval"])


class RegistrationSummaryResponse(BaseModel):
    """One registration in the queue (declared data + owner)."""

    prop_id: int
    hotel_name: str = ""
    property_type: str = ""
    city: str = ""
    country_label: str = ""
    currency: str = ""
    total_rooms_declared: int = 0
    approval_status: str = ""
    submitted_at: datetime | None = None
    owner_username: str = ""
    owner_email: str = ""
    owner_display_name: str = ""


class RegistrationListResponse(BaseModel):
    """Envelope for the queue list."""

    items: list[RegistrationSummaryResponse]
    total: int
    status: str


class RegistrationDetailResponse(RegistrationSummaryResponse):
    """Full registration detail."""

    description: str = ""
    contact_phone: str = ""
    owner_user_id: str = ""
    status_changed_at: datetime | None = None


class ApproveResponse(BaseModel):
    """Result of approving a registration."""

    ok: bool = True
    prop_id: int
    hotel_role_id: str = ""
    assignment_id: str = ""
    price_band: int | None = None
    price_band_monthly_usd: float | None = None
    message: str = ""


class RejectRequest(BaseModel):
    """Body of POST /{prop_id}/reject — reason is mandatory."""

    reason: str


class RequestChangesRequest(BaseModel):
    """Body of POST /{prop_id}/request-changes — feedback is mandatory."""

    feedback: str


class TransitionResponse(BaseModel):
    """Result of reject / request-changes."""

    ok: bool = True
    prop_id: int
    approval_status: str = ""
    message: str = ""


@api_router.get("", response_model=RegistrationListResponse)
def list_registrations(
    status: str = service.PENDING,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_permission("properties.approve")),
) -> RegistrationListResponse:
    db = get_database()
    return RegistrationListResponse.model_validate(
        service.list_registrations(db, status=status, page=page, page_size=page_size)
    )


@api_router.get("/{prop_id}", response_model=RegistrationDetailResponse)
def registration_detail(
    prop_id: int,
    current_user: dict = Depends(require_permission("properties.approve")),
) -> RegistrationDetailResponse:
    db = get_database()
    data = service.get_registration(db, prop_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No existe el registro del hotel {prop_id}.")
    return RegistrationDetailResponse.model_validate(data)


@api_router.post("/{prop_id}/approve", response_model=ApproveResponse)
def approve_registration(
    prop_id: int,
    current_user: dict = Depends(require_permission("properties.approve")),
) -> ApproveResponse:
    db = get_database()
    try:
        result = service.approve_registration(
            db,
            prop_id,
            approver_username=(current_user or {}).get("username", "system"),
            actor_user_id=(current_user or {}).get("_id"),
            actor_is_super_admin=is_super_admin(current_user or {}),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No existe el registro del hotel {prop_id}.")
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ApproveResponse(
        ok=True,
        prop_id=result["prop_id"],
        hotel_role_id=result["hotel_role_id"],
        assignment_id=result["assignment_id"],
        price_band=result.get("price_band"),
        price_band_monthly_usd=result.get("price_band_monthly_usd"),
        message=result["message"],
    )


@api_router.post("/{prop_id}/reject", response_model=TransitionResponse)
def reject_registration(
    prop_id: int,
    payload: RejectRequest,
    current_user: dict = Depends(require_permission("properties.approve")),
) -> TransitionResponse:
    """Reject a registration with a mandatory reason (owner gets email)."""
    db = get_database()
    try:
        result = service.reject_registration(
            db,
            prop_id,
            reason=payload.reason,
            changed_by=(current_user or {}).get("username", "system"),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No existe el registro del hotel {prop_id}.")
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TransitionResponse(
        ok=True,
        prop_id=result["prop_id"],
        approval_status=result["approval_status"],
        message=result["message"],
    )


@api_router.post("/{prop_id}/request-changes", response_model=TransitionResponse)
def request_changes_registration(
    prop_id: int,
    payload: RequestChangesRequest,
    current_user: dict = Depends(require_permission("properties.approve")),
) -> TransitionResponse:
    """Ask the owner to fix data (pending → changes_requested + feedback email)."""
    db = get_database()
    try:
        result = service.request_changes_registration(
            db,
            prop_id,
            feedback=payload.feedback,
            changed_by=(current_user or {}).get("username", "system"),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No existe el registro del hotel {prop_id}.")
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TransitionResponse(
        ok=True,
        prop_id=result["prop_id"],
        approval_status=result["approval_status"],
        message=result["message"],
    )
