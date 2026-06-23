from __future__ import annotations

from typing import Any

from pymongo import ASCENDING

from src.app.security.hotel_filter import hotel_filter_from_user
from src.database.connection import get_database


def reservation_hotel_options(limit: int = 30, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    db = get_database()
    user_filter = hotel_filter_from_user(user)
    query_filter: dict[str, Any] = {}
    if user_filter:
        query_filter.update(user_filter)
    hotels = list(
        db.dim_hotels.find(
            query_filter,
            {
                "_id": 0,
                "prop_id": 1,
                "display_name": 1,
                "display_label": 1,
                "hotel_name": 1,
                "prop_starrating": 1,
            },
        )
        .sort([("display_name", ASCENDING), ("prop_id", ASCENDING)])
        .limit(limit)
    )
    options: list[dict[str, Any]] = []
    for hotel in hotels:
        prop_id = hotel.get("prop_id")
        if prop_id is None:
            continue
        label = (
            hotel.get("display_label")
            or hotel.get("display_name")
            or hotel.get("hotel_name")
            or f"Hotel {prop_id}"
        )
        options.append({"prop_id": prop_id, "label": label})
    return options
