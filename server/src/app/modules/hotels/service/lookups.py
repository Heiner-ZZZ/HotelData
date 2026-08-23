from __future__ import annotations

import re
from typing import Any

from src.app.modules.hotels.service._helpers import _safe_float, _safe_int
from src.database.connection import get_database


def _ci_regex(term: str) -> re.Pattern[str]:
    """Compiled case-insensitive regex with the term escaped.

    $regex con el término crudo interpreta metacaracteres del usuario
    (``(``, ``[``, ``*``…) y puede lanzar OperationFailure → 500 en un
    endpoint público. ``re.escape`` convierte el input en substring literal.
    """
    return re.compile(re.escape(term), re.IGNORECASE)


def _destination_ids(destination: str) -> list[int]:
    destination_id = _safe_int(destination)
    if destination_id is not None:
        return [destination_id]
    if not destination:
        return []
    db = get_database()
    docs = db.dim_destinations.find(
        {"destination_name": _ci_regex(destination)},
        {"_id": 0, "srch_destination_id": 1},
    ).limit(200)
    return [int(item["srch_destination_id"]) for item in docs if item.get("srch_destination_id") is not None]


def suggest_destinations(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Public destination suggestions for the welcome booking-bar autocomplete.

    Case-insensitive substring match over three sources:

    - ``dim_destinations.destination_name`` → type ``city``
    - ``dim_hotels`` (``display_name`` / ``hotel_name`` / ``city``) → type ``hotel``
    - ``dim_visitor_countries`` → type ``country`` (tabla de países del dataset;
      el catálogo curado ``geo_catalog`` ya NO participa — opción B)

    Each item: ``{"id", "name", "type"}``. El mezclado es round-robin por
    tipo (fair mix): un prefijo con muchas ciudades no acapara los slots y
    deja de mostrar hoteles/países. No auth required — same surface as
    ``/api/hotels/availability``.
    """
    q = (query or "").strip()
    if not q:
        return []
    db = get_database()
    limit = min(max(int(limit), 1), 20)
    rx = _ci_regex(q)
    # Pool por tipo (más amplio que limit para que el interleave tenga fuel).
    pool_size = limit * 3

    cities: list[dict[str, Any]] = [
        {
            "id": int(doc["srch_destination_id"]),
            "name": doc.get("destination_name") or f"Destino {doc['srch_destination_id']}",
            "type": "city",
        }
        for doc in db.dim_destinations.find(
            {"destination_name": rx},
            {"_id": 0, "srch_destination_id": 1, "destination_name": 1},
        ).sort("destination_name", 1).limit(pool_size)
        if doc.get("srch_destination_id") is not None
    ]

    hotels: list[dict[str, Any]] = []
    for hotel in db.dim_hotels.find(
        {"$or": [{"display_name": rx}, {"hotel_name": rx}, {"city": rx}]},
        {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1},
    ).limit(pool_size):
        pid = hotel.get("prop_id")
        if pid is None:
            continue
        name = hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {pid}"
        hotels.append({"id": int(pid), "name": name, "type": "hotel"})

    countries: list[dict[str, Any]] = [
        {
            "id": int(c["visitor_location_country_id"]),
            "name": c.get("country_name") or c.get("country_display_name") or f"País {c['visitor_location_country_id']}",
            "type": "country",
        }
        for c in db.dim_visitor_countries.find(
            {"$or": [{"country_name": rx}, {"country_display_name": rx}, {"visitor_country_label": rx}]},
            {"_id": 0, "visitor_location_country_id": 1, "country_name": 1, "country_display_name": 1},
        ).limit(pool_size)
        if c.get("visitor_location_country_id") is not None
    ]

    # Dedup por nombre DENTRO de cada pool (una sola fuente de países: la del
    # dataset — no hay duplicados legacy/geo que reconciliar).
    def _dedup(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in pool:
            key = (item.get("name") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    pools = [_dedup(cities), _dedup(hotels), _dedup(countries)]
    # Round-robin por tipo: city → hotel → country → city… hasta llenar limit.
    out: list[dict[str, Any]] = []
    idx = [0, 0, 0]
    while len(out) < limit and any(p for p in pools):
        advanced = False
        for i, pool in enumerate(pools):
            if len(out) >= limit:
                break
            if idx[i] < len(pool):
                out.append(pool[idx[i]])
                idx[i] += 1
                advanced = True
        if not advanced:
            break
    return out


def _prop_ids_for_countries(country_ids: list[int]) -> list[int]:
    """prop_ids de dim_hotels cuyo país (prop_country_id → dim_visitor_countries)
    está en la lista."""
    if not country_ids:
        return []
    db = get_database()
    docs = db.dim_hotels.find(
        {"prop_country_id": {"$in": country_ids}},
        {"_id": 0, "prop_id": 1},
    ).limit(1000)
    return [int(doc["prop_id"]) for doc in docs if doc.get("prop_id") is not None]


def _resolve_destination(destination: str) -> dict[str, Any]:
    """Resolve free-text destination to city IDs, hotel prop_ids and country keys.

    Returns ``{"destination_ids", "prop_ids", "country_ids"}``
    so callers can build an OR filter over every place a user may type
    (ciudad, nombre de hotel o país). Each list is empty when nothing matches.
    """
    q = (destination or "").strip()
    out: dict[str, Any] = {"destination_ids": [], "prop_ids": [], "country_ids": []}
    if not q:
        return out
    db = get_database()

    out["destination_ids"] = _destination_ids(q)

    rx = _ci_regex(q)
    for hotel in db.dim_hotels.find(
        {"$or": [{"display_name": rx}, {"hotel_name": rx}, {"city": rx}]},
        {"_id": 0, "prop_id": 1},
    ).limit(200):
        if hotel.get("prop_id") is not None:
            out["prop_ids"].append(int(hotel["prop_id"]))

    for country in db.dim_visitor_countries.find(
        {"$or": [{"country_name": rx}, {"country_display_name": rx}, {"visitor_country_label": rx}]},
        {"_id": 0, "visitor_location_country_id": 1},
    ).limit(100):
        if country.get("visitor_location_country_id") is not None:
            out["country_ids"].append(int(country["visitor_location_country_id"]))

    return out


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
    terms = [{"destination_name": _ci_regex(w)} for w in words]

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
    resolved = _resolve_destination(destination) if destination else {}
    if destination:
        destination_ids = resolved.get("destination_ids", [])
        prop_ids = resolved.get("prop_ids", [])
        country_prop_ids = _prop_ids_for_countries(resolved.get("country_ids", []))
        if not destination_ids and not prop_ids and not country_prop_ids:
            return None
        or_conditions: list[dict[str, Any]] = []
        if destination_ids:
            or_conditions.append({"srch_destination_id": {"$in": destination_ids}})
        all_prop_ids = list(dict.fromkeys([*prop_ids, *country_prop_ids]))
        if all_prop_ids:
            or_conditions.append({"prop_id": {"$in": all_prop_ids}})
        if len(or_conditions) == 1:
            match.update(or_conditions[0])
        else:
            match["$or"] = or_conditions

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
