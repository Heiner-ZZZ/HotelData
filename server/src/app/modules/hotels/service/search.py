from __future__ import annotations

from math import ceil
from typing import Any

from src.database.connection import get_database

from ._helpers import (
    _active_fact_collection,
    _country_display_name,
    _destination_display_name,
    _empty_search,
    _format_money,
    _format_number,
    _hotel_display_name,
    _metric_projection,
)
from .lookups import (
    _build_match,
    _country_lookup,
    _destination_lookup,
    _geo_country_lookup,
    _hotel_lookup,
)
from .operational import published_prop_ids


def _enrich_hotel_metrics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hotel_lookup = _hotel_lookup([int(item["prop_id"]) for item in items if item.get("prop_id") is not None])

    # Collect country keys from hotels (both legacy int and geo string)
    legacy_country_ids: list[int] = []
    geo_country_codes: list[str] = []
    for hotel in hotel_lookup.values():
        geo_code = hotel.get("geo_country_code")
        if geo_code:
            geo_country_codes.append(geo_code)
            continue
        cid = hotel.get("prop_country_id")
        if cid is not None:
            legacy_country_ids.append(int(cid))

    country_lookup = _country_lookup(legacy_country_ids)
    geo_lookup = _geo_country_lookup(geo_country_codes)

    destination_ids = sorted(
        {
            int(destination_id)
            for item in items
            for destination_id in item.get("destinations", [])
            if destination_id is not None
        }
    )
    destination_lookup = _destination_lookup(destination_ids)
    enriched: list[dict[str, Any]] = []
    for item in items:
        prop_id = int(item["prop_id"])
        hotel = hotel_lookup.get(prop_id, {})

        # Resolve country info preferring geo_country_code
        geo_code = hotel.get("geo_country_code")
        if geo_code:
            country_key = geo_code
            country = geo_lookup.get(geo_code, {})
        else:
            country_id = hotel.get("prop_country_id") or item.get("prop_country_id")
            country_key = int(country_id) if country_id is not None else None
            country = country_lookup.get(country_key, {}) if country_key is not None else {}

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
                "hotel_display_label": hotel_label,
                "prop_country_id": country_key,
                "geo_country_code": geo_code or None,
                "country_display_name": _country_display_name(country, country_key) if country_key is not None else "N/D",
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

    # Gate operativo (Fase A): excluir hoteles pendientes de aprobación
    # (published=false) de la búsqueda pública. Los legados sin el campo
    # quedan incluidos (published_prop_ids usa `$ne: False`).
    published_ids = published_prop_ids(get_database())
    if not published_ids:
        return _empty_search(filters, page_size, source_collection)
    match["prop_id"] = {"$in": published_ids}

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
        # Keep the search envelope stable for non-empty pages too. The Angular
        # mapper treats this as a canonical array, including when no
        # alternatives are available.
        "alternative_destinations": [],
        "start_index": ((page - 1) * page_size) + 1 if total else 0,
        "end_index": ((page - 1) * page_size) + len(items) if items else 0,
    }


def search_hotels(filters: dict[str, Any], page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return get_hotel_search_cards(filters, page=page, page_size=page_size)
