from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, normalize_label, now_utc, register_content_change
from src.app.modules.partner.services.content.amenities import _amenity_category
from src.app.modules.partner.services.content.queries import content_page_for_prop
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def save_partner_hotel_content(
    prop_id: int,
    *,
    description: str,
    highlights: str,
    amenities_text: str,
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "description": clean_text(description),
        "highlights": clean_text(highlights),
        "amenities_text": clean_text(amenities_text),
        "source": "partner_manual",
        "updated_at": now_utc(),
    }
    document = db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_content_change(prop_id, "hotel_content_pages", "upsert", payload, changed_by=changed_by)
    return document


def save_partner_hotel_amenities(
    prop_id: int,
    *,
    active_amenities: list[str],
    amenities_text: str | None = None,
    room_type_id: str = "",
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    current = content_page_for_prop(prop_id)
    clean_active: list[str] = []
    seen: set[str] = set()
    for item in active_amenities:
        label = normalize_label(item)
        key = label.lower()
        if not label or key in seen:
            continue
        seen.add(key)
        clean_active.append(label)

    if room_type_id:
        room_amenities = dict(current.get("room_amenities") or {})
        room_amenities[room_type_id] = {
            "active_amenities": clean_active,
            "amenities_text": clean_text(amenities_text) or ", ".join(clean_active),
        }
        document = db.hotel_content_pages.find_one_and_update(
            {"prop_id": prop_id},
            {"$set": {"room_amenities": room_amenities, "updated_at": now_utc()}, "$setOnInsert": {"created_at": now_utc()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    else:
        payload = {
            "prop_id": prop_id,
            "description": current.get("description") or "",
            "highlights": current.get("highlights") or "",
            "amenities_text": clean_text(amenities_text) or ", ".join(clean_active),
            "active_amenities": clean_active,
            "amenities_catalog": [{"category": _amenity_category(label), "label": label} for label in clean_active],
            "source": current.get("source") or "partner_manual",
            "updated_at": now_utc(),
        }
        document = db.hotel_content_pages.find_one_and_update(
            {"prop_id": prop_id},
            {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
    register_content_change(prop_id, "hotel_content_pages", "upsert_amenities", {"room_type_id": room_type_id, "count": len(clean_active)}, changed_by=changed_by)
    return document


def save_partner_hotel_policies(
    prop_id: int,
    *,
    check_in_time: str,
    check_out_time: str,
    cancellation_policy: str,
    pet_policy: str,
    children_policy: str,
    extra_bed_policy: str = "",
    payment_policy: str = "",
    house_rules: str = "",
    room_type_id: str = "",
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    clean_room_type = clean_text(room_type_id)
    # Build the filter: hotel-wide (room_type_id="") or per-room-type
    filter_: dict[str, object] = {"prop_id": prop_id}
    if clean_room_type:
        filter_["room_type_id"] = clean_room_type
    else:
        filter_["room_type_id"] = {"$in": ["", None]}
    payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type,
        "check_in_time": clean_text(check_in_time),
        "check_out_time": clean_text(check_out_time),
        "cancellation_policy": clean_text(cancellation_policy),
        "pet_policy": clean_text(pet_policy),
        "children_policy": clean_text(children_policy),
        "extra_bed_policy": clean_text(extra_bed_policy),
        "payment_policy": clean_text(payment_policy),
        "house_rules": clean_text(house_rules),
        "source": "partner_manual",
        "updated_at": now_utc(),
    }
    document = db.hotel_policies.find_one_and_update(
        filter_,
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_content_change(prop_id, "hotel_policies", "upsert", payload, changed_by=changed_by)
    return document
