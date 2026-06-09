from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any

from src.database.connection import get_database


FACT_RESERVATION_COLUMNS = [
    "source_record_id",
    "srch_id",
    "date_time",
    "date_key",
    "site_id",
    "visitor_location_country_id",
    "visitor_hist_starrating",
    "visitor_hist_adr_usd",
    "prop_country_id",
    "prop_id",
    "prop_starrating",
    "prop_review_score",
    "prop_brand_bool",
    "prop_location_score1",
    "price_usd",
    "promotion_flag",
    "srch_destination_id",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
    "click_bool",
    "reserva_bool",
    "reservas_brutas_usd",
    "occupancy_profile_id",
    "stay_length_category_id",
    "booking_window_category_id",
    "price_category_id",
    "loaded_at",
    "execution_id",
]


def _safe_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not text.lstrip("-").isdigit():
        return None
    return int(text)


def _dimension_lookup(collection_name: str, key_field: str, ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    db = get_database()
    documents = db[collection_name].find({key_field: {"$in": ids}}, {"_id": 0})
    return {int(item[key_field]): item for item in documents if item.get(key_field) is not None}


def _serialize_number(value: Any) -> str:
    if value is None:
        return "N/D"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _log_search(query: str, destination: str, country: str, min_rating: float | None, page_size: int) -> None:
    if not any([query, destination, country, min_rating is not None]):
        return
    db = get_database()
    db.search_logs.insert_one(
        {
            "query": query,
            "destination": destination,
            "country": country,
            "min_rating": min_rating,
            "page_size": page_size,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def find_hotels(
    query: str,
    destination: str = "",
    country: str = "",
    min_rating: float | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 25)
    _log_search(query, destination, country, min_rating, page_size)

    fact_filter: dict[str, Any] = {}

    if query:
        hotel_filter: dict[str, Any] = {"hotel_name": {"$regex": query, "$options": "i"}}
        if min_rating is not None:
            hotel_filter["hotel_rating"] = {"$gte": min_rating}
        prop_ids = [item["prop_id"] for item in db.dim_hotels.find(hotel_filter, {"prop_id": 1, "_id": 0})]
        query_as_id = _safe_int(query)
        if query_as_id is not None:
            prop_ids.append(query_as_id)
        prop_ids = sorted({int(prop_id) for prop_id in prop_ids if prop_id is not None})
        if not prop_ids:
            return _empty_results(query, destination, country, min_rating, page_size)
        fact_filter["prop_id"] = {"$in": prop_ids}
    elif min_rating is not None:
        prop_ids = [
            item["prop_id"]
            for item in db.dim_hotels.find({"hotel_rating": {"$gte": min_rating}}, {"prop_id": 1, "_id": 0})
        ]
        prop_ids = sorted({int(prop_id) for prop_id in prop_ids if prop_id is not None})
        if not prop_ids:
            return _empty_results(query, destination, country, min_rating, page_size)
        fact_filter["prop_id"] = {"$in": prop_ids}

    if destination:
        destination_filter: dict[str, Any] = {"destination_name": {"$regex": destination, "$options": "i"}}
        destination_ids = [
            item["srch_destination_id"]
            for item in db.dim_destinations.find(destination_filter, {"srch_destination_id": 1, "_id": 0})
        ]
        destination_as_id = _safe_int(destination)
        if destination_as_id is not None:
            destination_ids.append(destination_as_id)
        destination_ids = sorted({int(item) for item in destination_ids if item is not None})
        if not destination_ids:
            return _empty_results(query, destination, country, min_rating, page_size)
        fact_filter["srch_destination_id"] = {"$in": destination_ids}

    if country:
        country_filter: dict[str, Any] = {"country_name": {"$regex": country, "$options": "i"}}
        country_ids = [
            item["visitor_location_country_id"]
            for item in db.dim_visitor_countries.find(country_filter, {"visitor_location_country_id": 1, "_id": 0})
        ]
        country_as_id = _safe_int(country)
        if country_as_id is not None:
            country_ids.append(country_as_id)
        country_ids = sorted({int(item) for item in country_ids if item is not None})
        if not country_ids:
            return _empty_results(query, destination, country, min_rating, page_size)
        fact_filter["visitor_location_country_id"] = {"$in": country_ids}

    fact_collection = db.fact_hotel_reservations
    if fact_collection.estimated_document_count() == 0:
        fact_collection = db.fact_hotel_events

    total = fact_collection.count_documents(fact_filter)
    total_pages = ceil(total / page_size) if total else 0
    if total_pages and page > total_pages:
        page = total_pages

    items = list(
        fact_collection.find(fact_filter, {"_id": 0})
        .sort([("date_time", -1), ("srch_id", 1), ("prop_id", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    hotel_lookup = _dimension_lookup("dim_hotels", "prop_id", [item["prop_id"] for item in items if item.get("prop_id")])
    destination_lookup = _dimension_lookup(
        "dim_destinations",
        "srch_destination_id",
        [item["srch_destination_id"] for item in items if item.get("srch_destination_id")],
    )
    country_lookup = _dimension_lookup(
        "dim_visitor_countries",
        "visitor_location_country_id",
        [item["visitor_location_country_id"] for item in items if item.get("visitor_location_country_id")],
    )

    enriched_items: list[dict[str, Any]] = []
    for item in items:
        hotel = hotel_lookup.get(int(item["prop_id"]), {})
        destination_doc = destination_lookup.get(int(item["srch_destination_id"]), {})
        country_doc = country_lookup.get(int(item["visitor_location_country_id"]), {})
        reservation_state = "Reserva completada" if item.get("reserva_bool") == 1 else "Abandono / no reservó"
        enriched_items.append(
            {
                **item,
                "hotel_name": hotel.get("hotel_name") or f"Hotel #{item['prop_id']}",
                "hotel_rating": hotel.get("hotel_rating"),
                "destination_name": destination_doc.get("destination_name") or f"Destino #{item['srch_destination_id']}",
                "country_name": country_doc.get("country_name")
                or f"País #{item['visitor_location_country_id']}",
                "reservation_state": reservation_state,
                "promotion_label": "Promoción" if item.get("promotion_flag") == 1 else "Normal",
                "price_label": _serialize_number(item.get("price_usd")),
                "gross_label": _serialize_number(item.get("reservas_brutas_usd")),
                "rating_label": (
                    f"{hotel['hotel_rating']:.1f}" if isinstance(hotel.get("hotel_rating"), (int, float)) else "N/D"
                ),
            }
        )

    prices = [float(item["price_usd"]) for item in enriched_items if item.get("price_usd") is not None]
    bookings = [item for item in enriched_items if item.get("reserva_bool") in (1, True)]
    start_index = (page - 1) * page_size + 1 if total else 0
    end_index = start_index + len(enriched_items) - 1 if enriched_items else 0

    return {
        "items": enriched_items,
        "display_columns": FACT_RESERVATION_COLUMNS,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
        "prev_page": page - 1 if page > 1 and total_pages > 0 else None,
        "next_page": page + 1 if total_pages > 0 and page < total_pages else None,
        "start_index": start_index,
        "end_index": end_index,
        "average_price": round(sum(prices) / len(prices), 2) if prices else None,
        "bookings_on_page": len(bookings),
        "promotion_events_on_page": sum(1 for item in enriched_items if item.get("promotion_flag") == 1),
        "filters": {
            "query": query,
            "destination": destination,
            "country": country,
            "min_rating": min_rating,
        },
    }


def _empty_results(
    query: str,
    destination: str,
    country: str,
    min_rating: float | None,
    page_size: int,
) -> dict[str, Any]:
    return {
        "items": [],
        "display_columns": FACT_RESERVATION_COLUMNS,
        "total": 0,
        "page": 1,
        "page_size": page_size,
        "total_pages": 0,
        "has_prev": False,
        "has_next": False,
        "prev_page": None,
        "next_page": None,
        "start_index": 0,
        "end_index": 0,
        "average_price": None,
        "bookings_on_page": 0,
        "promotion_events_on_page": 0,
        "filters": {
            "query": query,
            "destination": destination,
            "country": country,
            "min_rating": min_rating,
        },
    }
