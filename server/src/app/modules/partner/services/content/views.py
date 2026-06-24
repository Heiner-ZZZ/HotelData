from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import clean_text
from src.app.modules.partner.services.content.amenities import amenities_payload_for_prop
from src.app.modules.partner.services.content.queries import (
    content_page_for_prop,
    images_for_prop,
    policies_for_prop,
    recent_content_changes,
)
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.app.modules.partner.services.properties.metadata import profile_description, profile_payload
from src.database.connection import get_database


def partner_hotel_content(prop_id: int, room_type_id: str = "") -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    content_page = content_page_for_prop(prop_id)
    policies = policies_for_prop(prop_id)
    images = images_for_prop(prop_id)
    detail["content_page"] = content_page
    detail["policies"] = policies
    detail["images"] = images[:4]
    detail["images_count"] = len(images)
    detail["recent_changes"] = recent_content_changes(prop_id)
    detail["amenities"] = amenities_payload_for_prop(prop_id, room_type_id=room_type_id)
    from src.app.modules.partner.services.rooms import _room_types_for_prop
    detail["room_types"] = _room_types_for_prop(prop_id)
    detail["room_amenities"] = content_page.get("room_amenities", {})
    return detail


def partner_hotel_content_editor(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["content_page"] = content_page_for_prop(prop_id)
    detail["recent_changes"] = recent_content_changes(prop_id)
    return detail


def partner_hotel_policies(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["policies"] = policies_for_prop(prop_id)
    detail["recent_changes"] = recent_content_changes(prop_id)
    # Include room types so the UI can offer per-room-type policies
    from src.app.modules.partner.services.rooms import _room_types_for_prop
    detail["room_types"] = _room_types_for_prop(prop_id)
    detail["per_room_policies"] = list(
        get_database().hotel_policies.find(
            {"prop_id": prop_id, "room_type_id": {"$nin": ["", None]}},
            {"_id": 0},
        )
    )
    return detail


def partner_hotel_per_room_policies(prop_id: int, room_type_id: str) -> dict[str, Any] | None:
    """Get policies for a specific room type."""
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["policies"] = policies_for_prop(prop_id, room_type_id=room_type_id)
    detail["room_type_id"] = room_type_id
    return detail


def partner_hotel_images(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["images"] = images_for_prop(prop_id)
    detail["recent_changes"] = recent_content_changes(prop_id)
    return detail


def partner_hotel_profile(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    hotel = detail["hotel"]
    return {
        "hotel": hotel,
        "profile": {
            **profile_payload(hotel),
            "description": profile_description(prop_id, hotel),
        },
    }


def partner_hotel_edit_profile(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    hotel = detail["hotel"]
    content_page = content_page_for_prop(prop_id)
    policies = policies_for_prop(prop_id)
    images = images_for_prop(prop_id)
    amenities = amenities_payload_for_prop(prop_id)
    return {
        "hotel": hotel,
        "profile": {
            **profile_payload(hotel),
            "description": clean_text(hotel.get("description")) or clean_text(content_page.get("description")) or "",
        },
        "content_page": content_page,
        "policies": policies,
        "images": images[:20],
        "images_count": len(images),
        "amenities": amenities,
    }
