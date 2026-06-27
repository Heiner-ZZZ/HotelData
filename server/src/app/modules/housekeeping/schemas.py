from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class RoomStatusLogCreate(BaseModel):
    prop_id: int
    room_type_id: str
    room_label: str
    status: str = "available"  # available, occupied, cleaning, maintenance, out_of_order
    note: str = ""


class RoomStatusLogResponse(BaseModel):
    id: str = Field(alias="_id")
    prop_id: int
    room_type_id: str
    room_label: str
    status: str
    note: str
    created_at: str
    updated_at: str | None = None


class HousekeepingTaskCreate(BaseModel):
    prop_id: int
    room_label: str
    task_type: str = "cleaning"  # cleaning, deep_clean, turnover, inspection
    assigned_to: str = ""
    priority: str = "normal"  # low, normal, high, urgent
    note: str = ""
    scheduled_date: str = ""
    status: str = "pending"


class HousekeepingTaskResponse(BaseModel):
    id: str = Field(alias="_id")
    prop_id: int
    room_label: str
    task_type: str
    status: str
    assigned_to: str
    priority: str
    note: str
    created_at: str
    completed_at: str | None = None


class MaintenanceTaskCreate(BaseModel):
    prop_id: int
    room_label: str
    task_type: str  # preventive, corrective, inspection
    title: str
    description: str = ""
    priority: str = "normal"
    scheduled_date: str = ""
    status: str = "scheduled"
    auto_block: bool = True  # RF-002: block room availability during maintenance


class MaintenanceTaskResponse(BaseModel):
    id: str = Field(alias="_id")
    prop_id: int
    room_label: str
    task_type: str
    title: str
    description: str
    status: str
    priority: str
    scheduled_date: str
    created_at: str
    completed_at: str | None = None


class AdditionalChargeCreate(BaseModel):
    booking_id: str
    prop_id: int
    concept: str
    amount: float
    quantity: int = 1
    note: str = ""


class AdditionalChargeResponse(BaseModel):
    id: str = Field(alias="_id")
    booking_id: str
    prop_id: int
    concept: str
    amount: float
    quantity: int
    total: float
    note: str
    created_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
