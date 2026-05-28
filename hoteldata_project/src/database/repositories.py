from __future__ import annotations

from pymongo.database import Database


MASTER_COLLECTIONS = [
    "dim_hotels",
    "dim_destinations",
    "dim_visitor_countries",
    "dim_dates",
    "dim_promotions",
    "dim_reservation_status",
    "dim_occupancy_profile",
    "dim_stay_length_category",
    "dim_booking_window_category",
    "dim_price_category",
]

FACT_COLLECTIONS = [
    "fact_hotel_events",
    "fact_hotel_reservations",
]

REJECTED_COLLECTIONS = [
    "rejected_records",
]

DATASET_COLLECTIONS = FACT_COLLECTIONS

PROTECTED_COLLECTIONS = [
    "search_logs",
    "system_catalogs",
    "etl_executions",
    "data_quality_reports",
    *MASTER_COLLECTIONS,
]


def truncate_dataset_collections(db: Database) -> None:
    for collection_name in DATASET_COLLECTIONS:
        db[collection_name].delete_many({})
