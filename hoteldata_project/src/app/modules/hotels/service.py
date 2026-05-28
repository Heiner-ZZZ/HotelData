from __future__ import annotations

from math import ceil
from typing import Any

from pymongo.collection import Collection

from src.app.modules.hotels.schemas import ModuleStatus
from src.database.connection import get_database


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="hotels",
        status="partial",
        description="Modulo cliente/viajero inicial con busqueda, detalle y comparacion analitica de hoteles.",
    )


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _active_fact_collection() -> tuple[Collection, str]:
    db = get_database()
    if db.fact_hotel_reservations.estimated_document_count() > 0:
        return db.fact_hotel_reservations, "fact_hotel_reservations"
    return db.fact_hotel_events, "fact_hotel_events"


def _metric_projection() -> dict[str, Any]:
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    promoted = {"$or": [{"$eq": ["$promotion_flag", 1]}, {"$eq": ["$promotion_flag", True]}]}
    return {
        "events": {"$sum": 1},
        "reservations": {"$sum": {"$cond": [booked, 1, 0]}},
        "clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
        "promotions": {"$sum": {"$cond": [promoted, 1, 0]}},
        "avg_price": {"$avg": "$price_usd"},
        "min_price": {"$min": "$price_usd"},
        "max_price": {"$max": "$price_usd"},
        "gross_revenue": {"$sum": "$reservas_brutas_usd"},
        "prop_starrating": {"$max": "$prop_starrating"},
        "prop_review_score": {"$avg": "$prop_review_score"},
        "prop_country_id": {"$first": "$prop_country_id"},
        "destinations": {"$addToSet": "$srch_destination_id"},
    }


def _format_money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.2f}"


def _format_number(value: Any, decimals: int = 1) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.{decimals}f}"


def _destination_ids(destination: str) -> list[int]:
    destination_id = _safe_int(destination)
    if destination_id is not None:
        return [destination_id]
    if not destination:
        return []
    db = get_database()
    docs = db.dim_destinations.find(
        {
            "$or": [
                {"destination_display_name": {"$regex": destination, "$options": "i"}},
                {"destination_label": {"$regex": destination, "$options": "i"}},
                {"destination_name": {"$regex": destination, "$options": "i"}},
            ]
        },
        {"_id": 0, "srch_destination_id": 1},
    ).limit(200)
    return [int(item["srch_destination_id"]) for item in docs if item.get("srch_destination_id") is not None]


def _hotel_lookup(prop_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not prop_ids:
        return {}
    db = get_database()
    docs = db.dim_hotels.find({"prop_id": {"$in": prop_ids}}, {"_id": 0})
    return {int(item["prop_id"]): item for item in docs if item.get("prop_id") is not None}


def _destination_lookup(destination_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not destination_ids:
        return {}
    db = get_database()
    docs = db.dim_destinations.find({"srch_destination_id": {"$in": destination_ids}}, {"_id": 0})
    return {int(item["srch_destination_id"]): item for item in docs if item.get("srch_destination_id") is not None}


def _country_lookup(country_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not country_ids:
        return {}
    db = get_database()
    docs = db.dim_visitor_countries.find({"visitor_location_country_id": {"$in": country_ids}}, {"_id": 0})
    return {int(item["visitor_location_country_id"]): item for item in docs if item.get("visitor_location_country_id") is not None}


def _site_lookup(site_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not site_ids:
        return {}
    db = get_database()
    docs = db.dim_sites.find({"site_id": {"$in": site_ids}}, {"_id": 0})
    return {int(item["site_id"]): item for item in docs if item.get("site_id") is not None}


def _hotel_display_name(hotel: dict[str, Any], prop_id: int) -> str:
    return hotel.get("display_name") or hotel.get("hotel_name") or hotel.get("hotel_label") or f"Hotel Partner {prop_id}"


def _destination_display_name(destination: dict[str, Any], destination_id: int) -> str:
    return destination.get("destination_display_name") or destination.get("destination_name") or destination.get("destination_label") or f"Destino {destination_id}"


def _country_display_name(country: dict[str, Any], country_id: int) -> str:
    return country.get("country_display_name") or country.get("country_name") or country.get("visitor_country_label") or f"Mercado visitante {country_id}"


def _site_display_name(site: dict[str, Any], site_id: int) -> str:
    return site.get("site_display_name") or site.get("site_name") or site.get("site_label") or f"Canal Expedia {site_id}"


def _build_match(filters: dict[str, Any]) -> dict[str, Any] | None:
    match: dict[str, Any] = {}
    destination = str(filters.get("destination") or "").strip()
    destination_ids = _destination_ids(destination)
    if destination:
        if not destination_ids:
            return None
        match["srch_destination_id"] = {"$in": destination_ids}

    min_price = _safe_float(filters.get("min_price"))
    max_price = _safe_float(filters.get("max_price"))
    price_filter: dict[str, Any] = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        match["price_usd"] = price_filter

    min_stars = _safe_float(filters.get("min_stars"))
    if min_stars is not None:
        match["prop_starrating"] = {"$gte": min_stars}

    promotion = str(filters.get("promotion") or "").strip()
    if promotion == "yes":
        match["promotion_flag"] = {"$in": [1, True]}
    elif promotion == "no":
        match["promotion_flag"] = {"$in": [0, False]}

    adults = _safe_int(filters.get("adults"))
    children = _safe_int(filters.get("children"))
    rooms = _safe_int(filters.get("rooms"))
    if adults is not None:
        match["srch_adults_count"] = {"$gte": adults}
    if children is not None:
        match["srch_children_count"] = {"$gte": children}
    if rooms is not None:
        match["srch_room_count"] = {"$gte": rooms}
    return match


def _enrich_hotel_metrics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hotel_lookup = _hotel_lookup([int(item["prop_id"]) for item in items if item.get("prop_id") is not None])
    country_ids = sorted(
        {
            int(hotel.get("prop_country_id"))
            for hotel in hotel_lookup.values()
            if hotel.get("prop_country_id") is not None
        }
    )
    destination_ids = sorted(
        {
            int(destination_id)
            for item in items
            for destination_id in item.get("destinations", [])
            if destination_id is not None
        }
    )
    country_lookup = _country_lookup(country_ids)
    destination_lookup = _destination_lookup(destination_ids)
    enriched: list[dict[str, Any]] = []
    for item in items:
        prop_id = int(item["prop_id"])
        hotel = hotel_lookup.get(prop_id, {})
        country_id = hotel.get("prop_country_id") or item.get("prop_country_id")
        country = country_lookup.get(int(country_id), {}) if country_id is not None else {}
        destination_labels = [
            _destination_display_name(destination_lookup.get(int(destination_id), {}), int(destination_id))
            for destination_id in item.get("destinations", [])[:3]
            if destination_id is not None
        ]
        hotel_label = _hotel_display_name(hotel, prop_id)
        events = int(item.get("events") or 0)
        reservations = int(item.get("reservations") or 0)
        clicks = int(item.get("clicks") or 0)
        enriched.append(
            {
                **item,
                "prop_id": prop_id,
                "hotel_label": hotel_label,
                "hotel_display_label": hotel.get("display_label") or hotel_label,
                "prop_country_id": country_id,
                "country_display_name": _country_display_name(country, int(country_id)) if country_id is not None else "N/D",
                "prop_starrating": hotel.get("prop_starrating") or item.get("prop_starrating"),
                "prop_review_score": hotel.get("prop_review_score") or item.get("prop_review_score"),
                "destination_labels": destination_labels,
                "avg_price_label": _format_money(item.get("avg_price")),
                "gross_revenue_label": _format_money(item.get("gross_revenue")),
                "review_label": _format_number(hotel.get("prop_review_score") or item.get("prop_review_score")),
                "conversion_rate": round((reservations / events) * 100, 2) if events else 0.0,
                "click_rate": round((clicks / events) * 100, 2) if events else 0.0,
                "has_promotion": int(item.get("promotions") or 0) > 0,
            }
        )
    return enriched


def get_hotel_search_cards(filters: dict[str, Any], page: int = 1, page_size: int = 20) -> dict[str, Any]:
    collection, source_collection = _active_fact_collection()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    match = _build_match(filters)
    if match is None:
        return _empty_search(filters, page_size, source_collection)

    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {"$group": {"_id": "$prop_id", "prop_id": {"$first": "$prop_id"}, **_metric_projection()}},
        {"$sort": {"reservations": -1, "clicks": -1, "events": -1, "prop_id": 1}},
        {
            "$facet": {
                "metadata": [{"$count": "total"}],
                "items": [{"$skip": (page - 1) * page_size}, {"$limit": page_size}],
            }
        },
    ]
    result = next(collection.aggregate(pipeline, allowDiskUse=True), {"metadata": [], "items": []})
    total = int(result["metadata"][0]["total"]) if result.get("metadata") else 0
    total_pages = ceil(total / page_size) if total else 0
    if total_pages and page > total_pages:
        return get_hotel_search_cards(filters, page=total_pages, page_size=page_size)

    items = _enrich_hotel_metrics(result.get("items", []))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
        "source_collection": source_collection,
        "filters": filters,
        "start_index": ((page - 1) * page_size) + 1 if total else 0,
        "end_index": ((page - 1) * page_size) + len(items) if items else 0,
    }


def top_destinations_for_hotel(prop_id: int, limit: int = 8) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {"$group": {"_id": "$srch_destination_id", "events": {"$sum": 1}, "avg_price": {"$avg": "$price_usd"}}},
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _destination_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "srch_destination_id": int(row["_id"]),
            "destination_label": _destination_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "avg_price_label": _format_money(row.get("avg_price")),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _top_visitor_countries_for_hotel(prop_id: int, limit: int = 6) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$visitor_location_country_id",
                "events": {"$sum": 1},
                "reservations": {"$sum": {"$cond": [{"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _country_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "visitor_location_country_id": int(row["_id"]),
            "country_label": _country_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "reservations": int(row.get("reservations") or 0),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _top_sites_for_hotel(prop_id: int, limit: int = 6) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$site_id",
                "events": {"$sum": 1},
                "clicks": {"$sum": {"$cond": [{"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}, 1, 0]}},
                "reservations": {"$sum": {"$cond": [{"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _site_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "site_id": int(row["_id"]),
            "site_label": _site_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "clicks": int(row.get("clicks") or 0),
            "reservations": int(row.get("reservations") or 0),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _hotel_rates_for_detail(prop_id: int, limit: int = 12) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("rate_plan_id", 1)])
        .limit(limit)
    )
    return [{**item, "rate_amount_label": _format_money(item.get("rate_amount"))} for item in items]


def _room_types_for_detail(prop_id: int, limit: int = 12) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.room_types.find(
            {"prop_id": prop_id},
            {"_id": 0, "room_type_id": 1, "name": 1, "base_capacity": 1, "max_adults": 1, "max_children": 1, "is_active": 1},
        )
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )


def _hotel_policies_for_detail(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    return db.hotel_policies.find_one({"prop_id": prop_id}, {"_id": 0})


def get_hotel_detail_view(prop_id: int) -> dict[str, Any] | None:
    collection, source_collection = _active_fact_collection()
    hotel = get_database().dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0}) or {}
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {"$group": {"_id": "$prop_id", "prop_id": {"$first": "$prop_id"}, **_metric_projection()}},
    ]
    metrics = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    if not hotel and not metrics:
        return None

    item = _enrich_hotel_metrics([metrics or {"prop_id": prop_id, "events": 0, "reservations": 0, "clicks": 0, "destinations": []}])[0]
    item["source_collection"] = source_collection
    item["hotel"] = hotel
    item["top_destinations"] = top_destinations_for_hotel(prop_id)
    item["top_visitor_countries"] = _top_visitor_countries_for_hotel(prop_id)
    item["top_sites"] = _top_sites_for_hotel(prop_id)
    item["hotel_rates"] = _hotel_rates_for_detail(prop_id)
    item["room_types"] = _room_types_for_detail(prop_id)
    item["hotel_policies"] = _hotel_policies_for_detail(prop_id)
    return item


def compare_hotel_options(limit: int = 120) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$group": {"_id": "$prop_id", "events": {"$sum": 1}, "reservations": {"$sum": {"$cond": [{"$in": ["$reserva_bool", [1, True]]}, 1, 0]}}}},
        {"$sort": {"reservations": -1, "events": -1, "_id": 1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    prop_ids = [int(row["_id"]) for row in rows if row.get("_id") is not None]
    hotel_lookup = _hotel_lookup(prop_ids)
    options: list[dict[str, Any]] = []
    for row in rows:
        prop_id = row.get("_id")
        if prop_id is None:
            continue
        prop_id = int(prop_id)
        hotel = hotel_lookup.get(prop_id, {})
        hotel_label = _hotel_display_name(hotel, prop_id)
        stars = hotel.get("prop_starrating")
        review = hotel.get("prop_review_score")
        label_parts = [hotel_label, f"Prop {prop_id}"]
        if stars is not None:
            label_parts.append(f"{_format_number(stars)} estrellas")
        if review is not None:
            label_parts.append(f"Score {_format_number(review)}")
        options.append(
            {
                "prop_id": prop_id,
                "label": " | ".join(label_parts),
                "hotel_label": hotel_label,
                "reservations": int(row.get("reservations") or 0),
                "events": int(row.get("events") or 0),
            }
        )
    return options


def compare_hotels(prop_ids: list[int]) -> dict[str, Any]:
    unique_ids = list(dict.fromkeys([prop_id for prop_id in prop_ids if prop_id is not None]))[:3]
    if not unique_ids:
        return {"items": [], "requested_ids": [], "source_collection": _active_fact_collection()[1]}
    collection, source_collection = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": {"$in": unique_ids}}},
        {"$group": {"_id": "$prop_id", "prop_id": {"$first": "$prop_id"}, **_metric_projection()}},
        {"$sort": {"prop_id": 1}},
    ]
    items = _enrich_hotel_metrics(list(collection.aggregate(pipeline, allowDiskUse=True)))
    found_ids = {item["prop_id"] for item in items}
    for missing_id in unique_ids:
        if missing_id not in found_ids:
            detail = get_hotel_detail_view(missing_id)
            if detail:
                items.append(detail)
    items.sort(key=lambda item: item["prop_id"])
    return {"items": items[:3], "requested_ids": unique_ids, "source_collection": source_collection}


def search_hotels(filters: dict[str, Any], page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return get_hotel_search_cards(filters, page=page, page_size=page_size)


def hotel_detail(prop_id: int) -> dict[str, Any] | None:
    return get_hotel_detail_view(prop_id)


def _empty_search(filters: dict[str, Any], page_size: int, source_collection: str) -> dict[str, Any]:
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": page_size,
        "total_pages": 0,
        "has_prev": False,
        "has_next": False,
        "source_collection": source_collection,
        "filters": filters,
        "start_index": 0,
        "end_index": 0,
    }
