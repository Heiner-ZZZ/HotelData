"""Reservation notifications package — split into focused submodules."""

from __future__ import annotations

from .guest import notify_guest_invoice, notify_guest_status_change
from .staff import notify_staff_check_event, notify_staff_new_booking

__all__ = [
    "notify_guest_invoice",
    "notify_guest_status_change",
    "notify_staff_check_event",
    "notify_staff_new_booking",
]
