from __future__ import annotations

from typing import Any

from ._helpers import _active_fact_collection, _format_number, _hotel_display_name, _metric_projection
from .detail import get_hotel_detail_view
from .lookups import _hotel_lookup
from .search import _enrich_hotel_metrics


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
