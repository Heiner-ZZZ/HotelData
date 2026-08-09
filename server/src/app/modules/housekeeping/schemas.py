from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


# ── Room Statuses (Hotel cycle) ──
#
# The complete housekeeping lifecycle:
#   occupied_clean → occupied_dirty → vacant_dirty
#   → cleaning_in_progress → cleaning_completed
#   → inspected → vacant_clean → (available for booking)
#
#   maintenance_requested → out_of_service/out_of_order
#   → (repair completed) → inspected

ROOM_STATUSES = {
    "vacant_dirty": "Vacante Sucia",
    "vacant_clean": "Vacante Limpia",
    "occupied_clean": "Ocupada Limpia",
    "occupied_dirty": "Ocupada Sucia",
    "cleaning_in_progress": "Limpieza en Progreso",
    "cleaning_completed": "Limpieza Completada",
    "inspected": "Inspeccionada",
    "out_of_service": "Fuera de Servicio",
    "out_of_order": "Fuera de Orden",
    "maintenance_requested": "Mantenimiento Solicitado",
}

# Valid transitions (old_status → [new_statuses])
ROOM_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "vacant_dirty": ["cleaning_in_progress", "maintenance_requested"],
    "vacant_clean": ["occupied_clean", "cleaning_in_progress"],
    "occupied_clean": ["occupied_dirty", "vacant_dirty"],
    "occupied_dirty": ["cleaning_in_progress", "vacant_dirty"],
    "cleaning_in_progress": ["cleaning_completed", "maintenance_requested"],
    "cleaning_completed": ["inspected", "cleaning_in_progress", "maintenance_requested"],
    "inspected": ["vacant_clean", "occupied_clean", "maintenance_requested"],
    "out_of_service": ["inspected", "cleaning_in_progress"],
    "out_of_order": ["inspected", "maintenance_requested"],
    "maintenance_requested": ["out_of_service", "out_of_order", "inspected"],
}

ROOM_STATUS_COLORS: dict[str, str] = {
    "vacant_dirty": "#92400e",
    "vacant_clean": "#16a34a",
    "occupied_clean": "#006076",
    "occupied_dirty": "#d97706",
    "cleaning_in_progress": "#ca8a04",
    "cleaning_completed": "#059669",
    "inspected": "#4338ca",
    "out_of_service": "#6f797d",
    "out_of_order": "#ba1a1a",
    "maintenance_requested": "#ea580c",
}


def is_valid_transition(old_status: str, new_status: str) -> bool:
    """Check if a room status transition is valid per the central StateMachine."""
    from src.app.core.state_machine import room_sm
    return room_sm.can_transition(old_status, new_status)


def get_valid_next_statuses(current_status: str) -> list[str]:
    """Return valid next states for a given current status, from central StateMachine."""
    from src.app.core.state_machine import room_sm
    return room_sm.get_valid_next_states(current_status)


class RoomStatusLogCreate(BaseModel):
    prop_id: int
    room_type_id: str
    room_label: str
    status: str = "vacant_clean"
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
    room_id: str  # hotel_room_id (e.g. HR-1-101)
    task_type: str = "cleaning"  # cleaning, deep_clean, turnover, inspection
    assigned_to: str = ""
    priority: str = "normal"  # low, normal, high, urgent
    note: str = ""
    scheduled_date: str = ""
    status: str = "pending"


class MaintenanceTaskCreate(BaseModel):
    prop_id: int
    room_id: str  # hotel_room_id (e.g. HR-1-101)
    task_type: str  # preventive, corrective, inspection
    title: str
    description: str = ""
    priority: str = "normal"
    scheduled_date: str = ""
    status: str = "scheduled"
    auto_block: bool = True  # RF-002: block room availability during maintenance
    estimated_cost: float | None = Field(default=None, ge=0)
    actual_cost: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    vendor_name: str | None = None
    vendor_id: str | None = None
    expense_invoice_id: str | None = None
    ledger_journal_id: str | None = None
    inventory_consumption_ids: list[str] = Field(default_factory=list)


class AdditionalChargeCreate(BaseModel):
    booking_id: str
    prop_id: int
    concept: str
    amount: float
    quantity: int = 1
    category: str = ""  # minibar, spa, restaurante, lavanderia, parking, mascotas, room_service, danos, late_checkout
    note: str = ""
    charge_date: str = ""  # ISO datetime string; if empty, server uses now_iso()


class AdditionalChargeUpdate(BaseModel):
    concept: str | None = None
    amount: float | None = None
    quantity: int | None = None
    note: str | None = None
    charge_date: str | None = None


class AdditionalChargeResponse(BaseModel):
    id: str = Field(alias="_id")
    booking_id: str
    prop_id: int
    concept: str
    amount: float
    quantity: int
    total: float
    category: str = ""
    note: str
    folio_id: str | None = None
    folio_number: str | None = None
    posting_status: str | None = None
    posting_error: str | None = None
    created_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
