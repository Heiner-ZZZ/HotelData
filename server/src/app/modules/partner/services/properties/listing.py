from __future__ import annotations

import os
from typing import Any

from src.app.modules.partner.services._common import clean_text, hotel_display_name, safe_int
from src.app.modules.partner.services.properties.builders import (
    build_fact_backed_hotel,
    enriched_property_row,
    synthetic_hotel,
)
from src.cache.cache_service import get_cache, set_cache
from src.app.security.hotel_filter import hotel_filter_from_user
from src.database.connection import get_database


def _cache_enabled() -> bool:
    """Skip Redis caching on the isolated test DB.

    The pytest conftest wipes the Mongo collections per test but does NOT
    flush Redis — caching the catalog there would serve stale seeds from one
    test to the next (a test seeding 2 hotels could read a cache holding 3
    from a previous test). The guard keeps prod/dev caching fully on while
    tests always exercise the real query path.
    """
    return os.environ.get("MONGO_DATABASE", "") != "hoteldata_hub_test"


def _paginate(page: int, page_size: int, total: int) -> dict[str, Any]:
    total_pages = (total + page_size - 1) // page_size if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
        "start_index": ((page - 1) * page_size) + 1 if total else 0,
        "end_index": 0,
    }


def _options_cache_key(query: str, page: int, page_size: int, user: dict[str, Any] | None) -> str:
    """Cache key that includes the user's hotel scope.

    The scope (``hotel_filter_from_user``) decides WHICH prop_ids a user may
    see; caching under a key without it would leak hotels between restricted
    roles. Unfiltered roles (super_admin) get ``{}`` → stable key shared by
    all of them (safe: they all see the full catalog).
    """
    scope = hotel_filter_from_user(user)
    # ``{}`` (no "prop_id") → unfiltered scope (super_admin/admin_sistema) —
    # key literal "all". Any "prop_id" filter (even empty $in = deny-by-
    # default) gets its own key, so a restricted role can never read the
    # unfiltered cache or vice versa.
    if "prop_id" in scope:
        scope_part = "ids:" + "|".join(str(p) for p in sorted(scope["prop_id"].get("$in", [])))
    else:
        scope_part = "all"
    return f"partner:property:options:{scope_part}:{query}:{page}:{page_size}"


def list_property_options(query: str = "", page: int = 1, page_size: int = 20, user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Lightweight property list for selector/options endpoints.

    The property-selector and ``rooms/options`` only need ``prop_id`` +
    ``display_name`` per hotel. ``list_partner_hotels`` enriches EVERY row
    with ``performance_for_prop`` (aggregates over the 800K-doc fact
    collection) + ``_operational_flags`` (6 counts) — seconds of latency for
    page sizes of 10-200. This path resolves the same prop_ids (same scope +
    query semantics) but builds light rows from ``dim_hotels`` only.

    Returns the same envelope as ``list_partner_hotels`` so consumers keep
    the same pagination contract. Cached in Redis for 30s (key scoped by the
    user's hotel filter) because the catalog scan (distinct over the fact
    collection + full dim_hotels read) is the dominant cost once the heavy
    per-hotel enrichment is gone.
    """
    cache_key = _options_cache_key(query, page, page_size, user)
    if _cache_enabled():
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    query = query.strip()
    query_as_id = safe_int(query)
    user_filter = hotel_filter_from_user(user)
    allowed_ids: set[int] | None = None

    if "prop_id" in user_filter:
        allowed_ids = set(int(p) for p in user_filter["prop_id"]["$in"])

    has_dim = db.dim_hotels.estimated_document_count() > 0
    if not has_dim:
        all_ids = db.fact_hotel_reservations.distinct("prop_id")
        all_ids.sort()
        if allowed_ids is not None:
            all_ids = [pid for pid in all_ids if pid in allowed_ids]
        if query_as_id is not None:
            all_ids = [pid for pid in all_ids if pid == query_as_id]
        total = len(all_ids)
        result = _paginate(page, page_size, total)
        page_ids = all_ids[(result["page"] - 1) * page_size: result["page"] * page_size]
        result["items"] = [{"prop_id": pid, "display_name": f"Hotel {pid}"} for pid in page_ids]
        result["query"] = query
        result["start_index"] = (result["page"] - 1) * page_size + 1 if total else 0
        result["end_index"] = min(result["page"] * page_size, total)
        if _cache_enabled():
            set_cache(cache_key, result, ttl_seconds=30)
        return result

    fact_prop_ids = set(db.fact_hotel_reservations.distinct("prop_id"))
    dim_hotels = list(db.dim_hotels.find({}, {"_id": 0}))
    dim_lookup = {int(item["prop_id"]): item for item in dim_hotels if item.get("prop_id") is not None}
    dim_prop_ids = set(dim_lookup.keys())
    all_prop_ids = sorted(fact_prop_ids | dim_prop_ids)
    if allowed_ids is not None:
        all_prop_ids = [pid for pid in all_prop_ids if pid in allowed_ids]

    if len(dim_prop_ids) < len(fact_prop_ids):
        filtered_ids = all_prop_ids
        if query:
            query_lower = query.lower()
            generic_hotel_terms = {"hotel", "hoteles", "partner", "hotel partner"}
            if query_lower not in generic_hotel_terms:
                filtered_ids = []
                for prop_id in all_prop_ids:
                    hotel = dim_lookup.get(prop_id) or {}
                    haystacks = [
                        hotel_display_name(hotel, prop_id),
                        clean_text(hotel.get("hotel_name")),
                        clean_text(hotel.get("display_country_label")),
                    ]
                    if any(query_lower in value.lower() for value in haystacks if value):
                        filtered_ids.append(prop_id)
                    elif query_as_id is not None and prop_id == query_as_id:
                        filtered_ids.append(prop_id)

        total = len(filtered_ids)
        result = _paginate(page, page_size, total)
        page_ids = filtered_ids[(result["page"] - 1) * page_size: result["page"] * page_size]
        result["items"] = [
            {
                "prop_id": prop_id,
                "display_name": hotel_display_name(dim_lookup.get(prop_id) or {}, prop_id)
                if dim_lookup.get(prop_id)
                else f"Hotel {prop_id}",
            }
            for prop_id in page_ids
        ]
        result["query"] = query
        result["start_index"] = (result["page"] - 1) * page_size + 1 if total else 0
        result["end_index"] = min(result["page"] * page_size, total)
        if _cache_enabled():
            set_cache(cache_key, result, ttl_seconds=30)
        return result

    filters: dict[str, Any] = {}
    if user_filter:
        filters.update(user_filter)
    if query:
        query_or = [
            {"display_name": {"$regex": query, "$options": "i"}},
            {"hotel_name": {"$regex": query, "$options": "i"}},
        ]
        if query_as_id is not None:
            query_or.append({"prop_id": query_as_id})
        if user_filter:
            filters = {"$and": [user_filter, {"$or": query_or}]}
        else:
            filters["$or"] = query_or

    total = db.dim_hotels.count_documents(filters)
    result = _paginate(page, page_size, total)
    cursor = (
        db.dim_hotels.find(filters, {"_id": 0, "prop_id": 1, "hotel_name": 1, "display_name": 1})
        .sort([("prop_id", 1)])
        .skip((result["page"] - 1) * page_size)
        .limit(page_size)
    )
    items = list(cursor)
    result["items"] = [
        {
            "prop_id": int(item["prop_id"]),
            "display_name": hotel_display_name(item, int(item["prop_id"])),
        }
        for item in items
    ]
    result["query"] = query
    result["start_index"] = ((result["page"] - 1) * page_size) + 1 if total else 0
    result["end_index"] = ((result["page"] - 1) * page_size) + len(result["items"]) if result["items"] else 0

    if _cache_enabled():
        set_cache(cache_key, result, ttl_seconds=30)
    return result


def list_partner_hotels(query: str = "", page: int = 1, page_size: int = 20, user: dict[str, Any] | None = None) -> dict[str, Any]:
    # Cache common queries (empty query, page 1) for 30 seconds. Key is scoped
    # by the user's hotel filter so a restricted role can never read the
    # unfiltered (super_admin) cache or vice versa. Enriched rows contain
    # KPI-ish aggregates, so the TTL stays short (30s) — same as the legacy
    # anonymous default cache, now also covering authenticated dashboards.
    cache_key = _options_cache_key(query, page, page_size, user)
    if _cache_enabled() and not query.strip() and page == 1 and page_size <= 20:
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    query = query.strip()
    query_as_id = safe_int(query)
    user_filter = hotel_filter_from_user(user)
    allowed_ids: set[int] | None = None

    # If user has assigned_hotels, resolve the set immediately for in-memory filtering
    if "prop_id" in user_filter:
        allowed_ids = set(int(p) for p in user_filter["prop_id"]["$in"])

    has_dim = db.dim_hotels.estimated_document_count() > 0
    if not has_dim:
        all_ids = db.fact_hotel_reservations.distinct("prop_id")
        all_ids.sort()
        # Apply user filter
        if allowed_ids is not None:
            all_ids = [pid for pid in all_ids if pid in allowed_ids]
        if query_as_id is not None:
            all_ids = [pid for pid in all_ids if pid == query_as_id]
        total = len(all_ids)
        result = _paginate(page, page_size, total)
        page_ids = all_ids[(result["page"] - 1) * page_size: result["page"] * page_size]
        enriched = [synthetic_hotel(pid) for pid in page_ids]
        result["items"] = enriched
        result["query"] = query
        result["start_index"] = (result["page"] - 1) * page_size + 1 if total else 0
        result["end_index"] = min(result["page"] * page_size, total)
        return result

    fact_prop_ids = set(db.fact_hotel_reservations.distinct("prop_id"))
    dim_hotels = list(db.dim_hotels.find({}, {"_id": 0}))
    dim_lookup = {int(item["prop_id"]): item for item in dim_hotels if item.get("prop_id") is not None}
    dim_prop_ids = set(dim_lookup.keys())
    all_prop_ids = sorted(fact_prop_ids | dim_prop_ids)
    # Apply user filter
    if allowed_ids is not None:
        all_prop_ids = [pid for pid in all_prop_ids if pid in allowed_ids]

    if len(dim_prop_ids) < len(fact_prop_ids):
        filtered_ids = all_prop_ids
        if query:
            query_lower = query.lower()
            generic_hotel_terms = {"hotel", "hoteles", "partner", "hotel partner"}
            if query_lower not in generic_hotel_terms:
                filtered_ids = []
                for prop_id in all_prop_ids:
                    hotel = dim_lookup.get(prop_id) or build_fact_backed_hotel(prop_id) or {}
                    haystacks = [
                        hotel_display_name(hotel, prop_id),
                        clean_text(hotel.get("hotel_name")),
                        clean_text(hotel.get("display_country_label")),
                    ]
                    if any(query_lower in value.lower() for value in haystacks if value):
                        filtered_ids.append(prop_id)
                    elif query_as_id is not None and prop_id == query_as_id:
                        filtered_ids.append(prop_id)

        total = len(filtered_ids)
        result = _paginate(page, page_size, total)
        page_ids = filtered_ids[(result["page"] - 1) * page_size: result["page"] * page_size]
        result["items"] = [enriched_property_row(dim_lookup.get(prop_id), prop_id) for prop_id in page_ids]
        result["query"] = query
        result["start_index"] = (result["page"] - 1) * page_size + 1 if total else 0
        result["end_index"] = min(result["page"] * page_size, total)
        return result

    filters: dict[str, Any] = {}
    # Apply user hotel filter as base
    if user_filter:
        filters.update(user_filter)
    if query:
        # Combine query with user filter using $and if user_filter exists
        query_or = [
            {"display_name": {"$regex": query, "$options": "i"}},
            {"hotel_name": {"$regex": query, "$options": "i"}},
        ]
        if query_as_id is not None:
            query_or.append({"prop_id": query_as_id})
        if user_filter:
            filters = {"$and": [user_filter, {"$or": query_or}]}
        else:
            filters["$or"] = query_or

    total = db.dim_hotels.count_documents(filters)
    result = _paginate(page, page_size, total)
    cursor = (
        db.dim_hotels.find(filters, {"_id": 0})
        .sort([("prop_id", 1)])
        .skip((result["page"] - 1) * page_size)
        .limit(page_size)
    )
    items = list(cursor)
    result["items"] = [enriched_property_row(item, int(item["prop_id"])) for item in items]
    result["query"] = query
    result["start_index"] = ((result["page"] - 1) * page_size) + 1 if total else 0
    result["end_index"] = ((result["page"] - 1) * page_size) + len(result["items"]) if result["items"] else 0

    # Cache default (no query, page 1) for 30 seconds, scoped by hotel filter
    if _cache_enabled() and not query and page == 1 and page_size <= 20:
        set_cache(cache_key, result, ttl_seconds=30)

    return result
