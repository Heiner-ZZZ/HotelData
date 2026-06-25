from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc, register_content_change
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def _next_sort_order(prop_id: int) -> int:
    """Get the next sort_order for a new image (1-based)."""
    db = get_database()
    last = db.hotel_images.find_one(
        {"prop_id": prop_id},
        sort=[("sort_order", -1)],
        projection={"sort_order": 1},
    )
    return (last.get("sort_order", 0) if last else 0) + 1


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

    # RF-006: Validate 10 image limit
    existing_count = db.hotel_images.count_documents({"prop_id": prop_id})
    if existing_count >= 10:
        raise ValueError("Máximo 10 imágenes por propiedad.")

    sort_order = _next_sort_order(prop_id)
    payload = {
        "prop_id": prop_id,
        "image_url": image_url,
        "title": title,
        "sort_order": sort_order,
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


def reorder_partner_hotel_images(
    prop_id: int,
    *,
    image_order: list[str],
    changed_by: str = "angular_api",
) -> list[dict[str, Any]]:
    """Reorder images for a property. image_order is a list of image_urls in desired order.
    First image becomes the primary (portada)."""
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        raise ValueError("Property not found")

    db = get_database()
    now = now_utc()

    for index, image_url in enumerate(image_order):
        sort_order = index + 1
        db.hotel_images.update_one(
            {"prop_id": prop_id, "image_url": clean_text(image_url)},
            {"$set": {"sort_order": sort_order, "updated_at": now}},
        )

    register_content_change(
        prop_id,
        "hotel_images",
        "reorder",
        {"image_order": image_order, "count": len(image_order)},
        changed_by=changed_by,
    )

    images = list(
        db.hotel_images.find(
            {"prop_id": prop_id, "image_url": {"$in": image_order}},
            {"_id": 0},
        ).sort([("sort_order", 1)])
    )
    return images
