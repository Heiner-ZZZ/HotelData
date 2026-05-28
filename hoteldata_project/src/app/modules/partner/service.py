from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo import ReturnDocument
from pymongo.errors import CollectionInvalid

from src.database.connection import get_database
from src.app.modules.partner.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="partner",
        status="partial",
        description="Modulo inicial de Hotel Partner con contenido, habitaciones e inventario operativo basico.",
    )


def ensure_hotel_content_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    for name in ("hotel_images", "hotel_policies", "hotel_content_pages", "hotel_content_changes"):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs = {
        "hotel_images": [
            ("prop_id_1", db.hotel_images.create_index("prop_id")),
            ("image_url_1", db.hotel_images.create_index([("prop_id", 1), ("image_url", 1)], unique=True)),
            ("created_at_-1", db.hotel_images.create_index([("created_at", -1)])),
        ],
        "hotel_policies": [
            ("prop_id_1", db.hotel_policies.create_index([("prop_id", 1)], unique=True)),
            ("updated_at_-1", db.hotel_policies.create_index([("updated_at", -1)])),
        ],
        "hotel_content_pages": [
            ("prop_id_1", db.hotel_content_pages.create_index([("prop_id", 1)], unique=True)),
            ("updated_at_-1", db.hotel_content_pages.create_index([("updated_at", -1)])),
        ],
        "hotel_content_changes": [
            ("prop_id_1", db.hotel_content_changes.create_index("prop_id")),
            ("entity_type_1", db.hotel_content_changes.create_index("entity_type")),
            ("changed_at_-1", db.hotel_content_changes.create_index([("changed_at", -1)])),
        ],
    }
    for indexes in index_specs.values():
        for label, name in indexes:
            created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}


def ensure_inventory_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    for name in ("room_types", "hotel_rooms", "room_inventory_calendar", "room_availability_blocks", "blackout_dates"):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs = {
        "room_types": [
            ("room_type_id_1", db.room_types.create_index([("room_type_id", 1)], unique=True)),
            ("prop_id_1", db.room_types.create_index("prop_id")),
            ("is_active_1", db.room_types.create_index("is_active")),
        ],
        "hotel_rooms": [
            ("hotel_room_id_1", db.hotel_rooms.create_index([("hotel_room_id", 1)], unique=True)),
            ("prop_id_1", db.hotel_rooms.create_index("prop_id")),
            ("room_type_id_1", db.hotel_rooms.create_index("room_type_id")),
        ],
        "room_inventory_calendar": [
            ("prop_room_date", db.room_inventory_calendar.create_index([("prop_id", 1), ("room_type_id", 1), ("date", 1)], unique=True)),
            ("date_1", db.room_inventory_calendar.create_index("date")),
        ],
        "room_availability_blocks": [
            ("prop_id_1", db.room_availability_blocks.create_index("prop_id")),
            ("room_type_id_1", db.room_availability_blocks.create_index("room_type_id")),
            ("start_date_1", db.room_availability_blocks.create_index("start_date")),
        ],
        "blackout_dates": [
            ("prop_id_1", db.blackout_dates.create_index("prop_id")),
            ("room_type_id_1", db.blackout_dates.create_index("room_type_id")),
            ("start_date_1", db.blackout_dates.create_index("start_date")),
            ("end_date_1", db.blackout_dates.create_index("end_date")),
        ],
    }
    for indexes in index_specs.values():
        for label, name in indexes:
            created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}


def _active_fact_collection() -> tuple[Collection, str]:
    db = get_database()
    if db.fact_hotel_reservations.estimated_document_count() > 0:
        return db.fact_hotel_reservations, "fact_hotel_reservations"
    return db.fact_hotel_events, "fact_hotel_events"


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or not text.lstrip("-").isdigit():
        return None
    return int(text)


def _money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.2f}"


def _number(value: Any, decimals: int = 1) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.{decimals}f}"


def _now() -> datetime:
    return datetime.now(UTC)


def _hotel_display_name(hotel: dict[str, Any], prop_id: int) -> str:
    return hotel.get("display_name") or hotel.get("hotel_name") or hotel.get("hotel_label") or f"Hotel Partner {prop_id}"


def _destination_display_name(destination: dict[str, Any], destination_id: int) -> str:
    return destination.get("destination_display_name") or destination.get("destination_name") or destination.get("destination_label") or f"Destino {destination_id}"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_positive_int(value: Any, default: int = 0) -> int:
    parsed = _safe_int(value)
    if parsed is None:
        return default
    return max(parsed, 0)


def _safe_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "on", "yes", "si"}


def _slugify(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "room"


def _register_content_change(
    prop_id: int,
    entity_type: str,
    action: str,
    payload: dict[str, Any],
    changed_by: str = "partner_web",
) -> None:
    db = get_database()
    db.hotel_content_changes.insert_one(
        {
            "prop_id": prop_id,
            "entity_type": entity_type,
            "action": action,
            "payload": payload,
            "changed_by": changed_by,
            "changed_at": _now(),
        }
    )


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
        "source": "partner_manual",
        "updated_at": None,
    }


def _recent_content_changes(prop_id: int, limit: int = 8) -> list[dict[str, Any]]:
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


def _content_page_for_prop(prop_id: int) -> dict[str, Any]:
    db = get_database()
    page = db.hotel_content_pages.find_one({"prop_id": prop_id}, {"_id": 0})
    return page or _content_page_defaults(prop_id)


def _policies_for_prop(prop_id: int) -> dict[str, Any]:
    db = get_database()
    policies = db.hotel_policies.find_one({"prop_id": prop_id}, {"_id": 0})
    return policies or _policy_defaults(prop_id)


def _images_for_prop(prop_id: int) -> list[dict[str, Any]]:
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


def _room_types_for_prop(prop_id: int, limit: int = 50) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_types.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )
    for item in items:
        item["capacity_label"] = f"{item.get('base_capacity', 0)} base · {item.get('max_adults', 0)} adultos · {item.get('max_children', 0)} niños"
    return items


def _inventory_for_prop(prop_id: int, limit: int = 90) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.room_inventory_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("room_type_id", 1)])
        .limit(limit)
    )
    room_name_lookup = {
        item["room_type_id"]: item.get("name") or item["room_type_id"]
        for item in db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1})
    }
    for item in items:
        item["room_type_name"] = room_name_lookup.get(item["room_type_id"], item["room_type_id"])
        item["occupancy_label"] = f"{item.get('available_rooms', 0)}/{item.get('total_rooms', 0)} disponibles"
    return items


def _blackout_blocks_for_prop(prop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.blackout_dates.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("created_at", -1)])
        .limit(limit)
    )
    for item in items:
        item["range_label"] = f"{item.get('start_date')} -> {item.get('end_date')}"
    return items


def _performance_for_prop(prop_id: int) -> dict[str, Any]:
    collection, source_collection = _active_fact_collection()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$prop_id",
                "searches": {"$sum": 1},
                "clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
                "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "gross_revenue": {"$sum": "$reservas_brutas_usd"},
                "avg_price": {"$avg": "$price_usd"},
                "review_score": {"$avg": "$prop_review_score"},
                "starrating": {"$max": "$prop_starrating"},
            }
        },
    ]
    metrics = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    if not metrics:
        return {
            "source_collection": source_collection,
            "searches": 0,
            "clicks": 0,
            "reservations": 0,
            "gross_revenue": 0.0,
            "avg_price": None,
            "review_score": None,
            "starrating": None,
            "conversion_rate": 0.0,
            "click_rate": 0.0,
            "gross_revenue_label": "0.00",
            "avg_price_label": "N/D",
            "review_score_label": "N/D",
        }
    searches = int(metrics.get("searches") or 0)
    clicks = int(metrics.get("clicks") or 0)
    reservations = int(metrics.get("reservations") or 0)
    conversion_rate = round((reservations / searches) * 100, 2) if searches else 0.0
    click_rate = round((clicks / searches) * 100, 2) if searches else 0.0
    return {
        "source_collection": source_collection,
        "searches": searches,
        "clicks": clicks,
        "reservations": reservations,
        "gross_revenue": float(metrics.get("gross_revenue") or 0.0),
        "avg_price": metrics.get("avg_price"),
        "review_score": metrics.get("review_score"),
        "starrating": metrics.get("starrating"),
        "conversion_rate": conversion_rate,
        "click_rate": click_rate,
        "gross_revenue_label": _money(metrics.get("gross_revenue") or 0.0),
        "avg_price_label": _money(metrics.get("avg_price")) if metrics.get("avg_price") is not None else "N/D",
        "review_score_label": _number(metrics.get("review_score")),
    }


def list_partner_hotels(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    filters: dict[str, Any] = {}
    query = query.strip()
    query_as_id = _safe_int(query)
    if query:
        filters["$or"] = [
            {"hotel_label": {"$regex": query, "$options": "i"}},
            {"hotel_name": {"$regex": query, "$options": "i"}},
        ]
        if query_as_id is not None:
            filters["$or"].append({"prop_id": query_as_id})

    total = db.dim_hotels.count_documents(filters)
    total_pages = (total + page_size - 1) // page_size if total else 0
    if total_pages and page > total_pages:
        page = total_pages

    cursor = (
        db.dim_hotels.find(filters, {"_id": 0})
        .sort([("prop_id", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(cursor)
    enriched = []
    for item in items:
        prop_id = int(item["prop_id"])
        performance = _performance_for_prop(prop_id)
        enriched.append(
            {
                **item,
                "prop_id": prop_id,
                "display_name": _hotel_display_name(item, prop_id),
                "country_display_name": item.get("display_country_label") or (f"Mercado hotelero {item.get('prop_country_id')}" if item.get("prop_country_id") is not None else "N/D"),
                "review_score_label": _number(item.get("prop_review_score")),
                "performance": performance,
            }
        )
    return {
        "items": enriched,
        "query": query,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
        "start_index": ((page - 1) * page_size) + 1 if total else 0,
        "end_index": ((page - 1) * page_size) + len(enriched) if enriched else 0,
    }


def partner_hotel_detail(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0})
    if hotel is None:
        return None
    master_hotel = db.hotels.find_one({"hotel_code": {"$exists": True}}, {"_id": 0}) or {}
    performance = _performance_for_prop(prop_id)
    return {
        "hotel": {
            **hotel,
            "prop_id": prop_id,
            "display_name": _hotel_display_name(hotel, prop_id),
            "country_display_name": hotel.get("display_country_label") or (f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else "N/D"),
            "review_score_label": _number(hotel.get("prop_review_score")),
        },
        "performance": performance,
        "master_hotel": master_hotel,
    }


def partner_hotel_performance(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$srch_destination_id",
                "searches": {"$sum": 1},
                "reservations": {
                    "$sum": {
                        "$cond": [
                            {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]},
                            1,
                            0,
                        ]
                    }
                },
                "avg_price": {"$avg": "$price_usd"},
            }
        },
        {"$sort": {"searches": -1}},
        {"$limit": 6},
    ]
    top_destinations = list(collection.aggregate(pipeline, allowDiskUse=True))
    destination_ids = [row["_id"] for row in top_destinations if row.get("_id") is not None]
    destination_lookup = {
        int(item["srch_destination_id"]): item
        for item in db.dim_destinations.find({"srch_destination_id": {"$in": destination_ids}}, {"_id": 0})
        if item.get("srch_destination_id") is not None
    }
    detail["top_destinations"] = [
        {
            "destination_label": _destination_display_name(destination_lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "searches": int(row.get("searches") or 0),
            "reservations": int(row.get("reservations") or 0),
            "avg_price_label": _money(row.get("avg_price")),
        }
        for row in top_destinations
        if row.get("_id") is not None
    ]
    return detail


def partner_hotel_content(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    content_page = _content_page_for_prop(prop_id)
    policies = _policies_for_prop(prop_id)
    images = _images_for_prop(prop_id)
    detail["content_page"] = content_page
    detail["policies"] = policies
    detail["images"] = images[:4]
    detail["images_count"] = len(images)
    detail["recent_changes"] = _recent_content_changes(prop_id)
    return detail


def partner_hotel_content_editor(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["content_page"] = _content_page_for_prop(prop_id)
    detail["recent_changes"] = _recent_content_changes(prop_id)
    return detail


def partner_hotel_policies(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["policies"] = _policies_for_prop(prop_id)
    detail["recent_changes"] = _recent_content_changes(prop_id)
    return detail


def partner_hotel_images(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    detail["images"] = _images_for_prop(prop_id)
    detail["recent_changes"] = _recent_content_changes(prop_id)
    return detail


def partner_hotel_rooms(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    ensure_inventory_collections()
    room_types = _room_types_for_prop(prop_id)
    detail["room_types"] = room_types
    detail["room_type_count"] = len(room_types)
    return detail


def partner_hotel_inventory(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    ensure_inventory_collections()
    room_types = _room_types_for_prop(prop_id)
    detail["room_types"] = room_types
    detail["inventory_items"] = _inventory_for_prop(prop_id)
    detail["blackout_items"] = _blackout_blocks_for_prop(prop_id)
    return detail


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
    ensure_hotel_content_collections()
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "description": _clean_text(description),
        "highlights": _clean_text(highlights),
        "amenities_text": _clean_text(amenities_text),
        "source": "partner_manual",
        "updated_at": _now(),
    }
    document = db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    _register_content_change(prop_id, "hotel_content_pages", "upsert", payload, changed_by=changed_by)
    return document


def save_partner_hotel_policies(
    prop_id: int,
    *,
    check_in_time: str,
    check_out_time: str,
    cancellation_policy: str,
    pet_policy: str,
    children_policy: str,
    changed_by: str = "partner_web",
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    ensure_hotel_content_collections()
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "check_in_time": _clean_text(check_in_time),
        "check_out_time": _clean_text(check_out_time),
        "cancellation_policy": _clean_text(cancellation_policy),
        "pet_policy": _clean_text(pet_policy),
        "children_policy": _clean_text(children_policy),
        "source": "partner_manual",
        "updated_at": _now(),
    }
    document = db.hotel_policies.find_one_and_update(
        {"prop_id": prop_id},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    _register_content_change(prop_id, "hotel_policies", "upsert", payload, changed_by=changed_by)
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
    image_url = _clean_text(image_url)
    title = _clean_text(title)
    if not image_url:
        raise ValueError("Debe ingresar una URL de imagen.")
    ensure_hotel_content_collections()
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "image_url": image_url,
        "title": title,
        "source": "partner_manual",
        "updated_at": _now(),
    }
    document = db.hotel_images.find_one_and_update(
        {"prop_id": prop_id, "image_url": image_url},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    _register_content_change(prop_id, "hotel_images", "upsert", payload, changed_by=changed_by)
    return document


def create_room_type(
    prop_id: int,
    *,
    name: str,
    description: str,
    max_adults: Any,
    max_children: Any,
    base_capacity: Any,
    is_active: Any = True,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    ensure_inventory_collections()
    db = get_database()
    clean_name = _clean_text(name)
    if not clean_name:
        raise ValueError("Debe ingresar el nombre del tipo de habitación.")
    room_type_id = f"RT-{prop_id}-{_slugify(clean_name)}"
    max_adults_value = _safe_positive_int(max_adults, 1)
    max_children_value = _safe_positive_int(max_children, 0)
    base_capacity_value = _safe_positive_int(base_capacity, max_adults_value or 1)
    payload = {
        "room_type_id": room_type_id,
        "prop_id": prop_id,
        "name": clean_name,
        "description": _clean_text(description),
        "max_adults": max_adults_value,
        "max_children": max_children_value,
        "base_capacity": base_capacity_value,
        "is_active": _safe_bool(is_active),
        "updated_at": _now(),
    }
    document = db.room_types.find_one_and_update(
        {"room_type_id": room_type_id},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    db.hotel_rooms.find_one_and_update(
        {"hotel_room_id": f"HR-{room_type_id}"},
        {
            "$set": {
                "hotel_room_id": f"HR-{room_type_id}",
                "prop_id": prop_id,
                "room_type_id": room_type_id,
                "room_label": clean_name,
                "is_active": payload["is_active"],
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return document


def save_inventory_entry(
    prop_id: int,
    *,
    room_type_id: str,
    date: str,
    total_rooms: Any,
    available_rooms: Any,
    blocked_rooms: Any,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    ensure_inventory_collections()
    db = get_database()
    clean_room_type_id = _clean_text(room_type_id)
    clean_date = _clean_text(date)
    if not clean_room_type_id or not clean_date:
        raise ValueError("Debe indicar room_type_id y fecha.")
    if db.room_types.find_one({"prop_id": prop_id, "room_type_id": clean_room_type_id}, {"_id": 1}) is None:
        raise ValueError("El room_type_id no existe para este hotel.")
    total_value = _safe_positive_int(total_rooms, 0)
    blocked_value = _safe_positive_int(blocked_rooms, 0)
    available_value = _safe_positive_int(available_rooms, 0)
    if blocked_value > total_value:
        blocked_value = total_value
    if available_value > total_value:
        available_value = total_value
    if available_value + blocked_value > total_value:
        available_value = max(total_value - blocked_value, 0)
    payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "date": clean_date,
        "total_rooms": total_value,
        "available_rooms": available_value,
        "blocked_rooms": blocked_value,
        "updated_at": _now(),
    }
    return db.room_inventory_calendar.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": clean_room_type_id, "date": clean_date},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def create_blackout_block(
    prop_id: int,
    *,
    room_type_id: str,
    start_date: str,
    end_date: str,
    reason: str,
    blocked_rooms: Any,
) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    ensure_inventory_collections()
    db = get_database()
    clean_room_type_id = _clean_text(room_type_id)
    clean_start = _clean_text(start_date)
    clean_end = _clean_text(end_date)
    if not clean_room_type_id or not clean_start or not clean_end:
        raise ValueError("Debe indicar room_type_id, fecha inicio y fecha fin.")
    if db.room_types.find_one({"prop_id": prop_id, "room_type_id": clean_room_type_id}, {"_id": 1}) is None:
        raise ValueError("El room_type_id no existe para este hotel.")
    blocked_value = _safe_positive_int(blocked_rooms, 0)
    blackout_payload = {
        "prop_id": prop_id,
        "room_type_id": clean_room_type_id,
        "start_date": clean_start,
        "end_date": clean_end,
        "reason": _clean_text(reason),
        "blocked_rooms": blocked_value,
        "updated_at": _now(),
    }
    blackout_doc = db.blackout_dates.find_one_and_update(
        {
            "prop_id": prop_id,
            "room_type_id": clean_room_type_id,
            "start_date": clean_start,
            "end_date": clean_end,
        },
        {"$set": blackout_payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    db.room_availability_blocks.find_one_and_update(
        {
            "prop_id": prop_id,
            "room_type_id": clean_room_type_id,
            "start_date": clean_start,
            "end_date": clean_end,
        },
        {
            "$set": {
                "prop_id": prop_id,
                "room_type_id": clean_room_type_id,
                "start_date": clean_start,
                "end_date": clean_end,
                "blocked_rooms": blocked_value,
                "reason": blackout_payload["reason"],
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return blackout_doc
