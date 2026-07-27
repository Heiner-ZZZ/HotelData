from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr


# ─── Module Status (kept preexistente) ────────────────────────────────────────


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


# ─── Input DTOs (unchanged — wire-format bodies, not responses) ──────────────


class EmployeeCreate(BaseModel):
    full_name: str
    id_document: str
    phone: str = ""
    email: str = ""
    address: str = ""
    position: str = ""
    department: str = ""
    hire_date: str = ""
    salary: float | None = None
    emergency_contact: str = ""
    emergency_phone: str = ""
    notes: str = ""
    prop_id: int | None = None
    user_id: str | None = None
    daily_duties: list[dict] | None = None

    # Replacement logic
    replaces_employee_id: str | None = None
    transfer_shifts: bool = False
    transfer_permissions: bool = False
    transfer_tasks: bool = False


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    position: str | None = None
    department: str | None = None
    salary: float | None = None
    emergency_contact: str | None = None
    emergency_phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    user_id: str | None = None
    daily_duties: list[dict] | None = None


class DepartmentCreate(BaseModel):
    name: str
    description: str = ""
    head_count: int = 0


class EmployeeShiftCreate(BaseModel):
    employee_id: str
    date: str
    scheduled_start: str = ""
    scheduled_end: str = ""
    area: str = ""
    notes: str = ""


class EmployeeShiftCheckIn(BaseModel):
    employee_id: str
    timestamp: str | None = None
    notes: str = ""


class EmployeeShiftCheckOut(BaseModel):
    employee_id: str
    timestamp: str | None = None
    notes: str = ""


# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ────────────
# All class declarations BELOW this banner must be on their OWN line.
# See knowledge.md → "Anti-pattern: from __future__ + Pydantic + response_model"
# for the failure modes this layout prevents.


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    full_name: str | None = None
    id_document: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    position: str | None = None
    department: str | None = None
    hire_date: str | None = None
    salary: float | None = None
    emergency_contact: str | None = None
    emergency_phone: str | None = None
    notes: str | None = None
    prop_id: int | None = None
    user_id: str | None = None
    is_active: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None
    department_id: ObjectIdStr | None = Field(default=None, validation_alias="department_id", serialization_alias="department_id")
    position_id: ObjectIdStr | None = Field(default=None, validation_alias="position_id", serialization_alias="position_id")
    daily_duties: list[Any] | None = None


class EmployeeListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[EmployeeResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str | None = None
    description: str | None = None
    head_count: int | None = None
    created_at: str | None = None


class DepartmentListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[DepartmentResponse] = Field(default_factory=list)
    total: int = 0


class EmployeeShiftResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    employee_id: str | None = None
    date: str | None = None
    scheduled_start: str | None = None
    scheduled_end: str | None = None
    area: str | None = None
    status: str | None = None
    actual_check_in: str | None = None
    actual_check_out: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    check_in_notes: str | None = None
    check_out_notes: str | None = None


class ShiftListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[EmployeeShiftResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class ShiftActionResponse(BaseModel):
    """Small action envelope returned by check-in / check-out."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    shift_id: str | None = None
    status: str | None = None
    check_in: str | None = None
    check_out: str | None = None


class EmployeePortalResponse(BaseModel):
    """Aggregator response — nested shape is fully permissive on purpose.

    The employee / kpis / weekly_roster / payroll / recent_events blobs
    each come from independent service code paths. Strictly typing every
    nested field would lock the schema prematurely; we accept the dict
    shapes verbatim under ``extra="allow"`` + ``populate_by_name=True``.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    employee: dict[str, Any] | None = None
    current_shift: dict[str, Any] | None = None
    kpis: dict[str, Any] | None = None
    weekly_roster: list[Any] = Field(default_factory=list)
    payroll: dict[str, Any] | None = None
    recent_events: list[Any] = Field(default_factory=list)


class PortalTasksResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    employee_id: str | None = None
    employee_name: str | None = None
    assigned_tasks: list[Any] = Field(default_factory=list)
    dirty_rooms: list[Any] = Field(default_factory=list)
    daily_duties: list[Any] = Field(default_factory=list)


class MyPortalResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    employee_id: str | None = None
    full_name: str | None = None
    portal_url: str | None = None


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    employee_id: str | None = None
    employee_name: str | None = None
    month: str | None = None
    records: list[Any] = Field(default_factory=list)
    summary: dict[str, Any] | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    total_employees: int | None = None
    active_employees: int | None = None
    inactive_employees: int | None = None
    departments: int | None = None
    recent_hires: list[EmployeeResponse] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    employee_id: ObjectIdStr | None = Field(default=None, validation_alias="employee_id", serialization_alias="employee_id")
    doc_type: str | None = None
    title: str | None = None
    file_url: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[DocumentResponse] = Field(default_factory=list)
    total: int = 0


# ─── Explicit rebuilds ──────────────────────────────────────────────────────
# `from __future__ import annotations` defers ALL type hints as forward refs,
# so Pydantic v2 needs explicit `.model_rebuild()` to resolve `ObjectIdStr`
# (Annotated[str, BeforeValidator(...)]). Ordering: all class defs ABOVE,
# rebuilds BELOW, before any consumer imports them.

EmployeeResponse.model_rebuild()
EmployeeListResponse.model_rebuild()
DepartmentResponse.model_rebuild()
DepartmentListResponse.model_rebuild()
EmployeeShiftResponse.model_rebuild()
ShiftListResponse.model_rebuild()
ShiftActionResponse.model_rebuild()
EmployeePortalResponse.model_rebuild()
PortalTasksResponse.model_rebuild()
MyPortalResponse.model_rebuild()
AttendanceResponse.model_rebuild()
DashboardResponse.model_rebuild()
DocumentResponse.model_rebuild()
DocumentListResponse.model_rebuild()


# ─── Helpers (kept preexistente) ─────────────────────────────────────────────


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
