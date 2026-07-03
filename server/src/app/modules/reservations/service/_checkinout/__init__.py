"""Check-in/out package — split into focused submodules."""

from __future__ import annotations

from src.app.modules.reservations.service._checkinout._checkin import (
    complete_check_in,
    update_check_in_datetime,
)
from src.app.modules.reservations.service._checkinout._checkout import complete_check_out
from src.app.modules.reservations.service._checkinout._helpers import (
    _generate_folio,
    _notify_guest_check_in,
    _notify_guest_check_out,
    _notify_staff_check_in,
    _notify_staff_check_out,
)

__all__ = [
    "complete_check_in",
    "complete_check_out",
    "update_check_in_datetime",
]
