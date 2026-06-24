from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


ALLOWED_STATUSES = {"pending", "confirmed", "cancelled", "rejected"}
CHECKIN_COMPLETED_STATUSES = {"checked_in", "checked_out"}
CHECKOUT_COMPLETED_STATUSES = {"checked_out"}


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
    guest_phone: str = ""
    room_type_id: str = ""
    coupon_code: str = ""
    special_requests: list[str] = None
    source: str = "web_request"
    user_id: str | None = None
    created_by: str | None = None
    is_test: bool = False

    def __post_init__(self):
        if self.special_requests is None:
            self.special_requests = []


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
