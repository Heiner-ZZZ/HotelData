from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class ReviewCreate(BaseModel):
    booking_id: str
    prop_id: int
    rating: int = Field(ge=1, le=5)
    title: str = ""
    comment: str = ""


class ReviewResponse(BaseModel):
    id: str = Field(alias="_id")
    booking_id: str
    prop_id: int
    user_id: str
    user_display_name: str = ""
    rating: int
    title: str
    comment: str
    moderation_status: str
    staff_response: str | None = None
    staff_response_at: str | None = None
    created_at: str
    updated_at: str


class ReviewModeration(BaseModel):
    status: str  # approved | rejected
    reason: str = ""


class ReviewStaffResponse(BaseModel):
    response: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
