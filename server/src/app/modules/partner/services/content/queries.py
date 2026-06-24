from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import clean_text, now_utc
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def _content_page_defaults(prop_id: int) -> dict[str, Any]:
    detail = partner_hotel_detail(prop_id)
    hotel = detail["hotel"] if detail else {}
    return {
        "prop_id": prop_id,
        "description": hotel.get("description") or "",
        "highlights": "",
        "amenities_text": "",
        "source": "partner_manual",
        "updated_at": None,
    }


def _policy_defaults(prop_id: int, room_type_id: str = "") -> dict[str, Any]:
    return {
        "prop_id": prop_id,
        "room_type_id": room_type_id,
        "check_in_time": "",
        "check_out_time": "",
        "cancellation_policy": "",
        "pet_policy": "",
        "children_policy": "",
        "extra_bed_policy": "",
        "payment_policy": "",
        "house_rules": "",
        "source": "partner_manual",
        "updated_at": None,
    }


def content_page_for_prop(prop_id: int) -> dict[str, Any]:
    db = get_database()
    page = db.hotel_content_pages.find_one({"prop_id": prop_id}, {"_id": 0})
    return page or _content_page_defaults(prop_id)


def policies_for_prop(prop_id: int, room_type_id: str = "") -> dict[str, Any]:
    db = get_database()
    filter_: dict[str, object] = {"prop_id": prop_id}
    if room_type_id:
        filter_["room_type_id"] = room_type_id
    else:
        filter_["room_type_id"] = {"$in": ["", None]}
    policies = db.hotel_policies.find_one(filter_, {"_id": 0})
    return policies or _policy_defaults(prop_id, room_type_id=room_type_id)


def images_for_prop(prop_id: int) -> list[dict[str, Any]]:
    db = get_database()
    images = list(
        db.hotel_images.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("created_at", -1)])
        .limit(24)
    )
    for image in images:
        created_at = image.get("created_at")
        image["created_at_label"] = created_at.isoformat() if hasattr(created_at, "isoformat") else "N/D"
    return images


def recent_content_changes(prop_id: int, limit: int = 8) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.hotel_content_changes.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("changed_at", -1)])
        .limit(limit)
    )
    for item in items:
        changed_at = item.get("changed_at")
        item["changed_at_label"] = changed_at.isoformat() if hasattr(changed_at, "isoformat") else "N/D"
    return items
