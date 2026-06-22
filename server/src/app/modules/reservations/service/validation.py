from __future__ import annotations

from datetime import date
from typing import Any

from ._helpers import ReservationInput, _clean_text, _safe_int


def validate_reservation_input(payload: ReservationInput) -> list[str]:
    errors: list[str] = []
    if payload.prop_id <= 0:
        errors.append("prop_id must be a positive integer")
    if not payload.guest_name:
        errors.append("guest_name is required")
    if not payload.guest_email or "@" not in payload.guest_email:
        errors.append("guest_email must be valid")
    if payload.guest_phone and not _valid_phone(payload.guest_phone):
        errors.append("guest_phone format is invalid (use + or digits only)")
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
    if payload.check_in_date and payload.check_out_date:
        try:
            start = date.fromisoformat(payload.check_in_date)
            end = date.fromisoformat(payload.check_out_date)
            nights = (end - start).days
            if nights < 1:
                errors.append("check_out_date must be after check_in_date (at least 1 night)")
        except (ValueError, TypeError):
            errors.append("check_in_date and check_out_date must be valid ISO dates (YYYY-MM-DD)")
    return errors


def _valid_phone(phone: str) -> bool:
    """Basic phone validation: allows +, digits, spaces, dashes, and parentheses."""
    cleaned = phone.strip()
    if not cleaned:
        return True  # optional, empty is ok
    allowed = set("+0123456789 -()")
    return all(c in allowed for c in cleaned)


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
