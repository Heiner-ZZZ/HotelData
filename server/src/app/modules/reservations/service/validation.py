from __future__ import annotations

import re
from datetime import date
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
        errors.append("El teléfono del huésped es obligatorio. Ingresalo para continuar.")
    if payload.guest_phone and not _valid_phone(payload.guest_phone):
        errors.append("El teléfono del huésped contiene caracteres inválidos. Usá solo números, espacios, guiones o paréntesis.")
    if not payload.cedula:
        errors.append("La cédula o documento del huésped es obligatorio. Ingresalo para continuar.")
    if not payload.check_in_time:
        errors.append("La hora de check-in es obligatoria. Elegí una hora de ingreso.")
    elif not TIME_RE.fullmatch(payload.check_in_time):
        errors.append("La hora de check-in debe usar formato HH:MM (ej. 15:00).")
    if not payload.check_out_time:
        errors.append("La hora de check-out es obligatoria. Elegí una hora de salida.")
    elif not TIME_RE.fullmatch(payload.check_out_time):
        errors.append("La hora de check-out debe usar formato HH:MM (ej. 12:00).")
    if payload.estimated_arrival_time and not TIME_RE.fullmatch(payload.estimated_arrival_time):
        errors.append("La hora estimada de llegada debe usar formato HH:MM (ej. 20:00).")
    if payload.check_in_date and payload.check_out_date and payload.check_out_date <= payload.check_in_date:
        errors.append("La fecha de check-out debe ser posterior al check-in. Ajustá las fechas para una estancia de al menos una noche.")
    return errors


def validate_reservation_input(payload: ReservationInput) -> list[str]:
    errors: list[str] = []
    if payload.prop_id <= 0:
        errors.append("El hotel seleccionado no es válido. Elegí un hotel de la lista.")
    if not payload.guest_name:
        errors.append("El nombre del huésped es obligatorio. Ingresalo para continuar.")
    if not payload.guest_email or "@" not in payload.guest_email:
        errors.append("El correo del huésped no es válido. Verificá el formato (ej. nombre@dominio.com).")
    if not payload.check_in_date:
        errors.append("La fecha de check-in es obligatoria. Elegí el día de ingreso.")
    if not payload.check_out_date:
        errors.append("La fecha de check-out es obligatoria. Elegí el día de salida.")
    if payload.adults <= 0:
        errors.append("Debe haber al menos un adulto. Indicá la cantidad de adultos.")
    if payload.children < 0:
        errors.append("La cantidad de niños no puede ser negativa. Corregí el valor.")
    if payload.rooms <= 0:
        errors.append("Debe haber al menos una habitación. Indicá la cantidad de habitaciones.")
    if payload.check_in_date and payload.check_out_date and payload.check_out_date < payload.check_in_date:
        errors.append("La fecha de check-out debe ser posterior o igual al check-in. Ajustá las fechas.")
    if not _valid_phone(payload.guest_phone):
        errors.append("El teléfono del huésped contiene caracteres inválidos. Usá solo números, espacios, guiones o paréntesis.")
    return errors


def validate_date_format(check_in_date: str, check_out_date: str) -> list[str]:
    """Validate that check_in_date and check_out_date are valid YYYY-MM-DD strings.

    Returns a list of error messages (empty if valid).
    """
    errors: list[str] = []
    try:
        cin = date.fromisoformat(check_in_date)
    except (ValueError, TypeError):
        errors.append(f"La fecha de check-in '{check_in_date}' no es válida. Usá el formato AAAA-MM-DD (ej. 2026-08-10).")
        cin = None

    try:
        cout = date.fromisoformat(check_out_date)
    except (ValueError, TypeError):
        errors.append(f"La fecha de check-out '{check_out_date}' no es válida. Usá el formato AAAA-MM-DD (ej. 2026-08-10).")
        cout = None

    if cin and cout and cout < cin:
        errors.append("La fecha de check-out debe ser posterior o igual al check-in. Ajustá las fechas.")

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
    if check_in_time and policy_ci and check_in_time < policy_ci:
        errors.append(f"Check-in antes de lo permitido. El check-in es desde las {policy_ci}")
    if check_out_time and policy_co and check_out_time > policy_co:
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
