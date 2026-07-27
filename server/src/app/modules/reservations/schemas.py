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

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr


# ── Module Status (kept pre-Fase — no migration needed) ─────────────────


class ModuleStatus(BaseModel):
    """Module status echo — used by ``GET /modules/reservations/status``."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    module: str
    status: str
    description: str


# ── Pydantic *Response models (canonical, migrated) ─────────────────────


class AssignedRoom(BaseModel):
    """One row in ``BookingResponse.assigned_rooms``.

    Locked wire-shape — service layer formats ``hotel_room_id`` as a string FK
    reference. ``room_label`` is the human-readable identifier surfaced to the
    UI; ``assigned_at`` is an ISO-8601 timestamp. Tightening the previous
    ``list[Any]`` field closes a hidden wire-shape contract (extra="allow"
    was silently swallowing the shape).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    hotel_room_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="hotel_room_id",
        serialization_alias="hotel_room_id",
    )
    room_label: str = ""
    assigned_at: str | None = None


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
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    booking_id: str = ""
    user_id: str = ""
    prop_id: int = 0
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
    special_requests: str | None = None
    assigned_rooms: list[AssignedRoom] = Field(default_factory=list)
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
AssignedRoom.model_rebuild()
BookingResponse.model_rebuild()
BookingListResponse.model_rebuild()
