from __future__ import annotations

import re
from typing import Any

from ._helpers import ReservationInput, _clean_text, _safe_int


PHONE_RE = re.compile(r"^[\d\s\-\+\(\)\.]+$")


def _valid_phone(value: str) -> bool:
    if not value:
        return True
    return bool(PHONE_RE.match(value))


def validate_reservation_input(payload: ReservationInput) -> list[str]:
    errors: list[str] = []
    if payload.prop_id <= 0:
        errors.append("prop_id must be a positive integer")
    if not payload.guest_name:
        errors.append("guest_name is required")
    if not payload.guest_email or "@" not in payload.guest_email:
        errors.append("guest_email must be valid")
    if not payload.check_in_date:
        errors.append("check_in_date is required")
    if not payload.check_out_date:
        errors.append("check_out_date is required")
    if payload.adults <= 0:
        errors.append("adults must be greater than zero")
    if payload.children < 0:
        errors.append("children cannot be negative")
    if payload.rooms <= 0:
        errors.append("rooms must be greater than zero")
    if payload.check_in_date and payload.check_out_date and payload.check_out_date < payload.check_in_date:
        errors.append("check_out_date must be greater than or equal to check_in_date")
    if not _valid_phone(payload.guest_phone):
        errors.append("guest_phone contains invalid characters")
    return errors


def build_reservation_input(form_data: dict[str, Any], *, source: str, is_test: bool = False) -> ReservationInput:
    return ReservationInput(
        prop_id=_safe_int(form_data.get("prop_id")),
        guest_name=_clean_text(form_data.get("guest_name")),
        guest_email=_clean_text(form_data.get("guest_email")).lower(),
        guest_phone=_clean_text(form_data.get("guest_phone")),
        room_type_id=_clean_text(form_data.get("room_type_id")),
        check_in_date=_clean_text(form_data.get("check_in_date")),
        check_out_date=_clean_text(form_data.get("check_out_date")),
        adults=_safe_int(form_data.get("adults"), 1),
        children=_safe_int(form_data.get("children"), 0),
        rooms=_safe_int(form_data.get("rooms"), 1),
        comment=_clean_text(form_data.get("comment")),
        source=source,
        user_id=_clean_text(form_data.get("user_id")) or None,
        created_by=_clean_text(form_data.get("created_by")) or None,
        is_test=is_test,
    )
