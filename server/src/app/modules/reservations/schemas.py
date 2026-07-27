"""Pydantic models for the Reservations module.

Fase #10 — closes the Migration #3 wave (final FASE of the 111-sitio backlog).
Canonical Pydantic v2 *Response convention, line with Fases #5/6/7/8/9.

RULES (canonical from prior Fases):
- Response classes use ``model_config = ConfigDict(extra=\"allow\", populate_by_name=True)``
  so Mongo docs with unknown fields round-trip without 500.
- Primary key ``id`` uses ``Field(validation_alias=AliasChoices(\"_id\",\"id\"),
  serialization_alias=\"id\")`` — accepts both raw Mongo ``_id`` and pre-stringified
  ``id`` from legacy callers.
- Foreign-key fields use a SINGLE alias matching the field name (NOT
  ``AliasChoices``) so they cannot collide with ``id``'s ``_id``.
- ``.model_rebuild()`` called on every class because the module uses
  ``from __future__ import annotations`` and several compose other classes.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ListToCommaStr, ObjectIdStr


# ── Module Status (kept pre-Fase — no migration needed) ─────────────────


class ModuleStatus(BaseModel):
    """Module status echo — used by ``GET /modules/reservations/status``."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    module: str
    status: str
    description: str


# ── Pydantic *Response models (canonical, migrated) ─────────────────────


class BookingHistoryResponse(BaseModel):
    """One record of a booking's status history.

    Models the structure written by every booking-state transition
    (``confirm_booking``, ``reject_booking``, ``cancel_booking``,
    ``complete_check_in``, ``complete_check_out``, ``process_no_show``,
    early checkout, etc.). The ``booking_id`` is an FK reference to
    ``booking_orders`` (collection enumerated in
    ``service/collections.py::BOOKINGS_COLLECTION``).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    booking_id: str = ""
    status: str = ""
    changed_at: str | None = None
    reason: str | None = None
    changed_by: str | None = None
    is_test: bool | None = None


class BookingResponse(BaseModel):
    """Booking order — the canonical booking record from ``booking_orders``.

    Includes a nested ``history`` list of ``BookingHistoryResponse`` items
    surfaced by ``get_booking_detail`` (queries.py:401). The list is
    permissive in length — recent vs full history depends on the service
    layer's projection.

    ``assigned_rooms`` is a flat ``list[str]`` of room labels (e.g.
    ``['HR-1-119', 'HR-1-120']``), as emitted by the Mongo
    ``booking_orders`` collection. Once the service layer evolves to
    embed rich dicts (FK + label + assigned_at), this field should
    migrate to ``list[AssignedRoom]``. The previously-added
    ``AssignedRoom`` typed sub-model was orphaned and removed in the
    Mongo-shape-verification round (one-time diagnostic).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    booking_id: str = ""
    user_id: ObjectIdStr | None = Field(
        default=None,
        description=(
            "Owner / creator FK reference (auth user). Tolerates explicit "
            "`None` from pre-migration docs and bookings created via "
            "unauthenticated channels (OTA imports, walk-ins, PocketBase "
            "legacy rows). Same canonical pattern as `prop_id`."
        ),
    )
    prop_id: int | ObjectIdStr | None = Field(
        default=None,
        description=(
            "Property/hotel FK reference. May be a legacy integer or a "
            "post-migration ObjectId string. Will collapse to `ObjectIdStr` "
            "once the create flow + tests are migrated."
        ),
    )
    hotel_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="hotel_id",
        serialization_alias="hotel_id",
    )
    room_type_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="room_type_id",
        serialization_alias="room_type_id",
    )
    rate_plan_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="rate_plan_id",
        serialization_alias="rate_plan_id",
    )
    status: str = ""
    stay_status: str | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    total_nights: int | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    guest_phone: str | None = None
    rooms: int = 1
    total_price: float | None = None
    currency: str | None = None
    coupon_code: str | None = None
    booking_source: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    special_requests: ListToCommaStr | None = None
    assigned_rooms: list[str] | None = Field(
        default=None,
        description=(
            "Room labels assigned to this booking (e.g. ``['HR-1-119', 'HR-1-120']``). "
            "Tolerates explicit ``None`` from pre-FK-migration docs that stored "
            "the field as ``null``. FUTURE: migrate to ``list[AssignedRoom]`` "
            "once the service layer starts emitting the richer dict shape."
        ),
    )
    # History is nested INSIDE BookingResponse because ``get_booking_detail``
    # surfaces it under the same response (queries.py:401).
    history: list[BookingHistoryResponse] = Field(default_factory=list)


class BookingListResponse(BaseModel):
    """Paginated envelope for ``GET /api/reservations`` (list)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    items: list[BookingResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


# ── Explicit rebuilds — ``from __future__ import annotations`` requires
#    eager resolution before the first TypeAdapter binds. Force it.

ModuleStatus.model_rebuild()
BookingHistoryResponse.model_rebuild()
BookingResponse.model_rebuild()
BookingListResponse.model_rebuild()
