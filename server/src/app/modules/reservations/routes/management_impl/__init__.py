"""Management routes implementation package."""

from __future__ import annotations

from ._checkin import extract_ip_address
from ._checkout import extract_ip_address as extract_checkout_ip_address
from ._pos import apply_pos_charge
from ._users import search_users
from ._rooms import get_available_rooms, assign_rooms_to_booking

__all__ = [
    "extract_ip_address",
    "extract_checkout_ip_address",
    "apply_pos_charge",
    "search_users",
    "get_available_rooms",
    "assign_rooms_to_booking",
]
