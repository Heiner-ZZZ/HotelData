from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.app.core.state_machine import booking_sm


# ── Reservation (booking.status) lifecycle ──
# Derived from the central booking StateMachine so we never drift.
ALLOWED_STATUSES = set(booking_sm.states) - {"checked_in", "checked_out"}

# ── Stay (booking.stay_status) lifecycle ──
# Derived from the central stay StateMachine.
STAY_CHECKED_IN = "checked_in"
STAY_CHECKED_OUT = "checked_out"
STAY_NOSHOW = "no_show"
STAY_PENDING = "pending"

# Completed statuses — a stay is considered "completed" for check-in
# when it has reached checked_in or checked_out; for check-out only
# when it has reached checked_out.
CHECKIN_COMPLETED_STAY_STATUSES = {STAY_CHECKED_IN, STAY_CHECKED_OUT}
CHECKOUT_COMPLETED_STAY_STATUSES = {STAY_CHECKED_OUT}


@dataclass
class ReservationInput:
    prop_id: int
    guest_name: str
    guest_email: str
    check_in_date: str
    check_out_date: str
    adults: int
    children: int
    rooms: int
    comment: str
    check_in_time: str = ""
    check_out_time: str = ""
    # Optional HH:MM — hora estimada de llegada del huésped (late check-in).
    estimated_arrival_time: str = ""
    guest_phone: str = ""
    cedula: str = ""
    room_type_id: str = ""
    hotel_room_id: str = ""
    rate_plan_id: str = ""
    coupon_code: str = ""
    contract_code: str = ""
    selected_amenities: list[str] | None = None
    special_requests: list[str] | None = None
    season_id: str = ""
    source: str = "web_request"
    # FK to users._id. Canonical storage is a BSON ObjectId; the field also
    # accepts a 24-hex string from legacy callers (``build_reservation_input``
    # normalizes it) and None for guest/anonymous bookings.
    user_id: str | ObjectId | None = None
    created_by: str | None = None
    is_test: bool = False
    # Payment / transaction fields (Phase 1)
    transaction_id: str = ""
    payment_method: str = ""
    card_last4: str = ""
    payment_status: str = "pending"

    def __post_init__(self):
        if self.selected_amenities is None:
            self.selected_amenities = []
        if self.special_requests is None:
            self.special_requests = []
        if self.season_id is None:
            self.season_id = ""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def generate_prefixed_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(4)
    return f"{prefix}-{stamp}-{token}".upper()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _clean_text(value: Any) -> str:
    return str(value or "").strip()
