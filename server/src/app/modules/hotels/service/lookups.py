from __future__ import annotations

from typing import Any

from src.app.modules.hotels.service._helpers import _safe_float, _safe_int
from src.database.connection import get_database


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
                {"destination_name": {"$regex": destination, "$options": "i"}},
            ]
        },
        {"_id": 0, "srch_destination_id": 1},
    ).limit(200)
    return [int(item["srch_destination_id"]) for item in docs if item.get("srch_destination_id") is not None]


def suggest_destinations(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Public destination suggestions for the welcome booking-bar autocomplete.

    Case-insensitive substring match over ``dim_destinations.destination_name``.
    Returns up to ``limit`` suggestions with ``id`` (srch_destination_id) and
    ``name`` (destination_name). No auth required — same surface as
    ``/api/hotels/availability``.
    """
    q = (query or "").strip()
    if not q:
        return []
    db = get_database()
    limit = min(max(int(limit), 1), 20)
    docs = db.dim_destinations.find(
        {"destination_name": {"$regex": q, "$options": "i"}},
        {"_id": 0, "srch_destination_id": 1, "destination_name": 1},
    ).sort("destination_name", 1).limit(limit)
    return [
        {
            "id": int(doc["srch_destination_id"]),
            "name": doc.get("destination_name") or f"Destino {doc['srch_destination_id']}",
        }
        for doc in docs
        if doc.get("srch_destination_id") is not None
    ]


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


def _geo_country_lookup(country_codes: list[str]) -> dict[str, dict[str, Any]]:
    """Resolve geo_catalog country codes to their geo_catalog documents."""
    if not country_codes:
        return {}
    db = get_database()
    docs = db.geo_catalog.find(
        {"type": "country", "code": {"$in": country_codes}},
        {"_id": 1, "code": 1, "name": 1},
    )
    return {item["code"]: item for item in docs if item.get("code")}


def _site_lookup(site_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not site_ids:
        return {}
    db = get_database()
    docs = db.dim_sites.find({"site_id": {"$in": site_ids}}, {"_id": 0})
    return {int(item["site_id"]): item for item in docs if item.get("site_id") is not None}


def _suggest_alternative_destinations(
    destination: str,
    exclude_ids: list[int] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Suggest alternative destinations when search yields no results.

    Strategy: find destinations whose name shares at least one word with the
    searched destination, or has a similar prefix. Excludes the searched IDs.
    Returns up to `limit` suggestions with id and display name.
    """
    if not destination:
        return []
    words = [w for w in destination.strip().lower().split() if len(w) > 2]
    if not words:
        return []

    db = get_database()
    terms = [{"destination_name": {"$regex": w, "$options": "i"}} for w in words]

    match: dict[str, Any] = {"$or": terms}
    if exclude_ids:
        match["srch_destination_id"] = {"$nin": exclude_ids}

    docs = db.dim_destinations.find(
        match,
        {"_id": 0, "srch_destination_id": 1, "destination_name": 1},
    ).limit(limit * 3)

    seen: set[int] = set()
    suggestions: list[dict[str, Any]] = []
    for doc in docs:
        did = int(doc["srch_destination_id"])
        if did in seen:
            continue
        seen.add(did)
        suggestions.append({
            "id": did,
            "display_name": doc.get("destination_name") or f"Destino {did}",
        })
        if len(suggestions) >= limit:
            break

    return suggestions


def _amenities_prop_ids(amenities: str, mode: str = "or") -> list[int]:
    """Find prop_ids whose amenity text matches the given terms.

    Parameters
    ----------
    amenities : str
        Comma-separated amenity terms (e.g. "piscina,gimnasio,wifi").
    mode : str
        "or" — any term matches; "and" — all terms must match.

    Returns
    -------
    list[int]
        Matching prop_ids, or empty if none found.
    """
    if not amenities:
        return []
    terms = [t.strip() for t in amenities.split(",") if t.strip()]
    if not terms:
        return []
    db = get_database()
    if mode == "and":
        conditions = [{"amenities_text": {"$regex": t, "$options": "i"}} for t in terms]
        pipeline = [
            {"$match": {"$and": conditions}},
            {"$group": {"_id": "$prop_id"}},
        ]
    else:
        conditions = [{"amenities_text": {"$regex": t, "$options": "i"}} for t in terms]
        pipeline = [
            {"$match": {"$or": conditions}},
            {"$group": {"_id": "$prop_id"}},
        ]
    results = db.hotel_content_pages.aggregate(pipeline)
    return [int(r["_id"]) for r in results if r.get("_id") is not None]


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
