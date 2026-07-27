"""Pydantic models for the In-Stay (Mi Estancia) module.

Fase #7 — Pydantic v2 *Response convention (consistent with Fase #5/6 hr/ +
billing/ + expenses/).

RULES (canonical from Fase #5/6):
- Response classes use ``model_config = ConfigDict(extra="allow", populate_by_name=True)``
  so Mongo docs with unknown fields round-trip without 500.
- Primary key ``id`` uses ``Field(validation_alias=AliasChoices("_id","id"),
  serialization_alias="id")`` so that legacy code passing ``_id`` (raw ObjectId)
  AND code passing ``id`` (already-stringified) both validate to a plain ``str``.
- Foreign-key fields use a SINGLE alias matching the field name (NOT
  ``AliasChoices``) so they cannot collide with ``_id`` from the primary key.
- ``.model_rebuild()`` is called on every class because the module uses
  ``from __future__ import annotations`` and several compose other classes.
- Iterable helpers (``status_label``, ``type_label``) stay in ``_helpers.py`` —
  they are pure-Python concerns, not Pydantic validation. Endpoints pass the
  labeled dicts in via ``model_validate``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Service Requests — enum helpers (kept outside Pydantic) ─────────


SERVICE_REQUEST_TYPES = {
    "housekeeping": "Limpieza de habitación",
    "towels": "Toallas adicionales",
    "amenities": "Amenities (jabón, shampoo, etc.)",
    "maintenance": "Mantenimiento (avería en habitación)",
    "room_service": "Servicio a la habitación",
    "minibar": "Minibar",
    "laundry": "Lavandería / Tintorería",
    "wake_up_call": "Llamada de despertar",
    "late_checkout": "Late check-out",
    "extra_bed": "Cama adicional",
    "spa": "Spa & Bienestar",
    "restaurant": "Reserva en restaurante",
    "extend_stay": "Extender estancia",
    "early_checkout": "Salida anticipada",
    "other": "Otro",
}

SERVICE_REQUEST_STATUSES = {
    "pending": "Pendiente",
    "in_progress": "En proceso",
    "completed": "Completado",
    "cancelled": "Cancelado",
}


# ── Input DTOs (kept as-is — no migration required) ─────────────────


class StaySessionCreate(BaseModel):
    """Input DTO for staff creating a new stay session."""

    booking_id: str
    prop_id: int
    room_label: str
    guest_name: str
    check_in: str
    check_out: str
    expires_at: datetime | None = None


class ServiceRequestCreate(BaseModel):
    """Input DTO for staff creating a service request on behalf of a guest."""

    booking_id: str
    prop_id: int
    room_label: str
    request_type: str = "other"
    description: str = ""


class ServiceRequestUpdate(BaseModel):
    """Input DTO for staff updating the status of a service request."""

    status: str = "in_progress"
    staff_response: str = ""
    new_check_out_date: str = ""  # only used for extend_stay mid-stay op


class ChatMessageCreate(BaseModel):
    """Input DTO for chat messages (rarely used; legacy path is loose dict)."""

    booking_id: str
    prop_id: int
    room_label: str
    sender: str = "guest"  # guest | staff
    staff_name: str = ""
    message: str


# ── Compendium Info (already typed; just inherit canonical config) ──


class CompendiumInfo(BaseModel):
    """Hotel compendium exposed on the guest portal — wifi, hours, amenities."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    hotel_name: str = ""
    hotel_address: str = ""
    hotel_phone: str = ""
    wifi_ssid: str = ""
    wifi_password: str = ""
    check_in_time: str = "15:00"
    check_out_time: str = "12:00"
    breakfast_hours: str = ""
    restaurant_hours: str = ""
    gym_hours: str = ""
    pool_hours: str = ""
    parking_info: str = ""
    emergency_contact: str = ""
    policies: list[dict[str, Any]] = []
    amenities: list[dict[str, Any]] = []


# ── Pydantic *Response models (canonical, migrated) ────────────────


class StaySessionResponse(BaseModel):
    """Stay session — guest portal token.

    Note: no ``_id`` field — the canonical identity is ``token`` (random
    URL-safe string), not a Mongo ObjectId. Still inherits ``model_config``
    so the helper-produced dict round-trips cleanly.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    token: str
    booking_id: str
    prop_id: int
    room_label: str
    guest_name: str
    check_in: str
    check_out: str
    created_at: str
    expires_at: str | None = None
    active: bool = True


class StaySessionListResponse(BaseModel):
    """Paginated envelope for listing stay sessions."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    items: list[StaySessionResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class ServiceRequestResponse(BaseModel):
    """Service request — guest-initiated or staff-created.

    ``id`` accepts both ``_id`` (raw Mongo ObjectId) and ``id`` (pre-stringified)
    via ``AliasChoices``. FK fields use single alias (no collision risk).

    Note: ``mid_stay`` is intentionally on ``ServiceRequestUpdateResponse``
    only — that's the endpoint that embeds mid-stay operation results.
    The list endpoints never populate it.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    booking_id: str = ""
    prop_id: int = 0
    hotel_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="hotel_id",
        serialization_alias="hotel_id",
    )
    room_label: str = ""
    hotel_room_id: ObjectIdStr | None = Field(
        default=None,
        validation_alias="hotel_room_id",
        serialization_alias="hotel_room_id",
    )
    request_type: str = "other"
    request_type_label: str = ""
    description: str = ""
    status: str = "pending"
    status_label: str = "Pendiente"
    staff_response: str = ""
    staff_name: str = ""
    created_by: str = ""
    created_at: str = ""
    resolved_at: str | None = None
    staff_responded_at: str | None = None


class ServiceRequestListResponse(BaseModel):
    """Paginated envelope for listing service requests."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    items: list[ServiceRequestResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class ServiceRequestUpdateResponse(BaseModel):
    """Response for PUT /requests/{request_id} — may embed mid-stay result."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: bool = True
    request_id: str | None = None
    message: str = "Solicitud actualizada."
    mid_stay: dict[str, Any] | None = None


class CreateRequestResponse(BaseModel):
    """Response for POST /requests — created request id + DND flag."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: bool = True
    request_id: str
    message: str = "Solicitud creada."
    dnd_was_active: bool | None = None


class ChatMessageResponse(BaseModel):
    """Chat message — guest or staff — embedded in ``stay_messages``."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    booking_id: str = ""
    prop_id: int = 0
    room_label: str = ""
    sender: str = "guest"  # guest | staff | system
    staff_name: str = ""
    message: str = ""
    created_at: str = ""
    read: bool = False


class ChatMessageListResponse(BaseModel):
    """Enveloped list of chat messages."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    messages: list[ChatMessageResponse] = []


class ConversationResponse(BaseModel):
    """One row of the staff conversations inbox (per room_label group)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    room_label: str = ""
    booking_id: str = ""
    prop_id: int = 0
    last_message: str = ""
    last_sender: str = ""
    last_time: str = ""
    message_count: int = 0
    unread: int = 0
    guest_name: str = ""
    dnd: bool = False


class ConversationListResponse(BaseModel):
    """Enveloped list of conversations (grouped by room_label)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    conversations: list[ConversationResponse] = []


class FolioPostingItemResponse(BaseModel):
    """One line item from ``guest_folios.postings`` — typed for the portal."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    concept: str = ""
    category: str = ""
    amount: float = 0.0
    type: str = ""  # charge | payment | adjustment
    posted_at: str = ""


class ChargeItemResponse(BaseModel):
    """One line item from ``additional_charges`` — typed for the portal."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    concept: str = ""
    amount: float = 0.0
    quantity: float = 1.0
    total: float = 0.0
    category: str = ""
    note: str = ""
    created_at: str = ""


class PortalDataResponse(BaseModel):
    """Composite response for GET /portal — compendium + folio + charges.

    Wire-shape is enforced through strongly-typed inner classes
    (``StaySessionResponse``, ``CompendiumInfo``, ``ChargeItemResponse``,
    ``FolioPostingItemResponse``) so the FE can render nested grids with
    confidence.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    session: StaySessionResponse = Field(
        default_factory=lambda: StaySessionResponse.model_validate({}),
    )
    compendium: CompendiumInfo = Field(
        default_factory=lambda: CompendiumInfo.model_validate({}),
    )
    charges: list[ChargeItemResponse] = []
    folio_balance: float = 0.0
    folio_postings: list[FolioPostingItemResponse] = []
    nights_remaining: int = 0
    dnd_active: bool = False
    unread_messages: int = 0
    pending_requests: int = 0


class LostItemResponse(BaseModel):
    """Lost & found item — guest-facing."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: ObjectIdStr = Field(
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    description: str = ""
    status: str = "found"
    location_found: str = ""
    reported_by: str = ""
    returned_to: str = ""
    created_at: str = ""


class LostItemListResponse(BaseModel):
    """Enveloped list of lost & found items."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    items: list[LostItemResponse] = []


# ── Generic + dedicated Action Responses ────────────────────────────


class ActionResponse(BaseModel):
    """Generic OK response for actions (close/cancel/deactivate/etc.).

    Wire-shape: ``{"ok": true, "message": "..."}``. Frontend reads neither
    the field order nor any extra fields; ``extra=allow`` lets endpoints
    add ad-hoc fields without breaking.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: bool = True
    message: str = ""


class CleanupSessionActionResponse(BaseModel):
    """POST /sessions/cleanup-expired — batch deactivation summary."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: bool = True
    deactivated: int = 0
    total: int = 0
    prop_id: int | None = None
    message: str = ""


class ToggleDndResponse(BaseModel):
    """POST /dnd/toggle — echo back new DND state."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: bool = True
    dnd_active: bool = False
    message: str = ""


class ModuleStatusResponse(BaseModel):
    """Module status mimicked from hr/ for parity — minimal info."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    ok: bool = True
    module: str = "instay"


# ── Explicit rebuilds — ``from __future__ import annotations`` means every
#    class with a custom-class reference below needs ``model_rebuild()`` so
#    Pydantic can resolve forward refs (ListResponse→Item, PortalData→session).
#    Leaf classes with primitive-only fields work without rebuild, but we
#    call it on every class for uniformity with Fase #5/6.

PortalDataResponse.model_rebuild()
StaySessionResponse.model_rebuild()
StaySessionListResponse.model_rebuild()
ServiceRequestResponse.model_rebuild()
ServiceRequestListResponse.model_rebuild()
ServiceRequestUpdateResponse.model_rebuild()
CreateRequestResponse.model_rebuild()
ChatMessageResponse.model_rebuild()
ChatMessageListResponse.model_rebuild()
ConversationResponse.model_rebuild()
ConversationListResponse.model_rebuild()
FolioPostingItemResponse.model_rebuild()
ChargeItemResponse.model_rebuild()
LostItemResponse.model_rebuild()
LostItemListResponse.model_rebuild()
ActionResponse.model_rebuild()
CleanupSessionActionResponse.model_rebuild()
ToggleDndResponse.model_rebuild()
ModuleStatusResponse.model_rebuild()
CompendiumInfo.model_rebuild()
