"""Pydantic models for the Reviews module.

Fase #8 (canonical Pydantic v2 *Response convention, line with Fase #5/6/7).

RULES (canonical from Fase #5/6/7):
- Response classes use ``model_config = ConfigDict(extra=\"allow\", populate_by_name=True)``
  so Mongo docs with unknown fields round-trip without 500.
- Primary key ``id`` uses ``Field(validation_alias=AliasChoices(\"_id\",\"id\"),
  serialization_alias=\"id\")`` so that legacy code passing ``_id`` (raw ObjectId)
  AND code passing ``id`` (already-stringified) both validate to a plain ``str``.
- Foreign-key fields use a SINGLE alias matching the field name (NOT
  ``AliasChoices``) so they cannot collide with ``id``'s ``_id``.
- ``.model_rebuild()`` is called on every class because the module uses
  ``from __future__ import annotations`` and several compose other classes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Module Status (kept pre-Fase — no migration needed) ─────────────────


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


# ── Input DTOs (kept unchanged) ─────────────────────────────────────────


class ServiceRatings(BaseModel):
    """Per-category 1–5 ratings attached to a review."""

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


class ReviewModeration(BaseModel):
    status: str  # approved | rejected
    reason: str = ""


class ReviewStaffResponse(BaseModel):
    """Input DTO for ``PATCH /api/reviews/{id}/respond``."""

    response: str


class ReviewUpdate(BaseModel):
    """Input DTO for ``PUT /api/reviews/{id}`` (only while pending)."""

    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = None
    comment: str | None = None


class ReviewReportCreate(BaseModel):
    reason: str
    description: str = ""


# ── Pydantic *Response models (canonical, migrated) ─────────────────────


class ReviewResponse(BaseModel):
    """Guest review — booker_rating, sentiment, staff response threads.

    ``id`` accepts both ``_id`` (raw Mongo ObjectId) and ``id`` (pre-stringified)
    via ``AliasChoices``. FK fields use single alias (no collision risk).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    booking_id: str = ""
    prop_id: int = 0
    user_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="user_id",
        serialization_alias="user_id",
    )
    user_display_name: str = ""
    rating: int = 0
    title: str = ""
    comment: str = ""
    moderation_status: str = "pending"
    staff_response: str | None = None
    staff_response_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


class ReviewListResponse(BaseModel):
    """Envelope for ``GET /api/reviews`` (paginated list with RBAC filter).

    ``items`` is typed as ``list[ReviewResponse]`` to keep the response
    wire-shape pinned under Pydantic v2 — each row MUST go through
    ``ReviewResponse.model_validate(...)``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    items: list[ReviewResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class ReviewReportResponse(BaseModel):
    """A user-submitted report flagging a review for moderation."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    review_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="review_id",
        serialization_alias="review_id",
    )
    reported_by: str = ""
    reason: str = ""
    description: str = ""
    status: str = ""
    created_at: str = ""


# ── Explicit rebuilds — ``from __future__ import annotations`` requires
#    eager resolution before the first TypeAdapter binds. Force it.

ReviewResponse.model_rebuild()
ReviewListResponse.model_rebuild()
ReviewReportResponse.model_rebuild()
ModuleStatus.model_rebuild()
