from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class LostItemCreate(BaseModel):
    prop_id: int
    booking_id: str = ""
    guest_name: str = ""
    guest_contact: str = ""
    item_name: str
    description: str = ""
    found_location: str = ""
    found_by: str = ""
    status: str = "pending"  # pending, claimed, disposed, returned
    notes: str = ""


class LostItemUpdate(BaseModel):
    item_name: str | None = None
    description: str | None = None
    found_location: str | None = None
    found_by: str | None = None
    status: str | None = None
    notes: str | None = None
    guest_name: str | None = None
    guest_contact: str | None = None
    returned_to: str | None = None
    returned_at: str | None = None


class LostItemResponse(BaseModel):
    id: str = Field(alias="_id")
    prop_id: int
    booking_id: str
    guest_name: str
    guest_contact: str
    item_name: str
    description: str
    found_location: str
    found_by: str
    status: str
    notes: str
    returned_to: str
    returned_at: str | None = None
    created_at: str
    updated_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
