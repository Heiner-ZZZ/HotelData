from __future__ import annotations

from typing import Any

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


def _policy_defaults(prop_id: int, room_type_id: str = "", rate_plan_id: str = "", season_id: str = "") -> dict[str, Any]:
    return {
        "prop_id": prop_id,
        "room_type_id": room_type_id,
        "rate_plan_id": rate_plan_id,
        "season_id": season_id,
        "check_in_time": "",
        "check_out_time": "",
        "cancellation_policy": "",
        "pet_policy": "",
        "children_policy": "",
        "extra_bed_policy": "",
        "payment_policy": "",
        "house_rules": "",
        "deposit_percent": 0,
        "deposit_required": False,
        "cancellation_penalty_percent": 100,
        "source": "partner_manual",
        "updated_at": None,
    }


def content_page_for_prop(prop_id: int) -> dict[str, Any]:
    db = get_database()
    page = db.hotel_content_pages.find_one({"prop_id": prop_id}, {"_id": 0})
    return page or _content_page_defaults(prop_id)


def policies_for_prop(prop_id: int, room_type_id: str = "", rate_plan_id: str = "", season_id: str = "") -> dict[str, Any]:
    """Resolve policies with hierarchy: rate_plan > room_type > hotel-wide.

    If rate_plan_id is provided, looks for rate-plan-specific policies first.
    Falls back to room-type-specific, then hotel-wide policies.
    Returns default empty policies if nothing is configured.
    """
    db = get_database()

    def _build_filter(rt: str, rp: str = "", se: str = "") -> dict[str, object]:
        f: dict[str, object] = {"prop_id": prop_id}
        if rp:
            f["rate_plan_id"] = rp
        elif rt:
            f["room_type_id"] = rt
            f["rate_plan_id"] = {"$in": ["", None]}
        else:
            f["room_type_id"] = {"$in": ["", None]}
            f["rate_plan_id"] = {"$in": ["", None]}
        if se:
            f["season_id"] = se
        else:
            f["season_id"] = {"$in": ["", None]}
        return f

    # Try rate_plan-level first (only if rate_plan_id provided)
    if rate_plan_id:
        policies = db.hotel_policies.find_one(_build_filter("", rate_plan_id, season_id), {"_id": 0})
        if policies:
            return policies

    # Fall back to room_type-level or hotel-wide
    policies = db.hotel_policies.find_one(_build_filter(room_type_id, "", season_id), {"_id": 0})
    return policies or _policy_defaults(prop_id, room_type_id=room_type_id, rate_plan_id=rate_plan_id, season_id=season_id)


def images_for_prop(prop_id: int) -> list[dict[str, Any]]:
    db = get_database()
    images = list(
        db.hotel_images.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("sort_order", 1), ("created_at", -1)])
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
