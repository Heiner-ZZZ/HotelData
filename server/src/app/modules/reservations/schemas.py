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

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

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


class AssignedRoomSnapshot(BaseModel):
    """Snapshot of a hotel room assigned to a booking.

    Mirrors the dict shape produced by ``get_booking_detail`` (queries.py
    around line 374) which enriches each ``booking.assigned_rooms`` ID
    against the ``hotel_rooms`` collection. Optional fields tolerate
    pre-migration docs that stored only ``hotel_room_id``.

    Backward compat for legacy ``list[str]`` rows: a ``@model_validator``
    coerces bare strings into ``{hotel_room_id: <str>}``, so the wire
    shape is consistent end-to-end and the frontend never has to handle
    a mixed ``list[str | dict]``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    hotel_room_id: str
    room_number: str | None = None
    room_label: str | None = None
    floor: str | None = None
    room_status: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_string(cls, data: Any) -> Any:
        """Pre-migration bookings stored ``assigned_rooms: list[str]``.

        Pydantic's per-item validator runs BEFORE the strict field
        check, so a bare string like ``"HR-1-119"`` is converted into
        the dict shape required by the field definitions below. There
        is no ObjectId / richer-id roundtrip from this class — the
        canonical identifier is the wire-level ``hotel_room_id`` string.
        """
        if isinstance(data, str):
            return {"hotel_room_id": data}
        return data


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
    # Late check-out outcome persisted by the completion flow. These fields are
    # read-only booking facts for reservation history; the UI must not infer a
    # late departure from the current clock or policy.
    check_out_mode: str | None = None
    late_checkout_minutes: int = 0
    late_checkout_policy_time: str | None = None
    check_out_date_actual: str | None = None
    check_out_time_actual: str | None = None
    # Ventana de reapertura de no-show (server-authoritative, misma regla que
    # el calendario de Recepción): 'open' | 'too_late' | 'stay_ended' | None.
    # Solo las reservas no-show llevan ventana; el resto serializa ``None``.
    reopen_window: str | None = None
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
    assigned_rooms: list[AssignedRoomSnapshot] | None = Field(
        default=None,
        description=(
            "Room snapshots assigned to this booking. Each item carries "
            "``hotel_room_id`` plus enriched metadata (room_number/label/floor/status) "
            "resolved from ``hotel_rooms`` at query time. Tolerates ``None`` "
            "and legacy ``list[str]`` rows (auto-coerced via the @model_validator)."
        ),
    )
    # History is nested INSIDE BookingResponse because ``get_booking_detail``
    # surfaces it under the same response (queries.py:401).
    history: list[BookingHistoryResponse] = Field(default_factory=list)


class ReservationCreatedResponse(BaseModel):
    """Compact response returned by POST /api/reservations.

    KEEP IN SYNC with ``ReservationCreateDto`` in the frontend. Creation
    returns a summary envelope, not a full Mongo booking document, so it must
    not reuse ``BookingResponse`` (whose canonical ``id`` is required).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    booking_id: str
    status: str
    total_price: float | None = None
    currency: str = "USD"
    total_nights: int = 0
    manual_reservation_id: str | None = None
    hotel_label: str = ""
    hotel_prop_id: int | None = None
    room_type_name: str | None = None
    check_in_date: str = ""
    check_out_date: str = ""
    rooms: int = 1
    adults: int = 1
    children: int = 0
    guest_name: str = ""
    guest_email: str = ""
    discount_percent: float | None = None
    original_total_price: float | None = None
    transaction_id: str | None = None
    payment_method: str | None = None
    card_last4: str | None = None
    payment_status: str | None = None
    cancellation_policy: str | None = None


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
AssignedRoomSnapshot.model_rebuild()
BookingResponse.model_rebuild()
ReservationCreatedResponse.model_rebuild()
BookingListResponse.model_rebuild()
