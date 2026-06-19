from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc, register_content_change
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def add_partner_hotel_image(
    prop_id: int,
    *,
    image_url: str,
    title: str = "",
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    image_url = clean_text(image_url)
    title = clean_text(title)
    if not image_url:
        raise ValueError("Debe ingresar una URL de imagen.")
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "image_url": image_url,
        "title": title,
        "source": "partner_manual",
        "updated_at": now_utc(),
    }
    document = db.hotel_images.find_one_and_update(
        {"prop_id": prop_id, "image_url": image_url},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_content_change(prop_id, "hotel_images", "upsert", payload, changed_by=changed_by)
    return document


def delete_partner_hotel_image(
    prop_id: int,
    *,
    image_url: str,
    changed_by: str = "angular_api",
) -> bool:
    db = get_database()
    result = db.hotel_images.delete_one({"prop_id": prop_id, "image_url": image_url})
    if result.deleted_count:
        register_content_change(prop_id, "hotel_images", "delete", {"image_url": image_url}, changed_by=changed_by)
    return result.deleted_count > 0
