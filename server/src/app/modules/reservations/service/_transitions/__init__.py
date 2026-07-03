"""Status transitions package — split into focused submodules."""

from __future__ import annotations

from src.app.modules.reservations.service._transitions._inventory import (
    _auto_assign_rooms,
    _deduct_inventory,
    _restore_inventory,
)
from src.app.modules.reservations.service._transitions._core import (
    _transition_status,
    confirm_booking,
    reject_booking,
)

__all__ = [
    "confirm_booking",
    "reject_booking",
]
