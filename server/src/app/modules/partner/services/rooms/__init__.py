"""Rooms sub-domain package — split into focused submodules.

Re-exports all public functions for backward compatibility with
services/__init__.py and routes.
"""

from __future__ import annotations

from .types import (
    _room_types_for_prop,
    create_room_type,
    delete_room_type,
    update_room_type,
)
from .inventory import (
    partner_hotel_inventory,
    save_inventory_entry,
    soft_delete_inventory_entry,
)
from .availability import (
    create_blackout_block,
    delete_blackout_block,
    list_property_blackouts,
)
from .queries import (
    partner_hotel_rooms,
)
from .features import (
    add_custom_feature,
    get_all_features,
    get_room_type_features,
    update_room_type_features,
)

__all__ = [
    "partner_hotel_rooms",
    "partner_hotel_inventory",
    "create_room_type",
    "update_room_type",
    "delete_room_type",
    "save_inventory_entry",
    "soft_delete_inventory_entry",
    "create_blackout_block",
    "delete_blackout_block",
    "list_property_blackouts",
    "add_custom_feature",
    "get_all_features",
    "get_room_type_features",
    "update_room_type_features",
]
