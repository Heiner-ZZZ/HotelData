"""Reservation lifecycle package — split into focused submodules."""

from __future__ import annotations

from .create import (
    _calculate_total_price,
    # Private helpers re-exported for the test suite (test_reservations.py
    # imports them from the package root). KEEP IN SYNC with .create.
    _check_availability,
    create_booking,
    modify_booking,
    validate_coupon_code,
)
from .guests import (
    get_check_in_status,
    get_room_guests,
    save_room_guests,
)

__all__ = [
    "_calculate_total_price",
    "_check_availability",
    "create_booking",
    "get_check_in_status",
    "get_room_guests",
    "modify_booking",
    "save_room_guests",
    "validate_coupon_code",
]
