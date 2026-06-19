"""Properties sub-domain: hotel list, detail, performance and profile.

Owns the read-side of `dim_hotels` plus the fact-collection aggregations
that drive the partner dashboard's per-property view. Also owns
`save_partner_hotel_profile` (a write that touches both `dim_hotels` and
`hotel_content_pages.description`).
"""
from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import (
    active_fact_collection,
    clean_text,
    destination_display_name,
    hotel_display_name,
    now_utc,
    number,
    safe_int,
)
from src.database.connection import get_database


def _ensure_hotel_profile_metadata(prop_id: int | None = None) -> int:
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
        generated_name = clean_text(hotel.get("display_name"))
        if not generated_name:
            generated_name = hotel_display_name(hotel, prop_id_value)
        update_payload: dict[str, Any] = {
            "manual_override": bool(hotel.get("manual_override", False)),
            "name_source": hotel.get("name_source") or "generated_from_id",
        }
        if hotel.get("demo_enriched") and not clean_text(hotel.get("original_generated_name")):
            update_payload["original_generated_name"] = generated_name
        elif not clean_text(hotel.get("original_generated_name")):
            update_payload["original_generated_name"] = generated_name
        if update_payload:
            result = db.dim_hotels.update_one({"_id": hotel["_id"]}, {"$set": update_payload})
            modified += int(result.modified_count)
    return modified


def _profile_badge(hotel: dict[str, Any]) -> str:
    return "Nombre editado manualmente" if bool(hotel.get("manual_override")) else "Nombre generado"


def _profile_description(prop_id: int, hotel: dict[str, Any]) -> str:
    from src.app.modules.partner.services.content import content_page_for_prop

    content_page = content_page_for_prop(prop_id)
    return clean_text(hotel.get("description")) or clean_text(content_page.get("description")) or ""


def _profile_payload(hotel: dict[str, Any]) -> dict[str, Any]:
    prop_id = int(hotel.get("prop_id") or 0)
    return {
        "prop_id": prop_id,
        "hotel_name": clean_text(hotel.get("hotel_name")) or hotel_display_name(hotel, prop_id),
        "display_name": hotel_display_name(hotel, prop_id),
        "display_country_label": hotel.get("display_country_label")
        or (f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else ""),
        "original_generated_name": _hotel_generated_name(hotel, prop_id),
        "manual_override": bool(hotel.get("manual_override", False)),
        "name_source": hotel.get("name_source") or "generated_from_id",
        "profile_badge": _profile_badge(hotel),
        "updated_by": hotel.get("updated_by"),
        "updated_at": hotel.get("updated_at").isoformat() if hasattr(hotel.get("updated_at"), "isoformat") else hotel.get("updated_at"),
    }


def _hotel_generated_name(hotel: dict[str, Any], prop_id: int) -> str:
    return clean_text(hotel.get("original_generated_name")) or hotel_display_name(hotel, prop_id)


def _performance_for_prop(prop_id: int) -> dict[str, Any]:
    from src.app.modules.partner.services._common import money as _money

    collection, source_collection = active_fact_collection()
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
        "review_score_label": number(metrics.get("review_score")),
    }


def _property_yield_score(performance: dict[str, Any]) -> int:
    searches = int(performance.get("searches", 0))
    reservations = int(performance.get("reservations", 0))
    conv = (reservations / searches * 100) if searches else 0
    review = float(performance.get("review_score") or 0)
    return min(round(60 + conv * 3.5 + review * 0.2), 100)


def _build_fact_backed_hotel(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    sample = db.fact_hotel_reservations.find_one(
        {"prop_id": prop_id},
        {
            "_id": 0,
            "prop_id": 1,
            "prop_country_id": 1,
            "prop_starrating": 1,
            "prop_review_score": 1,
            "prop_brand_bool": 1,
            "prop_location_score1": 1,
        },
    )
    if sample is None:
        return None
    generated_name = f"Hotel Partner {prop_id}"
    return {
        "prop_id": prop_id,
        "hotel_name": "Hotel no especificado",
        "display_name": generated_name,
        "hotel_label": generated_name,
        "display_country_label": (
            f"Mercado hotelero {sample.get('prop_country_id')}"
            if sample.get("prop_country_id") is not None
            else ""
        ),
        "prop_country_id": sample.get("prop_country_id"),
        "prop_starrating": sample.get("prop_starrating"),
        "prop_review_score": sample.get("prop_review_score"),
        "prop_brand_bool": sample.get("prop_brand_bool"),
        "prop_location_score1": sample.get("prop_location_score1"),
        "manual_override": False,
        "name_source": "generated_from_id",
        "original_generated_name": generated_name,
        "description": "",
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


def _enriched_property_row(hotel: dict[str, Any] | None, prop_id: int) -> dict[str, Any]:
    base_hotel = hotel or _build_fact_backed_hotel(prop_id) or _synthetic_hotel(prop_id)
    performance = _performance_for_prop(prop_id)
    from src.app.modules.partner.services.dashboard import _operational_flags

    operational = _operational_flags(prop_id)
    country = base_hotel.get("display_country_label") or (
        f"Mercado hotelero {base_hotel.get('prop_country_id')}"
        if base_hotel.get("prop_country_id") is not None
        else "N/D"
    )
    yield_score = _property_yield_score(performance)
    status = "Operational" if yield_score >= 70 else ("Under Review" if yield_score >= 40 else "Maintenance")
    sync_status = "SYNC_ACTIVE"
    sync_latency = max(round(100 - yield_score * 0.8), 5)
    return {
        **base_hotel,
        "prop_id": prop_id,
        "display_name": hotel_display_name(base_hotel, prop_id),
        "country_display_name": country,
        "location": country,
        "review_score_label": number(base_hotel.get("prop_review_score")),
        "prop_starrating": base_hotel.get("prop_starrating"),
        "manual_override": bool(base_hotel.get("manual_override", False)),
        "profile_badge": _profile_badge(base_hotel),
        "status": status,
        "sync_status": sync_status,
        "sync_latency_ms": sync_latency,
        "yield_score": yield_score,
        "unit_count": operational["counts"]["hotel_rooms"],
        "performance": performance,
        "operational": operational,
    }


def list_partner_hotels(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    query = query.strip()
    query_as_id = safe_int(query)

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

    fact_prop_ids = set(db.fact_hotel_reservations.distinct("prop_id"))
    dim_hotels = list(db.dim_hotels.find({}, {"_id": 0}))
    dim_lookup = {int(item["prop_id"]): item for item in dim_hotels if item.get("prop_id") is not None}
    dim_prop_ids = set(dim_lookup.keys())
    all_prop_ids = sorted(fact_prop_ids | dim_prop_ids)

    if len(dim_prop_ids) < len(fact_prop_ids):
        filtered_ids = all_prop_ids
        if query:
            query_lower = query.lower()
            generic_hotel_terms = {"hotel", "hoteles", "partner", "hotel partner"}
            if query_lower in generic_hotel_terms:
                filtered_ids = all_prop_ids
            else:
                filtered_ids = []
                for prop_id in all_prop_ids:
                    hotel = dim_lookup.get(prop_id) or _build_fact_backed_hotel(prop_id) or {}
                    haystacks = [
                        hotel_display_name(hotel, prop_id),
                        clean_text(hotel.get("hotel_name")),
                        clean_text(hotel.get("hotel_label")),
                        clean_text(hotel.get("display_country_label")),
                    ]
                    if any(query_lower in value.lower() for value in haystacks if value):
                        filtered_ids.append(prop_id)
                    elif query_as_id is not None and prop_id == query_as_id:
                        filtered_ids.append(prop_id)

        total = len(filtered_ids)
        total_pages = (total + page_size - 1) // page_size if total else 0
        if total_pages and page > total_pages:
            page = total_pages
        page_ids = filtered_ids[(page - 1) * page_size: page * page_size]
        enriched = [_enriched_property_row(dim_lookup.get(prop_id), prop_id) for prop_id in page_ids]
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
            {"display_name": {"$regex": query, "$options": "i"}},
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
    enriched = [_enriched_property_row(item, int(item["prop_id"])) for item in items]
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
        hotel = _build_fact_backed_hotel(prop_id)
    if hotel is None:
        return None
    master_hotel = db.hotels.find_one({"hotel_code": {"$exists": True}}, {"_id": 0}) or {}
    performance = _performance_for_prop(prop_id)
    from src.app.modules.partner.services.dashboard import _operational_flags

    operational = _operational_flags(prop_id)
    return {
        "hotel": {
            **hotel,
            "prop_id": prop_id,
            "display_name": hotel_display_name(hotel, prop_id),
            "country_display_name": hotel.get("display_country_label") or (f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else "N/D"),
            "review_score_label": number(hotel.get("prop_review_score")),
            "manual_override": bool(hotel.get("manual_override", False)),
            "name_source": hotel.get("name_source") or "generated_from_id",
            "original_generated_name": _hotel_generated_name(hotel, prop_id),
            "profile_badge": _profile_badge(hotel),
            "operational": operational,
        },
        "performance": performance,
        "master_hotel": master_hotel,
    }


def partner_hotel_performance(prop_id: int) -> dict[str, Any] | None:
    from src.app.modules.partner.services._common import money as _money

    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None
    db = get_database()
    collection, _ = active_fact_collection()
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
            "destination_label": destination_display_name(destination_lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "searches": int(row.get("searches") or 0),
            "reservations": int(row.get("reservations") or 0),
            "avg_price_label": _money(row.get("avg_price")),
        }
        for row in top_destinations
        if row.get("_id") is not None
    ]
    return detail


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
    from src.app.modules.partner.services.content import content_page_for_prop, partner_hotel_profile

    _ensure_hotel_profile_metadata(prop_id)
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id})
    if hotel is None:
        fallback_hotel = _build_fact_backed_hotel(prop_id)
        if fallback_hotel is None:
            return None
        hotel = db.dim_hotels.find_one_and_update(
            {"prop_id": prop_id},
            {
                "$setOnInsert": {
                    **fallback_hotel,
                    "created_at": now_utc(),
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if hotel is None:
            return None

    clean_hotel_name = clean_text(hotel_name) or hotel_display_name(hotel, prop_id)
    clean_display_name = clean_text(display_name) or clean_hotel_name or f"Hotel Partner {prop_id}"
    clean_description = clean_text(description)
    clean_country_label = clean_text(display_country_label) or (
        f"Mercado hotelero {hotel.get('prop_country_id')}" if hotel.get("prop_country_id") is not None else ""
    )

    previous_values = {
        "hotel_name": clean_text(hotel.get("hotel_name")),
        "display_name": clean_text(hotel.get("display_name")) or hotel_display_name(hotel, prop_id),
        "description": clean_text(hotel.get("description")),
        "display_country_label": clean_text(hotel.get("display_country_label")),
    }
    new_values = {
        "hotel_name": clean_hotel_name,
        "display_name": clean_display_name,
        "description": clean_description,
        "display_country_label": clean_country_label,
    }

    generated_name = clean_text(hotel.get("original_generated_name"))
    if not generated_name:
        generated_name = clean_text(hotel.get("display_name")) if hotel.get("demo_enriched") else ""
    if not generated_name:
        generated_name = hotel_display_name(hotel, prop_id)

    db.dim_hotels.update_one(
        {"_id": hotel["_id"]},
        {
            "$set": {
                **new_values,
                "manual_override": True,
                "name_source": "manual",
                "updated_by": changed_by,
                "updated_at": now_utc(),
                "original_generated_name": generated_name,
            }
        },
    )

    current_content = content_page_for_prop(prop_id)
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
                "updated_at": now_utc(),
            },
            "$setOnInsert": {"created_at": now_utc()},
        },
        upsert=True,
    )

    changes = []
    changed_at = now_utc()
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
