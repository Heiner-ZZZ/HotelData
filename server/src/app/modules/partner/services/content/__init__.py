from src.app.modules.partner.services.content.views import (
    partner_hotel_content,
    partner_hotel_content_editor,
    partner_hotel_images,
    partner_hotel_per_room_policies,
    partner_hotel_policies,
    partner_hotel_profile,
    partner_hotel_edit_profile,
)
from src.app.modules.partner.services.content.save import (
    save_partner_hotel_content,
    save_partner_hotel_amenities,
    save_partner_hotel_policies,
)
from src.app.modules.partner.services.content.images import (
    add_partner_hotel_image,
    delete_partner_hotel_image,
    reorder_partner_hotel_images,
)
from src.app.modules.partner.services.content.queries import content_page_for_prop

__all__ = [
    "add_partner_hotel_image",
    "content_page_for_prop",
    "delete_partner_hotel_image",
    "reorder_partner_hotel_images",
    "partner_hotel_content",
    "partner_hotel_content_editor",
    "partner_hotel_edit_profile",
    "partner_hotel_images",
    "partner_hotel_per_room_policies",
    "partner_hotel_policies",
    "partner_hotel_profile",
    "save_partner_hotel_amenities",
    "save_partner_hotel_content",
    "save_partner_hotel_policies",
]
