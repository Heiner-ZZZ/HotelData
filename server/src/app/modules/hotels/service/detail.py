from __future__ import annotations

from typing import Any

from ._helpers import (
    _active_fact_collection,
    _country_display_name,
    _destination_display_name,
    _format_money,
    _metric_projection,
    _min_real_rate_for_prop,
    _site_display_name,
)
from .lookups import _country_lookup, _destination_lookup, _site_lookup
from .search import _enrich_hotel_metrics
from src.database.connection import get_database


def top_destinations_for_hotel(prop_id: int, limit: int = 8) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {"$group": {"_id": "$srch_destination_id", "events": {"$sum": 1}, "avg_price": {"$avg": "$price_usd"}}},
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _destination_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "srch_destination_id": int(row["_id"]),
            "destination_label": _destination_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "avg_price_label": _format_money(row.get("avg_price")),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _top_visitor_countries_for_hotel(prop_id: int, limit: int = 6) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$visitor_location_country_id",
                "events": {"$sum": 1},
                "reservations": {"$sum": {"$cond": [{"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _country_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "visitor_location_country_id": int(row["_id"]),
            "country_label": _country_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "reservations": int(row.get("reservations") or 0),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _top_sites_for_hotel(prop_id: int, limit: int = 6) -> list[dict[str, Any]]:
    collection, _ = _active_fact_collection()
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {
            "$group": {
                "_id": "$site_id",
                "events": {"$sum": 1},
                "clicks": {"$sum": {"$cond": [{"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}, 1, 0]}},
                "reservations": {"$sum": {"$cond": [{"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}, 1, 0]}},
            }
        },
        {"$sort": {"events": -1}},
        {"$limit": limit},
    ]
    rows = list(collection.aggregate(pipeline, allowDiskUse=True))
    lookup = _site_lookup([int(row["_id"]) for row in rows if row.get("_id") is not None])
    return [
        {
            "site_id": int(row["_id"]),
            "site_label": _site_display_name(lookup.get(int(row["_id"]), {}), int(row["_id"])),
            "events": int(row.get("events") or 0),
            "clicks": int(row.get("clicks") or 0),
            "reservations": int(row.get("reservations") or 0),
        }
        for row in rows
        if row.get("_id") is not None
    ]


def _hotel_rates_for_detail(prop_id: int, limit: int = 12) -> list[dict[str, Any]]:
    db = get_database()
    items = list(
        db.hotel_rate_calendar.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("date", 1), ("rate_plan_id", 1)])
        .limit(limit)
    )
    return [{**item, "rate_amount_label": _format_money(item.get("rate_amount"))} for item in items]


def _room_types_for_detail(prop_id: int, limit: int = 12) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.room_types.find(
            {"prop_id": prop_id},
            {"_id": 0, "room_type_id": 1, "name": 1, "base_capacity": 1, "max_adults": 1, "max_children": 1, "is_active": 1, "description": 1, "features": 1, "image_url": 1},
        )
        .sort([("is_active", -1), ("name", 1)])
        .limit(limit)
    )


def _hotel_rooms_for_detail(prop_id: int) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.hotel_rooms.find(
            {"prop_id": prop_id},
            {"_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1, "room_type_id": 1, "floor": 1, "is_active": 1},
        )
        .sort([("room_number", 1)])
    )


def _hotel_policies_for_detail(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    return db.hotel_policies.find_one({"prop_id": prop_id}, {"_id": 0})


def _hotel_images_for_detail(prop_id: int) -> list[dict[str, Any]]:
    db = get_database()
    return list(db.hotel_images.find({"prop_id": prop_id}, {"_id": 0, "image_url": 1}).sort([("_id", 1)]).limit(20))


def _hotel_content_for_detail(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    return db.hotel_content_pages.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "description": 1, "highlights": 1, "amenities_text": 1, "facilities": 1, "latitude": 1, "longitude": 1},
    )


def _hotel_reviews_for_detail(prop_id: int, limit: int = 5) -> list[dict[str, Any]]:
    db = get_database()
    return list(
        db.reviews.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("created_at", -1)])
        .limit(limit)
    )


def get_hotel_detail_view(prop_id: int) -> dict[str, Any] | None:
    collection, source_collection = _active_fact_collection()
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0}) or {}
    pipeline = [
        {"$match": {"prop_id": prop_id}},
        {"$group": {"_id": "$prop_id", "prop_id": {"$first": "$prop_id"}, **_metric_projection()}},
    ]
    metrics = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    if not hotel and not metrics:
        return None

    item = _enrich_hotel_metrics([metrics or {"prop_id": prop_id, "events": 0, "reservations": 0, "clicks": 0, "destinations": []}])[0]
    item["source_collection"] = source_collection
    item["hotel"] = hotel
    item["min_rate_label"] = _min_real_rate_for_prop(prop_id)
    item["top_destinations"] = top_destinations_for_hotel(prop_id)
    item["top_visitor_countries"] = _top_visitor_countries_for_hotel(prop_id)
    item["top_sites"] = _top_sites_for_hotel(prop_id)
    item["hotel_rates"] = _hotel_rates_for_detail(prop_id)
    item["room_types"] = _room_types_for_detail(prop_id)
    item["hotel_rooms"] = _hotel_rooms_for_detail(prop_id)
    item["hotel_policies"] = _hotel_policies_for_detail(prop_id)
    item["hotel_images"] = _hotel_images_for_detail(prop_id)
    item["hotel_content"] = _hotel_content_for_detail(prop_id)
    item["reviews"] = _hotel_reviews_for_detail(prop_id)
    reviews_full = list(db.reviews.find({"prop_id": prop_id}).limit(0))
    item["review_count"] = len(reviews_full) if reviews_full else db.reviews.count_documents({"prop_id": prop_id})
    return item


def hotel_detail(prop_id: int) -> dict[str, Any] | None:
    return get_hotel_detail_view(prop_id)
