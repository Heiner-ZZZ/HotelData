"""Management routes implementation package."""

from __future__ import annotations

from ._checkin import extract_ip_address
from ._checkout import extract_ip_address as extract_checkout_ip_address
from ._pos import apply_pos_charge
from ._rooms import assign_rooms_to_booking, get_available_rooms
from ._users import search_users

__all__ = [
    "apply_pos_charge",
    "assign_rooms_to_booking",
    "extract_checkout_ip_address",
    "extract_ip_address",
    "get_available_rooms",
    "search_users",
]
