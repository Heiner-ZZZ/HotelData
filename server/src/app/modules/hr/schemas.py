from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


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
    prop_id: int | None = None  # Hotel/property assignment
    user_id: str | None = None  # Optional link to users collection for login credentials

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
    user_id: str | None = None  # Link/unlink to a users collection account


class EmployeeResponse(BaseModel):
    id: str = Field(alias="_id")
    full_name: str
    id_document: str
    phone: str
    email: str
    address: str
    position: str
    department: str
    hire_date: str
    salary: float | None
    emergency_contact: str
    emergency_phone: str
    notes: str
    prop_id: int | None = None
    user_id: str | None = None
    is_active: bool
    created_at: str
    updated_at: str


class DepartmentCreate(BaseModel):
    name: str
    description: str = ""
    head_count: int = 0


class DepartmentResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    head_count: int
    created_at: str


class EmployeeDocumentUpload(BaseModel):
    doc_type: str  # id_passport | contract | tax_form | certificate | other
    filename: str
    notes: str = ""


class EmployeeShiftCreate(BaseModel):
    employee_id: str
    date: str  # YYYY-MM-DD
    scheduled_start: str = ""  # HH:MM
    scheduled_end: str = ""  # HH:MM
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


class EmployeeShiftResponse(BaseModel):
    id: str = Field(alias="_id")
    employee_id: str
    date: str
    scheduled_start: str
    scheduled_end: str
    area: str
    status: str  # pending, active, completed, rest
    actual_check_in: str | None = None
    actual_check_out: str | None = None
    notes: str
    created_at: str


class EmployeePortalResponse(BaseModel):
    employee: dict
    current_shift: dict | None = None
    kpis: dict
    weekly_roster: list[dict]
    payroll: dict
    recent_events: list[dict]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
