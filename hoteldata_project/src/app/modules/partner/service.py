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


def ensure_hotel_profile_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    if "hotel_profile_changes" not in db.list_collection_names():
        try:
            db.create_collection("hotel_profile_changes")
            created_collections.append("hotel_profile_changes")
        except CollectionInvalid:
            pass

    index_specs = [
        ("hotel_profile_changes.prop_id_1", db.hotel_profile_changes.create_index("prop_id")),
        ("hotel_profile_changes.changed_at_-1", db.hotel_profile_changes.create_index([("changed_at", -1)])),
        ("hotel_profile_changes.prop_field_changed_at", db.hotel_profile_changes.create_index([("prop_id", 1), ("field", 1), ("changed_at", -1)])),
        ("dim_hotels.prop_id_1", db.dim_hotels.create_index([("prop_id", 1)], unique=True)),
        ("dim_hotels.display_name_1", db.dim_hotels.create_index("display_name")),
        ("dim_hotels.manual_override_1", db.dim_hotels.create_index("manual_override")),
    ]
    for label, name in index_specs:
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


def _normalize_label(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _split_multiline_tokens(value: Any) -> list[str]:
    text = str(value or "")
    normalized = text.replace("\r", "\n").replace(";", "\n").replace(",", "\n")
    items: list[str] = []
    for chunk in normalized.split("\n"):
        clean = _normalize_label(chunk.lstrip("-* ").strip())
        if clean:
            items.append(clean)
    return items


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


def _hotel_generated_name(hotel: dict[str, Any], prop_id: int) -> str:
    return _clean_text(hotel.get("original_generated_name")) or _hotel_display_name(hotel, prop_id)


def _ensure_hotel_profile_metadata(prop_id: int | None = None) -> int:
    ensure_hotel_profile_collections()
    db = get_database()
    filter_doc: dict[str, Any] = {"manual_override": {"$exists": False}}
    if prop_id is not None:
        filter_doc["prop_id"] = prop_id
    modified = 0
    for hotel in db.dim_hotels.find(
        filter_doc,
        {
            "_id": 1,
            "prop_id": 1,
            "display_name": 1,
            "hotel_name": 1,
            "hotel_label": 1,
            "demo_enriched": 1,
            "manual_override": 1,
            "name_source": 1,
            "updated_by": 1,
            "updated_at": 1,
            "original_generated_name": 1,
        },
    ):
        prop_id_value = int(hotel.get("prop_id") or 0)
        generated_name = _clean_text(hotel.get("display_name"))
        if not generated_name:
            generated_name = _hotel_display_name(hotel, prop_id_value)
        update_payload: dict[str, Any] = {
            "manual_override": bool(hotel.get("manual_override", False)),
            "name_source": hotel.get("name_source") or "generated_from_id",
        }
        if hotel.get("demo_enriched") and not _clean_text(hotel.get("original_generated_name")):
            update_payload["original_generated_name"] = generated_name
        elif not _clean_text(hotel.get("original_generated_name")):
            update_payload["original_generated_name"] = generated_name
        if update_payload:
            result = db.dim_hotels.update_one({"_id": hotel["_id"]}, {"$set": update_payload})
            modified += int(result.modified_count)
    return modified


def _profile_badge(hotel: dict[str, Any]) -> str:
    return "Nombre editado manualmente" if bool(hotel.get("manual_override")) else "Nombre generado"


def _profile_description(prop_id: int, hotel: dict[str, Any]) -> str:
    content_page = _content_page_for_prop(prop_id)
    return _clean_text(hotel.get("description")) or _clean_text(content_page.get("description")) or ""


def _profile_payload(hotel: dict[str, Any]) -> dict[str, Any]:
    prop_id = int(hotel.get("prop_id") or 0)
    return {
        "prop_id": prop_id,
        "hotel_name": _clean_text(hotel.get("hotel_name")) or _hotel_display_name(hotel, prop_id),
        "display_name": _hotel_display_name(hotel, prop_id),
        "display_country_label": hotel.get("display_country_label")
        or (f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else ""),
        "original_generated_name": _hotel_generated_name(hotel, prop_id),
        "manual_override": bool(hotel.get("manual_override", False)),
        "name_source": hotel.get("name_source") or "generated_from_id",
        "profile_badge": _profile_badge(hotel),
        "updated_by": hotel.get("updated_by"),
        "updated_at": hotel.get("updated_at").isoformat() if hasattr(hotel.get("updated_at"), "isoformat") else hotel.get("updated_at"),
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


DEFAULT_AMENITIES_CATALOG: dict[str, list[str]] = {
    "General": ["Wi-Fi", "Recepcion 24 horas", "Aire acondicionado", "Parking", "Piscina", "Gimnasio"],
    "Habitacion": ["TV", "Minibar", "Caja fuerte", "Balcon", "Servicio a la habitacion"],
    "Gastronomia": ["Desayuno incluido", "Restaurante", "Bar", "Cafe"],
    "Negocios": ["Centro de negocios", "Salas de reuniones"],
    "Familia": ["Habitaciones familiares", "Cunas", "Camas extra"],
    "Bienestar": ["Spa", "Sauna", "Masajes"],
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


def _amenities_payload_for_prop(prop_id: int) -> dict[str, Any]:
    page = _content_page_for_prop(prop_id)
    stored_active = [_normalize_label(item) for item in page.get("active_amenities", []) if _normalize_label(item)]
    parsed_active = _split_multiline_tokens(page.get("amenities_text"))
    active_items = stored_active or parsed_active

    catalog_items: list[dict[str, str]] = []
    for category, labels in DEFAULT_AMENITIES_CATALOG.items():
        for label in labels:
            catalog_items.append({"category": category, "label": label})
    for item in page.get("amenities_catalog", []):
        label = _normalize_label(item.get("label"))
        if label:
            catalog_items.append({"category": _normalize_label(item.get("category")) or _amenity_category(label), "label": label})
    for label in active_items:
        catalog_items.append({"category": _amenity_category(label), "label": label})

    seen: set[tuple[str, str]] = set()
    grouped: dict[str, list[dict[str, Any]]] = {}
    active_lookup = {item.lower() for item in active_items}
    for item in catalog_items:
        category = _normalize_label(item.get("category")) or "General"
        label = _normalize_label(item.get("label"))
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


def _synthetic_hotel(prop_id: int) -> dict[str, Any]:
    db = get_database()
    perf = _performance_for_prop(prop_id)
    country = "N/D"
    sample = db.fact_hotel_reservations.find_one({"prop_id": prop_id}, {"_id": 0, "prop_country_id": 1})
    if sample and sample.get("prop_country_id") is not None:
        country = f"Mercado hotelero {sample['prop_country_id']}"
    yield_score = _property_yield_score(perf)
    return {
        "prop_id": prop_id,
        "display_name": f"Hotel {prop_id}",
        "country_display_name": country,
        "location": country,
        "review_score_label": None,
        "prop_starrating": None,
        "status": "Operational" if yield_score >= 70 else ("Under Review" if yield_score >= 40 else "Maintenance"),
        "sync_status": "SYNC_ACTIVE",
        "sync_latency_ms": max(round(100 - yield_score * 0.8), 5),
        "yield_score": yield_score,
        "unit_count": 0,
        "performance": perf,
    }


def list_partner_hotels(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    query = query.strip()
    query_as_id = _safe_int(query)

    has_dim = db.dim_hotels.estimated_document_count() > 0
    if not has_dim:
        all_ids = db.fact_hotel_reservations.distinct("prop_id")
        all_ids.sort()
        if query_as_id is not None:
            all_ids = [pid for pid in all_ids if pid == query_as_id]
        total = len(all_ids)
        total_pages = (total + page_size - 1) // page_size if total else 0
        if total_pages and page > total_pages:
            page = total_pages
        page_ids = all_ids[(page - 1) * page_size: page * page_size]
        enriched = [_synthetic_hotel(pid) for pid in page_ids]
        return {
            "items": enriched,
            "query": query,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "start_index": (page - 1) * page_size + 1 if total else 0,
            "end_index": min(page * page_size, total),
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    filters: dict[str, Any] = {}
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
        country = item.get("display_country_label") or (f"Mercado hotelero {item.get('prop_country_id')}" if item.get("prop_country_id") is not None else "N/D")
        yield_score = _property_yield_score(performance)
        status = "Operational" if yield_score >= 70 else ("Under Review" if yield_score >= 40 else "Maintenance")
        sync_status = "SYNC_ACTIVE"
        sync_latency = max(round(100 - yield_score * 0.8), 5)
        enriched.append(
            {
                **item,
                "prop_id": prop_id,
                "display_name": _hotel_display_name(item, prop_id),
                "country_display_name": country,
                "location": country,
                "review_score_label": _number(item.get("prop_review_score")),
                "prop_starrating": item.get("prop_starrating"),
                "status": status,
                "sync_status": sync_status,
                "sync_latency_ms": sync_latency,
                "yield_score": yield_score,
                "unit_count": 0,
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
    _ensure_hotel_profile_metadata(prop_id)
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
            "manual_override": bool(hotel.get("manual_override", False)),
            "name_source": hotel.get("name_source") or "generated_from_id",
            "original_generated_name": _hotel_generated_name(hotel, prop_id),
            "profile_badge": _profile_badge(hotel),
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
    detail["amenities"] = _amenities_payload_for_prop(prop_id)
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


def management_property_options(limit: int = 100) -> list[dict[str, Any]]:
    results = list_partner_hotels("", page=1, page_size=min(max(limit, 1), 100))
    return [
        {
            "prop_id": item["prop_id"],
            "display_name": item.get("display_name") or f"Hotel {item['prop_id']}",
        }
        for item in results["items"]
    ]


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
    ensure_hotel_content_collections()
    db = get_database()
    current = _content_page_for_prop(prop_id)
    clean_active: list[str] = []
    seen: set[str] = set()
    for item in active_amenities:
        label = _normalize_label(item)
        key = label.lower()
        if not label or key in seen:
            continue
        seen.add(key)
        clean_active.append(label)
    payload = {
        "prop_id": prop_id,
        "description": current.get("description") or "",
        "highlights": current.get("highlights") or "",
        "amenities_text": _clean_text(amenities_text) or ", ".join(clean_active),
        "active_amenities": clean_active,
        "amenities_catalog": [{"category": _amenity_category(label), "label": label} for label in clean_active],
        "source": current.get("source") or "partner_manual",
        "updated_at": _now(),
    }
    document = db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {"$set": payload, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    _register_content_change(prop_id, "hotel_content_pages", "upsert_amenities", payload, changed_by=changed_by)
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
    ensure_hotel_content_collections()
    db = get_database()
    payload = {
        "prop_id": prop_id,
        "check_in_time": _clean_text(check_in_time),
        "check_out_time": _clean_text(check_out_time),
        "cancellation_policy": _clean_text(cancellation_policy),
        "pet_policy": _clean_text(pet_policy),
        "children_policy": _clean_text(children_policy),
        "extra_bed_policy": _clean_text(extra_bed_policy),
        "payment_policy": _clean_text(payment_policy),
        "house_rules": _clean_text(house_rules),
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


def delete_partner_hotel_image(
    prop_id: int,
    *,
    image_url: str,
    changed_by: str = "angular_api",
) -> bool:
    db = get_database()
    result = db.hotel_images.delete_one({"prop_id": prop_id, "image_url": image_url})
    if result.deleted_count:
        _register_content_change(prop_id, "hotel_images", "delete", {"image_url": image_url}, changed_by=changed_by)
    return result.deleted_count > 0


def partner_hotel_edit_profile(prop_id: int) -> dict[str, Any] | None:
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    hotel = detail["hotel"]
    content_page = _content_page_for_prop(prop_id)
    policies = _policies_for_prop(prop_id)
    images = _images_for_prop(prop_id)
    amenities = _amenities_payload_for_prop(prop_id)
    return {
        "hotel": hotel,
        "profile": {
            **_profile_payload(hotel),
            "description": _clean_text(hotel.get("description")) or _clean_text(content_page.get("description")) or "",
        },
        "content_page": content_page,
        "policies": policies,
        "images": images[:20],
        "images_count": len(images),
        "amenities": amenities,
    }


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


def save_partner_hotel_profile(
    prop_id: int,
    *,
    hotel_name: str,
    display_name: str,
    description: str,
    display_country_label: str,
    changed_by: str = "angular_api",
    reason: str = "Actualización manual de perfil hotelero",
) -> dict[str, Any] | None:
    _ensure_hotel_profile_metadata(prop_id)
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    if hotel is None:
        return None

    clean_hotel_name = _clean_text(hotel_name) or _hotel_display_name(hotel, prop_id)
    clean_display_name = _clean_text(display_name) or clean_hotel_name or f"Hotel Partner {prop_id}"
    clean_description = _clean_text(description)
    clean_country_label = _clean_text(display_country_label) or (
        f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else ""
    )

    previous_values = {
        "hotel_name": _clean_text(hotel.get("hotel_name")),
        "display_name": _clean_text(hotel.get("display_name")) or _hotel_display_name(hotel, prop_id),
        "description": _clean_text(hotel.get("description")),
        "display_country_label": _clean_text(hotel.get("display_country_label")),
    }
    new_values = {
        "hotel_name": clean_hotel_name,
        "display_name": clean_display_name,
        "description": clean_description,
        "display_country_label": clean_country_label,
    }

    generated_name = _clean_text(hotel.get("original_generated_name"))
    if not generated_name:
        generated_name = _clean_text(hotel.get("display_name")) if hotel.get("demo_enriched") else ""
    if not generated_name:
        generated_name = _hotel_display_name(hotel, prop_id)

    db.dim_hotels.update_one(
        {"_id": hotel["_id"]},
        {
            "$set": {
                **new_values,
                "manual_override": True,
                "name_source": "manual",
                "updated_by": changed_by,
                "updated_at": _now(),
                "original_generated_name": generated_name,
            }
        },
    )

    ensure_hotel_content_collections()
    current_content = _content_page_for_prop(prop_id)
    db.hotel_content_pages.find_one_and_update(
        {"prop_id": prop_id},
        {
            "$set": {
                "prop_id": prop_id,
                "description": clean_description,
                "highlights": current_content.get("highlights") or "",
                "amenities_text": current_content.get("amenities_text") or "",
                "active_amenities": current_content.get("active_amenities", []),
                "amenities_catalog": current_content.get("amenities_catalog", []),
                "source": current_content.get("source") or "partner_manual",
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )

    changes = []
    changed_at = _now()
    for field, old_value in previous_values.items():
        new_value = new_values[field]
        if old_value == new_value:
            continue
        changes.append(
            {
                "prop_id": prop_id,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by,
                "changed_at": changed_at,
                "reason": reason,
                "source": "manual_profile_edit",
            }
        )
    if changes:
        db.hotel_profile_changes.insert_many(changes)

    return partner_hotel_profile(prop_id)


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


def _dashboard_quick_stats(db) -> dict[str, Any]:
    collection, _ = _active_fact_collection()
    now = _now()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_searches": {"$sum": 1},
                "total_reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "total_revenue": {"$sum": "$reservas_brutas_usd"},
            }
        },
    ]
    stats = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    total_searches = int(stats["total_searches"]) if stats else 0
    total_reservations = int(stats["total_reservations"]) if stats else 0
    occupancy_rate = round((total_reservations / total_searches) * 100, 1) if total_searches else 0.0
    year, month = now.year, now.month
    date_key_start = int(f"{year}{month:02d}01")
    next_m = month + 1
    next_y = year
    if next_m > 12:
        next_m = 1
        next_y += 1
    date_key_end = int(f"{next_y}{next_m:02d}01")
    mtd = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": date_key_start, "$lt": date_key_end}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$reservas_brutas_usd"}}},
    ], allowDiskUse=True), None)
    revenue_mtd = float(mtd["revenue"]) if mtd else 0.0
    prev_m = month - 1
    prev_y = year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    prev_start = int(f"{prev_y}{prev_m:02d}01")
    prev = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": prev_start, "$lt": date_key_start}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$reservas_brutas_usd"}}},
    ], allowDiskUse=True), None)
    revenue_prev = float(prev["revenue"]) if prev else 0.0
    revenue_trend = round(((revenue_mtd - revenue_prev) / revenue_prev * 100), 1) if revenue_prev else 0.0
    pending = 0
    try:
        pending = db.booking_orders.count_documents({
            "check_in_date": now.strftime("%Y-%m-%d"),
            "status": {"$in": ["confirmed", "pending"]},
        })
    except Exception:
        pass
    health = 95
    try:
        last = db.data_quality_reports.find_one(sort=[("executed_at", -1)], projection={"overall_score": 1, "_id": 0})
        if last and "overall_score" in last:
            health = int(last["overall_score"])
    except Exception:
        pass
    return {
        "occupancy_rate": occupancy_rate,
        "occupancy_trend": round(occupancy_rate * 0.048, 1),
        "total_revenue_mtd": round(revenue_mtd, 2),
        "revenue_trend": revenue_trend,
        "pending_checkins": pending,
        "data_health_score": health,
    }


def _dashboard_revenue_chart(db) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    results = list(collection.aggregate([
        {"$match": {"reserva_bool": True}},
        {"$group": {"_id": {"$floor": {"$divide": ["$date_key", 100]}}, "revenue": {"$sum": "$reservas_brutas_usd"}}},
        {"$sort": {"_id": 1}},
        {"$limit": 8},
    ], allowDiskUse=True))
    return [{"period": str(r["_id"]), "revenue": round(float(r["revenue"]), 2)} for r in results]


def _dashboard_arrivals_today(db) -> list[dict[str, Any]]:
    try:
        today = _now().strftime("%Y-%m-%d")
        rows = list(db.booking_orders.find({"check_in_date": today, "status": {"$in": ["confirmed", "pending"]}}, {"_id": 0}).limit(20))
        out = []
        for r in rows:
            name = r.get("guest_name", "Invitado")
            parts = name.strip().split()
            initials = "".join(p[0].upper() for p in parts[:2] if p) or "??"
            out.append({
                "guest_name": name,
                "initials": initials,
                "room_type": r.get("room_type", "Standard"),
                "nights": int(r.get("nights", 1) or 1),
                "arrival_time": r.get("arrival_time", "15:00"),
                "status_tag": r.get("booking_source", "standard"),
            })
        return out
    except Exception:
        return []


def _property_yield_score(performance: dict[str, Any]) -> int:
    searches = int(performance.get("searches", 0))
    reservations = int(performance.get("reservations", 0))
    conv = (reservations / searches * 100) if searches else 0
    review = float(performance.get("review_score") or 0)
    return min(round(60 + conv * 3.5 + review * 0.2), 100)


def properties_dashboard(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    quick_stats = _dashboard_quick_stats(db)
    revenue_chart = _dashboard_revenue_chart(db)
    arrivals = _dashboard_arrivals_today(db)
    props_list = list_partner_hotels(query, page=page, page_size=page_size)
    return {
        "quick_stats": quick_stats,
        "revenue_chart": revenue_chart,
        "arrivals_today": arrivals,
        "properties": props_list,
    }
