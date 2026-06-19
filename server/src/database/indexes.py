from __future__ import annotations

from pymongo import ASCENDING
from pymongo.database import Database


def create_indexes(db: Database) -> dict[str, list[str]]:
    index_map = {
        "dim_hotels": [("prop_id", ASCENDING, True)],
        "dim_destinations": [("srch_destination_id", ASCENDING, True)],
        "dim_visitor_countries": [("visitor_location_country_id", ASCENDING, True)],
        "dim_dates": [("date_key", ASCENDING, True)],
        "dim_promotions": [("promotion_flag", ASCENDING, True)],
        "dim_reservation_status": [("reserva_bool", ASCENDING, True)],
        "dim_occupancy_profile": [("occupancy_profile_id", ASCENDING, True)],
        "dim_stay_length_category": [("stay_length_category_id", ASCENDING, True)],
        "dim_booking_window_category": [("booking_window_category_id", ASCENDING, True)],
        "dim_price_category": [("price_category_id", ASCENDING, True)],
        "fact_hotel_events": [
            ("srch_id", ASCENDING, False),
            ("date_key", ASCENDING, False),
            ("prop_id", ASCENDING, False),
            ("srch_destination_id", ASCENDING, False),
            ("visitor_location_country_id", ASCENDING, False),
            ("promotion_flag", ASCENDING, False),
            ("reserva_bool", ASCENDING, False),
            ("occupancy_profile_id", ASCENDING, False),
            ("stay_length_category_id", ASCENDING, False),
            ("booking_window_category_id", ASCENDING, False),
            ("price_category_id", ASCENDING, False),
            ("execution_id", ASCENDING, False),
        ],
        "fact_hotel_reservations": [
            ("srch_id", ASCENDING, False),
            ("date_key", ASCENDING, False),
            ("prop_id", ASCENDING, False),
            ("srch_destination_id", ASCENDING, False),
            ("visitor_location_country_id", ASCENDING, False),
            ("promotion_flag", ASCENDING, False),
            ("reserva_bool", ASCENDING, False),
            ("execution_id", ASCENDING, False),
        ],
        "rejected_records": [
            ("execution_id", ASCENDING, False),
            ("reason", ASCENDING, False),
        ],
        "hotels": [
            ("hotel_code", ASCENDING, True),
            ("hotel_name", ASCENDING, False),
            ("rating", ASCENDING, False),
        ],
        "locations": [
            ("hotel_code", ASCENDING, True),
            ("city_code", ASCENDING, False),
            ("city_name", ASCENDING, False),
            ("county_code", ASCENDING, False),
        ],
        "contacts": [("hotel_code", ASCENDING, True)],
        "websites": [("hotel_code", ASCENDING, True)],
        "facilities": [
            ("hotel_code", ASCENDING, False),
            ("facility", ASCENDING, False),
        ],
        "attractions": [
            ("hotel_code", ASCENDING, False),
            ("attraction", ASCENDING, False),
        ],
        "hotel_quality": [
            ("hotel_code", ASCENDING, True),
            ("quality_level", ASCENDING, False),
        ],
        "dataset_container": [("dataset_id", ASCENDING, True)],
        "data_quality_reports": [("execution_id", ASCENDING, False)],
        "etl_executions": [("execution_id", ASCENDING, True), ("executed_at", ASCENDING, False)],
        "search_logs": [("searched_at", ASCENDING, False)],
        "system_catalogs": [("catalog_type", ASCENDING, False), ("code", ASCENDING, False)],
    }

    created: dict[str, list[str]] = {}
    for collection_name, indexes in index_map.items():
        created[collection_name] = []
        for field, direction, unique in indexes:
            name = db[collection_name].create_index([(field, direction)], unique=unique)
            created[collection_name].append(name)
    return created
