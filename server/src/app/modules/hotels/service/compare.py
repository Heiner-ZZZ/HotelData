from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

from src.database.connection import get_database

from ._helpers import (
    _active_fact_collection,
    _format_number,
    _hotel_display_name,
    _metric_projection,
)
from .detail import get_hotel_detail_view
from .lookups import _hotel_lookup
from .search import _enrich_hotel_metrics


def _synthetic_coords(prop_id: int) -> tuple[float, float]:
    """Deterministic synthetic coordinates for a prop_id.

    Spreads hotels across a ~Mexico / Caribbean bounding box
    (19–27°N, 99–84°W) using MD5 so every hotel always gets
    the same lat/lng across restarts.
    """
    h = hashlib.md5(str(prop_id).encode()).hexdigest()
    lat = 19.0 + (int(h[:4], 16) / 65535) * 8.0
    lng = -99.0 + (int(h[4:8], 16) / 65535) * 15.0
    return round(lat, 6), round(lng, 6)


def _compare_hotel_rate(prop_id: int, check_in: str, check_out: str) -> float | None:
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


def compare_hotels_with_availability(
    prop_ids: list[int],
    check_in: str = "",
    check_out: str = "",
    adults: int = 1,
    children: int = 0,
) -> dict[str, Any]:
    """Compare hotels with operational availability data (rates, room types, amenities, policies).

    Returns enhanced comparison data for up to 3 hotels,
    combining analytical metrics with real-time operational info.
    """
    unique_ids = list(dict.fromkeys([pid for pid in prop_ids if pid is not None]))[:3]
    if not unique_ids:
        return {"items": []}

    db = get_database()
    hotel_lookup = _hotel_lookup(unique_ids)
    has_dates = bool(check_in and check_out)
    items: list[dict[str, Any]] = []

    for prop_id in unique_ids:
        hotel = hotel_lookup.get(prop_id, {})
        # Gate operativo (Fase A): los hoteles pendientes de aprobación
        # (published=false) no participan en la comparación pública.
        if hotel.get("published") is False:
            continue
        prop_id_int = int(prop_id)

        image_url = None
        img = db.hotel_images.find_one(
            {"prop_id": prop_id_int},
            {"_id": 0, "image_url": 1},
            sort=[("_id", 1)],
        )
        if img:
            image_url = img.get("image_url")

        amenities_text = ""
        content = db.hotel_content_pages.find_one(
            {"prop_id": prop_id_int},
            {"_id": 0, "amenities_text": 1},
        )
        if content:
            amenities_text = (content.get("amenities_text") or "")

        room_types = list(db.room_types.find(
            {"prop_id": prop_id_int, "is_active": True},
            {"_id": 0, "room_type_id": 1, "name": 1, "max_adults": 1, "max_children": 1, "base_capacity": 1, "description": 1},
        ).sort([("base_capacity", 1)]))

        policy_doc = db.hotel_policies.find_one({"prop_id": prop_id_int}, {"_id": 0})

        lat, lng = _synthetic_coords(prop_id_int)
        item: dict[str, Any] = {
            "prop_id": prop_id_int,
            "hotel_name": _hotel_display_name(hotel, prop_id_int),
            "display_name": hotel.get("display_name", ""),
            "prop_starrating": hotel.get("prop_starrating"),
            "prop_review_score": hotel.get("prop_review_score"),
            "image_url": image_url,
            "amenities_text": amenities_text,
            "room_types": room_types,
            "policies": policy_doc or {},
            "destination_labels": [],
            "latitude": lat,
            "longitude": lng,
        }

        if has_dates:
            rate = _compare_hotel_rate(prop_id_int, check_in, check_out)
            if rate is not None:
                nights = max((date.fromisoformat(check_out) - date.fromisoformat(check_in)).days, 1)
                item["min_nightly_rate"] = rate
                item["min_nightly_rate_label"] = f"${rate:.2f}"
                item["total_estimated"] = round(rate * nights, 2)
                item["total_estimated_label"] = f"${round(rate * nights, 2):.2f}"

        items.append(item)

    order = {pid: i for i, pid in enumerate(unique_ids)}
    items.sort(key=lambda x: order.get(x["prop_id"], 999))
    return {"items": items}


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
