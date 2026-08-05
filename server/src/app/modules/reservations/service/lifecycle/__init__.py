"""Reservation lifecycle package — split into focused submodules."""

from __future__ import annotations

from .create import (
    create_booking,
    modify_booking,
    validate_coupon_code,
    # Private helpers re-exported for the test suite (test_reservations.py
    # imports them from the package root). KEEP IN SYNC with .create.
    _check_availability,
    _calculate_total_price,
)
from .guests import (
    get_room_guests,
    save_room_guests,
    get_check_in_status,
)

__all__ = [
    "create_booking",
    "modify_booking",
    "validate_coupon_code",
    "_check_availability",
    "_calculate_total_price",
    "get_room_guests",
    "save_room_guests",
    "get_check_in_status",
]
