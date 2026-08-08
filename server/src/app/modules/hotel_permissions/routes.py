"""Fase 2 — API 'Equipo y permisos del hotel' (per-hotel RBAC admin).

Endpoints for managing ``hotel_roles`` (clone templates, adjust permissions,
activate/deactivate, delete) and ``role_assignments`` (assign, change role,
unassign) scoped to a single hotel ``prop_id``.

Every endpoint is gated by ``require_prop_permission("hotel.manage_roles")``
which (a) validates the user can access the hotel (``user_can_access_hotel``)
and (b) resolves the permission through the user's hotel-scoped role
(``role_assignments`` → ``hotel_roles``), deny-by-default when the user has
no assignment for the hotel.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr
from src.app.modules.hotel_permissions import service
from src.app.modules.hotel_permissions.service import ConflictError
from src.app.security.dependencies import require_prop_permission
from src.app.security.role_helpers import is_super_admin
from src.database.connection import get_database


def _actor_ctx(current_user: dict) -> dict:
    """Anti self-lockout context: who is acting and whether they are global admin.

    ``actor_user_id`` is the raw Mongo ``_id`` (ObjectId); ``actor_is_super_admin``
    lets ``super_admin`` keep its override (they are the safety net that fixes
    broken hotels, so self-protection does not apply to them).
    """
    return {
        "actor_user_id": (current_user or {}).get("_id"),
        "actor_is_super_admin": is_super_admin(current_user or {}),
    }

api_router = APIRouter(
    prefix="/api/management/hotels/{prop_id}",
    tags=["hotel-permissions"],
)

# ─── Pydantic *Response models (wire-shape convention) ─────────────────
# KEEP IN SYNC: los DTO de TypeScript espejo viven en
# frontend/src/app/features/<feature>/models/ (Fase 2 UI, pendiente).


class HotelRoleResponse(BaseModel):
    """A single hotel role. ``id`` = hotel_roles._id."""

    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    name: str = ""
    display_name: str = ""
    permissions: list[str] = []
    based_on_role_id: ObjectIdStr | None = None
    based_on: str = ""
    is_active: bool = True
    is_system: bool = False
    assignment_count: int = 0
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RoleTemplateResponse(BaseModel):
    """A global role usable as clone source (template)."""

    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    role_name: str = ""
    display_name: str = ""
    permissions: list[str] = []


class HotelRoleListResponse(BaseModel):
    """Envelope: hotel roles + clone templates + full permission catalog."""

    items: list[HotelRoleResponse]
    templates: list[RoleTemplateResponse]
    permission_codes: list[str]


class TeamMemberResponse(BaseModel):
    """A user of the hotel (for the team view)."""

    user_id: ObjectIdStr
    username: str = ""
    display_name: str = ""


class AssignmentResponse(BaseModel):
    """A user × hotel × role assignment, joined with user + role display info."""

    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int
    user_id: ObjectIdStr
    username: str = ""
    display_name: str = ""
    role_id: ObjectIdStr
    role_name: str = ""
    role_display_name: str = ""
    assigned_by: str = ""
    assigned_at: datetime | None = None


class HotelTeamResponse(BaseModel):
    """The hotel team: assigned members + hotel staff without a role yet."""

    assigned: list[AssignmentResponse]
    unassigned_staff: list[TeamMemberResponse]


class ActionResponse(BaseModel):
    ok: bool = True
    message: str = ""


class RoleAuditEntryResponse(BaseModel):
    """A single audit_log row for a hotel role change."""

    timestamp: datetime | None = None
    action: str = ""
    changed_by: str = ""
    summary: str = ""
    diff: dict[str, Any] | None = None


class RoleAuditResponse(BaseModel):
    """Role summary (creator, dates, base template) + chronological change history."""

    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    name: str = ""
    display_name: str = ""
    based_on: str = ""
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    permission_count: int = 0
    entries: list[RoleAuditEntryResponse] = []


# Rebuild Pydantic v2 models to resolve string-lazy annotations from
# ``from __future__ import annotations`` (see knowledge.md — Fase 6 COGS 500
# incident). Without this, FastAPI's TypeAdapter binding raises
# ``PydanticUserError`` / ``PydanticUndefinedAnnotation`` on first request.
HotelRoleResponse.model_rebuild()
RoleTemplateResponse.model_rebuild()
HotelRoleListResponse.model_rebuild()
TeamMemberResponse.model_rebuild()
AssignmentResponse.model_rebuild()
HotelTeamResponse.model_rebuild()
ActionResponse.model_rebuild()
RoleAuditEntryResponse.model_rebuild()
RoleAuditResponse.model_rebuild()

# ─── hotel_roles ────────────────────────────────────────────────────────


@api_router.get("/roles", response_model=HotelRoleListResponse)
def list_roles(
    prop_id: int,
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> HotelRoleListResponse:
    db = get_database()
    return HotelRoleListResponse.model_validate(
        service.list_hotel_roles(db, prop_id)
    )


@api_router.post(
    "/roles",
    response_model=HotelRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    prop_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> HotelRoleResponse:
    db = get_database()
    try:
        role = service.create_hotel_role(
            db,
            prop_id,
            name=str(payload.get("name") or ""),
            display_name=str(payload.get("display_name") or ""),
            permissions=payload.get("permissions") or [],
            based_on_role_id=payload.get("based_on_role_id"),
            created_by=(current_user or {}).get("username", "system"),
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return HotelRoleResponse.model_validate(role)


@api_router.put("/roles/{role_id}", response_model=HotelRoleResponse)
def update_role(
    prop_id: int,
    role_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> HotelRoleResponse:
    db = get_database()
    try:
        role = service.update_hotel_role(
            db,
            prop_id,
            role_id,
            display_name=payload.get("display_name"),
            permissions=payload.get("permissions"),
            is_active=payload.get("is_active"),
            changed_by=(current_user or {}).get("username", "system"),
            **_actor_ctx(current_user),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Rol no encontrado en este hotel.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return HotelRoleResponse.model_validate(role)


@api_router.delete("/roles/{role_id}", response_model=ActionResponse)
def delete_role(
    prop_id: int,
    role_id: str,
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> ActionResponse:
    db = get_database()
    try:
        service.delete_hotel_role(
            db,
            prop_id,
            role_id,
            changed_by=(current_user or {}).get("username", "system"),
            **_actor_ctx(current_user),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Rol no encontrado en este hotel.")
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ActionResponse(ok=True, message="Rol eliminado.")


@api_router.get("/roles/{role_id}/audit", response_model=RoleAuditResponse)
def role_audit(
    prop_id: int,
    role_id: str,
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> RoleAuditResponse:
    """Auditoría de un rol: creador, fechas, plantilla base y cambios de permisos.

    El historial viene de ``audit_log`` (entity_type="hotel_role"). Roles
    creados antes del audit trail responden 200 con ``entries=[]``.
    """
    db = get_database()
    try:
        return RoleAuditResponse.model_validate(
            service.get_role_audit(db, prop_id, role_id)
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Rol no encontrado en este hotel.")


# ─── role_assignments ───────────────────────────────────────────────────


@api_router.get("/assignments", response_model=HotelTeamResponse)
def list_assignments(
    prop_id: int,
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> HotelTeamResponse:
    db = get_database()
    return HotelTeamResponse.model_validate(
        service.list_hotel_assignments(db, prop_id)
    )


@api_router.post(
    "/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    prop_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> AssignmentResponse:
    db = get_database()
    try:
        assignment = service.assign_user_to_role(
            db,
            prop_id,
            user_id=str(payload.get("user_id") or ""),
            role_id=str(payload.get("role_id") or ""),
            assigned_by=(current_user or {}).get("username", "system"),
            **_actor_ctx(current_user),
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AssignmentResponse.model_validate(assignment)


@api_router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    prop_id: int,
    assignment_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> AssignmentResponse:
    db = get_database()
    try:
        assignment = service.update_assignment_role(
            db,
            prop_id,
            assignment_id,
            role_id=str(payload.get("role_id") or ""),
            **_actor_ctx(current_user),
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return AssignmentResponse.model_validate(assignment)


@api_router.delete("/assignments/{assignment_id}", response_model=ActionResponse)
def delete_assignment(
    prop_id: int,
    assignment_id: str,
    current_user: dict = Depends(require_prop_permission("hotel.manage_roles")),
) -> ActionResponse:
    db = get_database()
    try:
        service.delete_assignment(db, prop_id, assignment_id, **_actor_ctx(current_user))
    except KeyError:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ActionResponse(ok=True, message="Asignación eliminada.")
