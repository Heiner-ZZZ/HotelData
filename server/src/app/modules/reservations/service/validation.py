from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bson import ObjectId

from ._helpers import ReservationInput, _clean_text, _safe_int


PHONE_RE = re.compile(r"^[\d\s\-\+\(\)\.]+$")
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _valid_phone(value: str) -> bool:
    if not value:
        return True
    return bool(PHONE_RE.match(value))


def validate_booking_form_requirements(payload: ReservationInput) -> list[str]:
    """Validate requirements specific to the guest booking form.

    The reservation service still accepts legacy/internal bookings that may
    omit contact metadata. The public booking form, however, must send a
    complete guest identity and an explicit overnight schedule.
    """
    errors: list[str] = []
    if not payload.guest_phone:
        errors.append("guest_phone is required")
    if payload.guest_phone and not _valid_phone(payload.guest_phone):
        errors.append("guest_phone contains invalid characters")
    if not payload.cedula:
        errors.append("cedula is required")
    if not payload.check_in_time:
        errors.append("check_in_time is required")
    elif not TIME_RE.fullmatch(payload.check_in_time):
        errors.append("check_in_time must use HH:MM format")
    if not payload.check_out_time:
        errors.append("check_out_time is required")
    elif not TIME_RE.fullmatch(payload.check_out_time):
        errors.append("check_out_time must use HH:MM format")
    if payload.estimated_arrival_time and not TIME_RE.fullmatch(payload.estimated_arrival_time):
        errors.append("estimated_arrival_time must use HH:MM format")
    if payload.check_in_date and payload.check_out_date and payload.check_out_date <= payload.check_in_date:
        errors.append("check_out_date must be after check_in_date for an overnight booking")
    return errors


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


def validate_date_format(check_in_date: str, check_out_date: str) -> list[str]:
    """Validate that check_in_date and check_out_date are valid YYYY-MM-DD strings.

    Returns a list of error messages (empty if valid).
    """
    errors: list[str] = []
    try:
        cin = datetime.strptime(check_in_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        errors.append(f"Invalid check_in_date format: '{check_in_date}' (expected YYYY-MM-DD)")
        cin = None

    try:
        cout = datetime.strptime(check_out_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        errors.append(f"Invalid check_out_date format: '{check_out_date}' (expected YYYY-MM-DD)")
        cout = None

    if cin and cout:
        if cout < cin:
            errors.append("check_out_date must be greater than or equal to check_in_date")

    return errors


def _validate_policy_times(prop_id: int, check_in_time: str, check_out_time: str) -> list[str]:
    """Validate check-in/out times against hotel policies."""
    errors: list[str] = []
    if not check_in_time and not check_out_time:
        return errors  # No times provided, skip
    from src.database.connection import get_database
    db = get_database()
    policy = db.hotel_policies.find_one(
        {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "season_id": {"$in": ["", None]}},
        {"_id": 0, "check_in_time": 1, "check_out_time": 1},
    )
    if not policy:
        return errors
    policy_ci = policy.get("check_in_time", "")
    policy_co = policy.get("check_out_time", "")
    if check_in_time and policy_ci:
        if check_in_time < policy_ci:
            errors.append(f"Check-in antes de lo permitido. El check-in es desde las {policy_ci}")
    if check_out_time and policy_co:
        if check_out_time > policy_co:
            errors.append(f"Check-out después de lo permitido. El check-out es hasta las {policy_co}")
    return errors


def _normalize_user_id(value: Any) -> str | ObjectId | None:
    """Canonicalize ``user_id`` to a BSON ObjectId (FK to ``users._id``).

    - ``None`` / empty → ``None`` (guest/anonymous booking)
    - ``ObjectId`` → kept as-is (canonical write path)
    - 24-hex string → wrapped in ``ObjectId`` (legacy callers, partner API,
      client-sent hex)
    - anything else → passed through untouched (never silently dropped)
    """
    if value is None or value == "":
        return None
    if isinstance(value, ObjectId):
        return value
    text = str(value).strip()
    # Canonical hex check (same as ``queries.py`` client-filter hardening).
    if ObjectId.is_valid(text):
        return ObjectId(text)
    return text


def build_reservation_input(form_data: dict[str, Any], *, source: str, is_test: bool = False) -> ReservationInput:
    return ReservationInput(
        prop_id=_safe_int(form_data.get("prop_id")),
        guest_name=_clean_text(form_data.get("guest_name")),
        guest_email=_clean_text(form_data.get("guest_email")).lower(),
        guest_phone=_clean_text(form_data.get("guest_phone")),
        cedula=_clean_text(form_data.get("cedula")),
        room_type_id=_clean_text(form_data.get("room_type_id")),
        hotel_room_id=_clean_text(form_data.get("hotel_room_id")),
        rate_plan_id=_clean_text(form_data.get("rate_plan_id")),
        check_in_date=_clean_text(form_data.get("check_in_date")),
        check_out_date=_clean_text(form_data.get("check_out_date")),
        check_in_time=_clean_text(form_data.get("check_in_time")),
        check_out_time=_clean_text(form_data.get("check_out_time")),
        estimated_arrival_time=_clean_text(form_data.get("estimated_arrival_time")),
        adults=_safe_int(form_data.get("adults"), 1),
        children=_safe_int(form_data.get("children"), 0),
        rooms=_safe_int(form_data.get("rooms"), 1),
        comment=_clean_text(form_data.get("comment")),
        coupon_code=_clean_text(form_data.get("coupon_code") or form_data.get("promo_code")),
        contract_code=_clean_text(form_data.get("contract_code")),
        selected_amenities=form_data.get("selected_amenities", []),
        special_requests=form_data.get("special_requests", []),
        season_id=_clean_text(form_data.get("season_id")),
        source=source,
        user_id=_normalize_user_id(form_data.get("user_id")),
        created_by=_clean_text(form_data.get("created_by")) or None,
        is_test=is_test,
    )
