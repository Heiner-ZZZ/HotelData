"""Content sub-domain: content pages, amenities, policies, images, profile edit.

Owns the read/write paths for everything a partner edits in the
"content" tab of a property: descriptions, highlights, amenity catalog,
policies, image gallery, and the profile-level compose views that
combine those collections with the hotel record.
"""
from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import (
    clean_text,
    normalize_label,
    now_utc,
    register_content_change,
    split_multiline_tokens,
)
from src.app.modules.partner.services.properties.metadata import (
    profile_description as _profile_description,
    profile_payload as _profile_payload,
)
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


DEFAULT_AMENITIES_CATALOG: dict[str, list[str]] = {
    "General": ["Wi-Fi", "Recepcion 24 horas", "Aire acondicionado", "Parking", "Piscina", "Gimnasio"],
    "Habitacion": ["TV", "Minibar", "Caja fuerte", "Balcon", "Servicio a la habitacion"],
    "Gastronomia": ["Desayuno incluido", "Restaurante", "Bar", "Cafe"],
    "Negocios": ["Centro de negocios", "Salas de reuniones"],
    "Familia": ["Habitaciones familiares", "Cunas", "Camas extra"],
    "Bienestar": ["Spa", "Sauna", "Masajes"],
}


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


def _policy_defaults(prop_id: int) -> dict[str, Any]:
    return {
        "prop_id": prop_id,
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


def policies_for_prop(prop_id: int) -> dict[str, Any]:
    db = get_database()
    policies = db.hotel_policies.find_one({"prop_id": prop_id}, {"_id": 0})
    return policies or _policy_defaults(prop_id)


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


def _amenity_category(label: str) -> str:
    normalized = label.lower()
    checks = [
        ("Habitacion", {"tv", "minibar", "caja fuerte", "balcon", "habitacion", "servicio a la habitacion"}),
        ("Gastronomia", {"desayuno", "restaurante", "bar", "cafe"}),
        ("Negocios", {"negocios", "reuniones", "business", "meeting"}),
        ("Familia", {"familia", "cuna", "camas extra", "ninos", "niños"}),
        ("Bienestar", {"spa", "sauna", "masajes", "wellness", "gimnasio"}),
        ("General", {"wifi", "wi-fi", "parking", "recepcion", "aire acondicionado", "pool", "piscina"}),
    ]
    for category, keywords in checks:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "General"


def amenities_payload_for_prop(prop_id: int) -> dict[str, Any]:
    page = content_page_for_prop(prop_id)
    stored_active = [normalize_label(item) for item in page.get("active_amenities", []) if normalize_label(item)]
    parsed_active = split_multiline_tokens(page.get("amenities_text"))
    active_items = stored_active or parsed_active

    catalog_items: list[dict[str, str]] = []
    for category, labels in DEFAULT_AMENITIES_CATALOG.items():
        for label in labels:
            catalog_items.append({"category": category, "label": label})
    for item in page.get("amenities_catalog", []):
        label = normalize_label(item.get("label"))
        if label:
            catalog_items.append({"category": normalize_label(item.get("category")) or _amenity_category(label), "label": label})
    for label in active_items:
        catalog_items.append({"category": _amenity_category(label), "label": label})

    seen: set[tuple[str, str]] = set()
    grouped: dict[str, list[dict[str, Any]]] = {}
    active_lookup = {item.lower() for item in active_items}
    for item in catalog_items:
        category = normalize_label(item.get("category")) or "General"
        label = normalize_label(item.get("label"))
        key = (category.lower(), label.lower())
        if not label or key in seen:
            continue
        seen.add(key)
        grouped.setdefault(category, []).append({"label": label, "active": label.lower() in active_lookup})

    return {
        "active_amenities": active_items,
        "catalog": [
            {"category": category, "items": sorted(items, key=lambda entry: entry["label"].lower())}
            for category, items in grouped.items()
        ],
    }


def partner_hotel_content(prop_id: int) -> dict[str, Any] | None:
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
    detail["amenities"] = amenities_payload_for_prop(prop_id)
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
            **_profile_payload(hotel),
            "description": _profile_description(prop_id, hotel),
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
            **_profile_payload(hotel),
            "description": clean_text(hotel.get("description")) or clean_text(content_page.get("description")) or "",
        },
        "content_page": content_page,
        "policies": policies,
        "images": images[:20],
        "images_count": len(images),
        "amenities": amenities,
    }


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
    register_content_change(prop_id, "hotel_content_pages", "upsert_amenities", payload, changed_by=changed_by)
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
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    payload = {
        "prop_id": prop_id,
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
        {"prop_id": prop_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_content_change(prop_id, "hotel_policies", "upsert", payload, changed_by=changed_by)
    return document


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
