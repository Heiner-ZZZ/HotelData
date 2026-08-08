"""Email notifications for hotel-registration transitions (UX-2).

Dispatch for the three owner emails defined in
`docs/EXPERIENCIA_DUENO_PENDIENTE.md` §4: approved (with assigned plan),
rejected (with the admin's reason — never generic) and changes-requested
(with the admin's feedback).

Best-effort by design (same contract as `send_email` everywhere in the
project): a failure logs and NEVER breaks the approval transition — the
state change + audit already happened.
"""

from __future__ import annotations

import logging

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.email.templates import (
    registration_approved,
    registration_changes_requested,
    registration_rejected,
)

logger = logging.getLogger(__name__)

SUBJECT_APPROVED = "Tu alojamiento fue aprobado — HotelData"
SUBJECT_REJECTED = "Tu registro de alojamiento no fue aprobado — HotelData"
SUBJECT_CHANGES = "Revisa tu registro de alojamiento — HotelData"


def notify_registration_approved(
    email: str,
    *,
    hotel_name: str,
    plan_label: str,
    monthly_usd: float,
) -> None:
    try:
        base_url = (get_settings().app_base_url or "https://hoteldata.app").rstrip("/")
        html = registration_approved(
            hotel_name=hotel_name,
            plan_label=plan_label,
            monthly_usd=monthly_usd,
            base_url=base_url,
        )
        send_email(email, SUBJECT_APPROVED, html)
    except Exception:
        logger.exception("Failed to send approval email to %s for %s", email, hotel_name)


def notify_registration_rejected(email: str, *, hotel_name: str, reason: str) -> None:
    try:
        base_url = (get_settings().app_base_url or "https://hoteldata.app").rstrip("/")
        html = registration_rejected(
            hotel_name=hotel_name,
            reason=reason,
            base_url=base_url,
        )
        send_email(email, SUBJECT_REJECTED, html)
    except Exception:
        logger.exception("Failed to send rejection email to %s for %s", email, hotel_name)


def notify_registration_changes_requested(
    email: str,
    *,
    hotel_name: str,
    feedback: str,
) -> None:
    try:
        base_url = (get_settings().app_base_url or "https://hoteldata.app").rstrip("/")
        html = registration_changes_requested(
            hotel_name=hotel_name,
            feedback=feedback,
            base_url=base_url,
        )
        send_email(email, SUBJECT_CHANGES, html)
    except Exception:
        logger.exception("Failed to send changes-requested email to %s for %s", email, hotel_name)
