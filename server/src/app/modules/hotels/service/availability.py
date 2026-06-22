"""Operational hotel search with real-time availability checking.

This service finds hotels by destination, then verifies inventory
availability in `room_inventory_calendar` for the requested date range,
and returns base rates from `hotel_rate_calendar`.

It complements the analytical search (search.py) which queries the
fact table for historical metrics.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.app.modules.hotels.service._helpers import (
    _destination_display_name,
    _hotel_display_name,
)
from src.app.modules.hotels.service.lookups import (
    _amenities_prop_ids,
    _destination_ids,
    _destination_lookup,
)
from src.database.connection import get_database


def _check_inventory_for_dates(
    prop_id: int,
    room_type_id: str,
    check_in: str,
    check_out: str,
    required_rooms: int,
) -> bool:
    """Check if a room type has enough available rooms for all dates in range."""
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return False

    nights = (end - start).days
    if nights < 1:
        return False

    dates = [(start + timedelta(days=i)).isoformat() for i in range(nights)]

    db = get_database()
    count = db.room_inventory_calendar.count_documents(
        {
            "prop_id": prop_id,
            "room_type_id": room_type_id,
            "date": {"$in": dates},
            "available_rooms": {"$gte": required_rooms},
        }
    )
    return count == len(dates)


def _matching_room_types(prop_id: int, adults: int, children: int) -> list[dict[str, Any]]:
    """Find room types for a hotel that can accommodate the requested guests."""
    db = get_database()
    return list(
        db.room_types.find(
            {
                "prop_id": prop_id,
                "is_active": True,
                "max_adults": {"$gte": adults or 1},
                "max_children": {"$gte": children or 0},
            },
            {"_id": 0},
        ).sort([("base_capacity", 1)])
    )


def _hotel_min_rate_for_range(prop_id: int, check_in: str, check_out: str) -> float | None:
    """Get the minimum nightly rate across all rate plans and dates in range."""
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return None

    nights = (end - start).days
    if nights < 1:
        return None

    dates = [(start + timedelta(days=i)).isoformat() for i in range(nights)]

    db = get_database()
    result = db.hotel_rate_calendar.aggregate([
        {"$match": {"prop_id": prop_id, "date": {"$in": dates}, "is_closed": {"$ne": True}}},
        {"$group": {"_id": None, "min_rate": {"$min": "$rate_amount"}}},
    ])

    row = next(result, None)
    if row and row.get("min_rate") is not None:
        return round(float(row["min_rate"]), 2)
    return None


def _hotel_image_url(prop_id: int) -> str | None:
    """Get the first image URL for a hotel from hotel_images collection."""
    db = get_database()
    image = db.hotel_images.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "image_url": 1},
        sort=[("_id", 1)],
    )
    return image.get("image_url") if image else None


def search_available_hotels(
    destination: str = "",
    check_in: str = "",
    check_out: str = "",
    adults: int = 1,
    children: int = 0,
    rooms: int = 1,
    amenities: str = "",
    amenities_mode: str = "or",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Search hotels with real-time availability for the given criteria.

    Returns hotels that:
    - Match the destination (if provided)
    - Have room types that accommodate the guest count
    - Have available inventory for all dates in the range (if dates provided)
    - Have a rate configured for the date range (if dates provided)

    Results are paginated and sorted by minimum nightly rate.
    If no dates are provided, returns all hotels without availability filtering.
    """
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    has_dates = bool(check_in and check_out)
    
    # Validate date format if provided
    if has_dates:
        try:
            date.fromisoformat(check_in)
            date.fromisoformat(check_out)
        except (ValueError, TypeError):
            return _empty_availability(destination, check_in, check_out, adults, children, rooms)

    # 1. Resolve destination to IDs
    destination_ids = _destination_ids(destination) if destination else []
    destination_lookup = _destination_lookup(destination_ids) if destination_ids else {}

    # 2. Build base hotel query
    hotel_filter: dict[str, Any] = {}
    amenities_ids = _amenities_prop_ids(amenities, mode=amenities_mode.lower()) if amenities else []
    if amenities and not amenities_ids:
        return _empty_availability(destination, check_in, check_out, adults, children, rooms)

    if destination_ids or amenities_ids:
        # Combine destination and amenities filters
        prop_sets = []
        if destination_ids:
            fact_prop_ids = set(db.fact_hotel_reservations.distinct(
                "prop_id",
                {"srch_destination_id": {"$in": destination_ids}},
            ))
            if not fact_prop_ids:
                return _empty_availability(destination, check_in, check_out, adults, children, rooms)
            prop_sets.append(fact_prop_ids)
        if amenities_ids:
            prop_sets.append(set(amenities_ids))
        # Intersect all sets
        combined = set.intersection(*prop_sets) if prop_sets else set()
        if not combined:
            return _empty_availability(destination, check_in, check_out, adults, children, rooms)
        hotel_filter["prop_id"] = {"$in": list(combined)}

    # 3. Get ALL candidate hotels from dim_hotels (paginate AFTER availability check)
    all_candidates = list(db.dim_hotels.find(hotel_filter, {"_id": 0}).sort([("prop_id", 1)]))
    if not all_candidates:
        return _empty_availability(destination, check_in, check_out, adults, children, rooms)

    # 4. Check availability for ALL candidates
    available: list[dict[str, Any]] = []
    for hotel in all_candidates:
        prop_id = int(hotel["prop_id"])

        # Skip availability check if no dates provided
        if has_dates:
            # Find matching room types for this guest count
            room_types = _matching_room_types(prop_id, adults, children)
            if not room_types:
                continue

            # Check inventory for each room type
            has_availability = False
            matched_room_type = None
            for rt in room_types:
                if _check_inventory_for_dates(prop_id, rt["room_type_id"], check_in, check_out, rooms):
                    has_availability = True
                    matched_room_type = rt
                    break

            if not has_availability:
                continue

            # Get base rate for the range
            min_rate = _hotel_min_rate_for_range(prop_id, check_in, check_out)
            if min_rate is None:
                continue

            nights = max((date.fromisoformat(check_out) - date.fromisoformat(check_in)).days, 1)
            total_est = round(min_rate * nights, 2)
            
            # Get image
            image_url = _hotel_image_url(prop_id)

            available.append({
                "prop_id": prop_id,
                "hotel_name": _hotel_display_name(hotel, prop_id),
                "display_name": hotel.get("display_name") or "",
                "prop_starrating": hotel.get("prop_starrating"),
                "prop_review_score": hotel.get("prop_review_score"),
                "image_url": image_url,
                "destination_labels": [
                    _destination_display_name(destination_lookup.get(did, {}), did)
                    for did in (hotel.get("destinations") or [])[:3]
                ] if destination_ids else [],
                "matched_room_type": {
                    "room_type_id": matched_room_type["room_type_id"],
                    "name": matched_room_type.get("name") or "",
                    "max_adults": matched_room_type.get("max_adults"),
                    "max_children": matched_room_type.get("max_children"),
                    "base_capacity": matched_room_type.get("base_capacity"),
                },
                "min_nightly_rate": min_rate,
                "min_nightly_rate_label": f"${min_rate:.2f}",
                "total_estimated": total_est,
                "total_estimated_label": f"${total_est:.2f}",
                "available_room_types_count": len(room_types),
            })
        else:
            # No dates: return hotel without availability/rate info
            image_url = _hotel_image_url(prop_id)
            available.append({
                "prop_id": prop_id,
                "hotel_name": _hotel_display_name(hotel, prop_id),
                "display_name": hotel.get("display_name") or "",
                "prop_starrating": hotel.get("prop_starrating"),
                "prop_review_score": hotel.get("prop_review_score"),
                "image_url": image_url,
                "destination_labels": [
                    _destination_display_name(destination_lookup.get(did, {}), did)
                    for did in (hotel.get("destinations") or [])[:3]
                ] if destination_ids else [],
                "available_room_types_count": 0,
            })

    # 5. Sort by rate (cheapest first) — only when rates exist
    available.sort(key=lambda h: h.get("min_nightly_rate") or 999999)

    # 6. Paginate AFTER availability check
    total_available = len(available)
    total_pages = max((total_available + page_size - 1) // page_size, 1) if total_available else 0
    if page > total_pages:
        page = total_pages if total_pages > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = available[start_idx:end_idx]

    return {
        "items": page_items,
        "total": total_available,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": end_idx < total_available,
        "filters": {
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "children": children,
            "rooms": rooms,
        },
    }


def _empty_availability(destination: str, check_in: str, check_out: str, adults: int = 1, children: int = 0, rooms: int = 1) -> dict[str, Any]:
    return {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 10,
        "total_pages": 0,
        "has_prev": False,
        "has_next": False,
        "filters": {
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "children": children,
            "rooms": rooms,
        },
    }
