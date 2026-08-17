"""Email notifications for subscription transitions (PLAN_SUSCRIPCION_Y_PAGOS.md §8).

Dispatch for the five owner emails of the subscription lifecycle:

- ``submit_payment`` → ``subscription_payment_received``
- ``verify_payment`` → ``subscription_payment_verified``
- ``reject_payment`` → ``subscription_payment_rejected`` (motivo, nunca genérico)
- ``mark_overdue``  → ``subscription_overdue``
- ``suspend``       → ``subscription_suspended``

Best-effort by design (same contract as ``send_email`` everywhere and as the
``property_approval/notifications.py`` dispatch): a failure logs and NEVER
breaks the subscription transition — the state change + audit already happened.
"""

from __future__ import annotations

import logging

from config.settings import get_settings
from src.app.email.service import send_email
from src.app.email.templates import (
    subscription_overdue,
    subscription_payment_received,
    subscription_payment_rejected,
    subscription_payment_verified,
    subscription_suspended,
)

logger = logging.getLogger(__name__)

SUBJECT_PAYMENT_RECEIVED = "Recibimos tu comprobante de pago — HotelData"
SUBJECT_PAYMENT_VERIFIED = "Tu pago fue conciliado — HotelData"
SUBJECT_PAYMENT_REJECTED = "Tu comprobante fue rechazado — HotelData"
SUBJECT_OVERDUE = "Tu factura de suscripción venció — HotelData"
SUBJECT_SUSPENDED = "Tu hotel fue suspendido por impago — HotelData"


def _base_url() -> str:
    # Siempre se invoca dentro del ``try`` de un ``notify_*`` (que loguea con
    # ``logger.exception``), así que no captura aquí: un fallo de settings se
    # reporta igual de best-effort sin romper la transición.
    return (get_settings().app_base_url or "https://hoteldata.app").rstrip("/")


def notify_payment_received(
    email: str,
    *,
    hotel_name: str,
    amount: float,
    reference: str = "",
) -> None:
    if not email:
        return
    try:
        html = subscription_payment_received(
            hotel_name=hotel_name,
            amount=amount,
            reference=reference,
            base_url=_base_url(),
        )
        send_email(email, SUBJECT_PAYMENT_RECEIVED, html)
    except Exception:
        logger.exception("Failed to send payment-received email to %s for %s", email, hotel_name)


def notify_payment_verified(
    email: str,
    *,
    hotel_name: str,
) -> None:
    if not email:
        return
    try:
        html = subscription_payment_verified(
            hotel_name=hotel_name,
            base_url=_base_url(),
        )
        send_email(email, SUBJECT_PAYMENT_VERIFIED, html)
    except Exception:
        logger.exception("Failed to send payment-verified email to %s for %s", email, hotel_name)


def notify_payment_rejected(
    email: str,
    *,
    hotel_name: str,
    reason: str,
) -> None:
    if not email:
        return
    try:
        html = subscription_payment_rejected(
            hotel_name=hotel_name,
            reason=reason,
            base_url=_base_url(),
        )
        send_email(email, SUBJECT_PAYMENT_REJECTED, html)
    except Exception:
        logger.exception("Failed to send payment-rejected email to %s for %s", email, hotel_name)


def notify_overdue(
    email: str,
    *,
    hotel_name: str,
    amount: float,
    due_date=None,
) -> None:
    if not email:
        return
    try:
        html = subscription_overdue(
            hotel_name=hotel_name,
            amount=amount,
            due_date=due_date,
            base_url=_base_url(),
        )
        send_email(email, SUBJECT_OVERDUE, html)
    except Exception:
        logger.exception("Failed to send overdue email to %s for %s", email, hotel_name)


def notify_suspended(
    email: str,
    *,
    hotel_name: str,
    amount: float,
) -> None:
    if not email:
        return
    try:
        html = subscription_suspended(
            hotel_name=hotel_name,
            amount=amount,
            base_url=_base_url(),
        )
        send_email(email, SUBJECT_SUSPENDED, html)
    except Exception:
        logger.exception("Failed to send suspended email to %s for %s", email, hotel_name)
