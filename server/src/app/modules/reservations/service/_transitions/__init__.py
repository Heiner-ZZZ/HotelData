"""Status transitions package — split into focused submodules."""

from __future__ import annotations

from src.app.modules.reservations.service._transitions._core import (
    confirm_booking,
    reject_booking,
)
from src.app.modules.reservations.service._transitions._inventory import (
    _deduct_inventory,
    _restore_inventory,
)

__all__ = [
    "_deduct_inventory",
    "_restore_inventory",
    "confirm_booking",
    "reject_booking",
]
