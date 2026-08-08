"""Main hotel availability search with real-time inventory checking."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.app.modules.hotels.service.lookups import (
    _amenities_prop_ids,
    _destination_ids,
    _destination_lookup,
    _suggest_alternative_destinations,
)
from src.app.modules.hotels.service.operational import PUBLISHED_QUERY
from src.database.connection import get_database

from .helpers import (
    _available_room_type_summaries_for_properties,
    _destination_display_name,
    _general_amenities_for_properties,
    _hotel_display_name,
    _hotel_min_rates_for_properties,
)


def search_available_hotels(
    destination: str = "",
    check_in: str = "",
    check_out: str = "",
    adults: int = 1,
    children: int = 0,
    rooms: int = 1,
    amenities: str = "",
    amenities_mode: str = "or",
    sort_by: str = "price",
    price_min: float | None = None,
    price_max: float | None = None,
    star_rating: float | None = None,
    prop_ids: str = "",
    page: int = 1,
    page_size: int = 10,
    content_only: bool = False,
) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    has_dates = bool(check_in and check_out)

    # Parse explicit prop_ids (comma-separated) — used by favorites page
    explicit_ids: list[int] = []
    if prop_ids:
        for pid in prop_ids.split(","):
            try:
                explicit_ids.append(int(pid.strip()))
            except (ValueError, TypeError):
                pass

    if has_dates:
        try:
            date.fromisoformat(check_in)
            date.fromisoformat(check_out)
        except (ValueError, TypeError):
            return _empty_availability(destination, check_in, check_out, adults, children, rooms)

    destination_ids = _destination_ids(destination) if destination else []
    destination_lookup = _destination_lookup(destination_ids) if destination_ids else {}

    # Gate operativo (Fase A): la búsqueda pública nunca incluye hoteles
    # pendientes de aprobación (published=false). Se aplica SIEMPRE, también
    # cuando vienen prop_ids explícitos (página de favoritos).
    hotel_filter: dict[str, Any] = {**PUBLISHED_QUERY}

    # When explicit IDs are provided, use them directly (bypass destination/amenity lookups)
    if explicit_ids:
        hotel_filter["prop_id"] = {"$in": explicit_ids}
        page_size = min(page_size, len(explicit_ids))
    else:
        amenities_ids = _amenities_prop_ids(amenities, mode=amenities_mode.lower()) if amenities else []
        if amenities and not amenities_ids:
            alt = _suggest_alternative_destinations(destination, exclude_ids=destination_ids) if destination else []
            return _empty_availability(destination, check_in, check_out, adults, children, rooms, alternatives=alt)

        if destination_ids or amenities_ids:
            prop_sets: list[set[int]] = []
            if destination_ids:
                fact_prop_ids = set(db.fact_hotel_reservations.distinct(
                    "prop_id", {"srch_destination_id": {"$in": destination_ids}},
                ))
                if not fact_prop_ids:
                    alt = _suggest_alternative_destinations(destination, exclude_ids=destination_ids) if destination else []
                    return _empty_availability(destination, check_in, check_out, adults, children, rooms, alternatives=alt)
                prop_sets.append(fact_prop_ids)
            if amenities_ids:
                prop_sets.append(set(amenities_ids))
            combined = set.intersection(*prop_sets) if prop_sets else set()
            if not combined:
                alt = _suggest_alternative_destinations(destination, exclude_ids=destination_ids) if destination else []
                return _empty_availability(destination, check_in, check_out, adults, children, rooms, alternatives=alt)
            hotel_filter["prop_id"] = {"$in": list(combined)}

    if star_rating is not None:
        hotel_filter["prop_starrating"] = {"$gte": star_rating}

    if content_only:
        hotel_filter["display_name"] = {"$exists": True, "$ne": ""}

    total_candidates = db.dim_hotels.count_documents(hotel_filter)
    if total_candidates == 0:
        alt = _suggest_alternative_destinations(destination, exclude_ids=destination_ids) if destination else []
        return _empty_availability(destination, check_in, check_out, adults, children, rooms, alternatives=alt)

    mongo_sort: list[tuple[str, int]] = [("prop_id", 1)]
    if sort_by == "rating":
        mongo_sort = [("prop_review_score", -1), ("prop_id", 1)]
    elif sort_by == "stars":
        mongo_sort = [("prop_starrating", -1), ("prop_id", 1)]
    elif sort_by == "name":
        mongo_sort = [("hotel_name", 1), ("prop_id", 1)]

    def build_items(hotels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build one candidate batch with bounded Mongo round trips."""
        if not hotels:
            return []
        batch_ids = [int(hotel["prop_id"]) for hotel in hotels]
        image_map: dict[int, str] = {}
        for img in db.hotel_images.find(
            {"prop_id": {"$in": batch_ids}},
            {"_id": 0, "prop_id": 1, "image_url": 1},
        ).sort([("_id", 1)]):
            pid = int(img["prop_id"])
            if pid not in image_map:
                image_map[pid] = img["image_url"]

        available_room_summaries: dict[int, dict[str, Any]] = {}
        rates_by_property: dict[int, float] = {}
        general_amenities = _general_amenities_for_properties(batch_ids)
        nights = 0
        if has_dates:
            available_room_summaries = _available_room_type_summaries_for_properties(
                batch_ids, adults, children, check_in, check_out, rooms,
            )
            rates_by_property = _hotel_min_rates_for_properties(batch_ids, check_in, check_out)
            nights = max((date.fromisoformat(check_out) - date.fromisoformat(check_in)).days, 1)

        batch_items: list[dict[str, Any]] = []
        for hotel in hotels:
            prop_id = int(hotel["prop_id"])
            if has_dates:
                matched_room_type = available_room_summaries.get(prop_id)
                min_rate = rates_by_property.get(prop_id)
                if matched_room_type is None or min_rate is None:
                    continue
                total_est = round(min_rate * nights, 2)
                batch_items.append(_build_item(
                    hotel, prop_id, image_map, destination_lookup, destination_ids,
                    matched_room_type, min_rate, total_est,
                    general_amenities.get(prop_id, []),
                ))
            else:
                batch_items.append(_build_item(
                    hotel, prop_id, image_map, destination_lookup, destination_ids,
                    None, None, None, general_amenities.get(prop_id, []),
                ))
        # Without dates there is no live nightly rate to compare. Keep the
        # hotels visible; price filters are applied only when the request has
        # a real date range and the endpoint can calculate min_nightly_rate.
        if has_dates and price_min is not None:
            batch_items = [
                item for item in batch_items
                if item.get("min_nightly_rate") is not None
                and item["min_nightly_rate"] >= price_min
            ]
        if has_dates and price_max is not None:
            batch_items = [
                item for item in batch_items
                if item.get("min_nightly_rate") is not None
                and item["min_nightly_rate"] <= price_max
            ]
        return batch_items

    if has_dates:
        # Availability can remove candidates after the dimension query. Scan
        # ordered candidates in batches until this page is full (plus one
        # extra item to establish has_next), instead of returning short pages.
        target_count = page * page_size + 1
        eligible_items: list[dict[str, Any]] = []
        batch_size = max(page_size * 2, 20)
        candidate_cursor = db.dim_hotels.find(hotel_filter, {"_id": 0}).sort(mongo_sort)
        while len(eligible_items) < target_count:
            candidate_batch: list[dict[str, Any]] = []
            for _ in range(batch_size):
                try:
                    candidate_batch.append(next(candidate_cursor))
                except StopIteration:
                    break
            if not candidate_batch:
                break
            eligible_items.extend(build_items(candidate_batch))
        start = (page - 1) * page_size
        items = eligible_items[start:start + page_size]
        has_more_eligible = len(eligible_items) > start + page_size
    else:
        skip = (page - 1) * page_size
        page_hotels = list(db.dim_hotels.find(hotel_filter, {"_id": 0}).sort(mongo_sort).skip(skip).limit(page_size))
        items = build_items(page_hotels)
        has_more_eligible = page < ((total_candidates + page_size - 1) // page_size)

    if not items:
        empty = _empty_availability(destination, check_in, check_out, adults, children, rooms)
        empty["page"] = page
        empty["has_prev"] = page > 1
        empty["has_next"] = has_more_eligible
        return empty

    if has_dates and sort_by == "price":
        items.sort(key=lambda h: h.get("min_nightly_rate") or 999999)

    # With dates, availability is evaluated after candidate selection, so the
    # exact global total would require scanning every candidate. Expose the
    # pages known from this scan and rely on has_next for forward navigation.
    total_pages = (
        page + (1 if has_more_eligible else 0)
        if has_dates
        else max((total_candidates + page_size - 1) // page_size, 1)
    )
    result: dict[str, Any] = {
        "items": items, "total": total_candidates if items else 0, "page": page, "page_size": page_size, "total_pages": total_pages,
        "total_is_estimate": has_dates,
        "has_prev": page > 1, "has_next": has_more_eligible,
        "filters": {"destination": destination, "check_in": check_in, "check_out": check_out,
                     "adults": adults, "children": children, "rooms": rooms},
        # Keep the response envelope stable for every search result, including
        # successful searches. The frontend mapper consumes this as an array;
        # omitting it on non-empty pages caused a false wire-shape regression.
        "alternative_destinations": [],
    }
    if not items and destination:
        result["alternative_destinations"] = _suggest_alternative_destinations(destination, exclude_ids=destination_ids)
    return result


def _build_item(hotel, prop_id, image_map, destination_lookup, destination_ids, matched_room_type, min_rate, total_est, general_amenities):
    item = {
        "prop_id": prop_id, "hotel_name": _hotel_display_name(hotel, prop_id),
        "display_name": hotel.get("display_name") or "",
        "prop_starrating": hotel.get("prop_starrating"),
        "prop_review_score": hotel.get("prop_review_score"),
        "image_url": image_map.get(prop_id),
        "destination_labels": [_destination_display_name(destination_lookup.get(did, {}), did)
                               for did in (hotel.get("destinations") or destination_ids)[:3]] if destination_ids else [],
        "general_amenities": general_amenities,
    }
    if matched_room_type is not None and min_rate is not None and total_est is not None:
        item["matched_room_type"] = matched_room_type
        item["min_nightly_rate"] = min_rate
        item["min_nightly_rate_label"] = f"${min_rate:.2f}"
        item["total_estimated"] = total_est
        item["total_estimated_label"] = f"${total_est:.2f}"
    return item


def _empty_availability(destination="", check_in="", check_out="", adults=1, children=0, rooms=1, alternatives=None):
    result = {
        "items": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 0,
        "total_is_estimate": bool(check_in and check_out),
        "has_prev": False, "has_next": False,
        "filters": {"destination": destination, "check_in": check_in, "check_out": check_out,
                     "adults": adults, "children": children, "rooms": rooms},
        "alternative_destinations": alternatives or [],
    }
    return result
