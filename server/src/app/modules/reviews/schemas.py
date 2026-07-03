from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class ServiceRatings(BaseModel):
    housekeeping: int | None = Field(default=None, ge=1, le=5)
    food_beverage: int | None = Field(default=None, ge=1, le=5)
    staff: int | None = Field(default=None, ge=1, le=5)


class ReviewCreate(BaseModel):
    booking_id: str
    prop_id: int
    rating: int = Field(ge=1, le=5)
    title: str = ""
    comment: str = ""
    service_ratings: ServiceRatings | None = None


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


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = None
    comment: str | None = None


class ReviewReportCreate(BaseModel):
    reason: str
    description: str = ""


class ReviewReportResponse(BaseModel):
    id: str = Field(alias="_id")
    review_id: str
    reported_by: str
    reason: str
    description: str
    status: str
    created_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
