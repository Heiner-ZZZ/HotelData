"""Partner sub-services package.

Public API exposed by this package (re-exported here for convenience):

Bootstrap
    module_status, ensure_hotel_content_collections,
    ensure_hotel_profile_collections, ensure_inventory_collections,
    ensure_rate_collections

Properties
    list_partner_hotels, partner_hotel_detail, partner_hotel_performance,
    save_partner_hotel_profile

Content
    partner_hotel_content, partner_hotel_content_editor,
    partner_hotel_policies, partner_hotel_images,
    partner_hotel_profile, partner_hotel_edit_profile,
    save_partner_hotel_content, save_partner_hotel_amenities,
    save_partner_hotel_policies, add_partner_hotel_image,
    delete_partner_hotel_image

Rooms
    partner_hotel_rooms, partner_hotel_inventory,
    create_room_type, update_room_type, save_inventory_entry, create_blackout_block

Rates
    partner_hotel_rates, create_rate_plan, save_rate_calendar_entry

Dashboard
    management_property_options, management_reports_summary,
    properties_dashboard
"""
from __future__ import annotations

from src.app.modules.partner.services.bootstrap import (
    ensure_hotel_content_collections,
    ensure_hotel_profile_collections,
    ensure_inventory_collections,
    ensure_rate_collections,
    module_status,
)
from src.app.modules.partner.services.content import (  # type: ignore[assignment]
    add_partner_hotel_image,
    delete_partner_hotel_image,
    partner_hotel_content,
    partner_hotel_content_editor,
    partner_hotel_edit_profile,
    partner_hotel_images,
    partner_hotel_per_room_policies,
    partner_hotel_policies,
    partner_hotel_profile,
    save_partner_hotel_amenities,
    save_partner_hotel_content,
    save_partner_hotel_policies,
)
from src.app.modules.partner.services.dashboard import (  # type: ignore[assignment]
    management_property_options,
    management_reports_summary,
    properties_dashboard,
)
from src.app.modules.partner.services.history import list_hotel_changes, get_change_detail
from src.app.modules.partner.services.properties import (
    list_partner_hotels,
    partner_hotel_detail,
    partner_hotel_performance,
    save_partner_hotel_profile,
)  # type: ignore[assignment]
from src.app.modules.partner.services.rates import (
    create_rate_plan,
    partner_hotel_rates,
    save_rate_calendar_entry,
)
from src.app.modules.partner.services.rooms import (
    create_blackout_block,
    create_room_type,
    delete_blackout_block,
    delete_room_type,
    list_property_blackouts,
    partner_hotel_inventory,
    partner_hotel_rooms,
    save_inventory_entry,
    update_room_type,
)


__all__ = [
    "add_partner_hotel_image",
    "create_blackout_block",
    "delete_blackout_block",
    "list_property_blackouts",
    "get_change_detail",
    "list_hotel_changes",
    "create_rate_plan",
    "create_room_type",
    "delete_room_type",
    "update_room_type",
    "delete_partner_hotel_image",
    "ensure_hotel_content_collections",
    "ensure_hotel_profile_collections",
    "ensure_inventory_collections",
    "ensure_rate_collections",
    "list_partner_hotels",
    "management_property_options",
    "management_reports_summary",
    "module_status",
    "partner_hotel_content",
    "partner_hotel_content_editor",
    "partner_hotel_detail",
    "partner_hotel_edit_profile",
    "partner_hotel_images",
    "partner_hotel_inventory",
    "partner_hotel_performance",
    "partner_hotel_per_room_policies",
    "partner_hotel_policies",
    "partner_hotel_profile",
    "partner_hotel_rates",
    "partner_hotel_rooms",
    "properties_dashboard",
    "save_inventory_entry",
    "save_partner_hotel_amenities",
    "save_partner_hotel_content",
    "save_partner_hotel_policies",
    "save_partner_hotel_profile",
    "save_rate_calendar_entry",
]
