from __future__ import annotations

from typing import Any

from pymongo import ASCENDING

from src.app.security.hotel_filter import hotel_filter_from_user
from src.database.connection import get_database


def reservation_hotel_options(limit: int = 100, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    db = get_database()
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
        all_ids = all_ids[:limit]
        return [{"prop_id": pid, "label": f"Hotel {pid}"} for pid in all_ids]

    dim_hotels = list(db.dim_hotels.find({}, {"_id": 0}))
    dim_lookup = {int(item["prop_id"]): item for item in dim_hotels if item.get("prop_id") is not None}
    dim_prop_ids = set(dim_lookup.keys())
    fact_prop_ids = set(db.fact_hotel_reservations.distinct("prop_id"))
    all_prop_ids = sorted(dim_prop_ids | fact_prop_ids)
    if allowed_ids is not None:
        all_prop_ids = [pid for pid in all_prop_ids if pid in allowed_ids]

    options: list[dict[str, Any]] = []
    for prop_id in all_prop_ids[:limit]:
        hotel = dim_lookup.get(prop_id)
        if hotel:
            label = (
                hotel.get("display_label")
                or hotel.get("display_name")
                or hotel.get("hotel_name")
                or f"Hotel {prop_id}"
            )
        else:
            label = f"Hotel {prop_id}"
        options.append({"prop_id": prop_id, "label": label})
    return options
