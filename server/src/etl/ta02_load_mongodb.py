from __future__ import annotations

import os
from typing import Any

from pymongo import ASCENDING, UpdateOne
from pymongo.database import Database
from pymongo.errors import OperationFailure

from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS

INSERT_BATCH_SIZE = int(os.getenv("GA03_INSERT_BATCH_SIZE", "5000"))

INDEX_FIELDS = {
    "fact_hotel_reservations": [
        "srch_id",
        "prop_id",
        "srch_destination_id",
        "visitor_location_country_id",
        "date_key",
        "execution_id",
    ],
    "dim_hotels": ["prop_id"],
    "dim_destinations": ["srch_destination_id"],
    "dim_visitor_countries": ["visitor_location_country_id"],
    "dim_sites": ["site_id"],
    "dim_dates": ["date_key"],
    "dim_promotions": ["promotion_flag"],
    "dim_click_status": ["click_bool"],
    "dim_reservation_status": ["reserva_bool"],
}


def create_ta02_indexes(db: Database) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {}
    for collection_name, fields in INDEX_FIELDS.items():
        created[collection_name] = []
        for field in fields:
            try:
                index_name = db[collection_name].create_index([(field, ASCENDING)])
            except OperationFailure as exc:
                if exc.code != 86:
                    raise
                index_name = f"{field}_1"
            created[collection_name].append(index_name)
    return created


def upsert_dimensions(db: Database, dimensions: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    full_reload = os.getenv("GA03_FULL_RELOAD_DIMENSIONS", "true").lower() in {"1", "true", "yes"}
    for collection_name, documents in dimensions.items():
        if not documents:
            counts[collection_name] = 0
            continue
        if full_reload:
            db[collection_name].delete_many({})
            inserted = 0
            for start in range(0, len(documents), INSERT_BATCH_SIZE):
                batch = documents[start:start + INSERT_BATCH_SIZE]
                result = db[collection_name].insert_many(batch, ordered=False)
                inserted += len(result.inserted_ids)
            counts[collection_name] = inserted
        else:
            key_field = DIMENSION_KEY_FIELDS[collection_name]
            operations = [
                UpdateOne({key_field: doc[key_field]}, {"$set": doc}, upsert=True)
                for doc in documents
                if doc.get(key_field) is not None
            ]
            if operations:
                for start in range(0, len(operations), INSERT_BATCH_SIZE):
                    batch = operations[start:start + INSERT_BATCH_SIZE]
                    result = db[collection_name].bulk_write(batch, ordered=False)
                    counts[collection_name] = counts.get(collection_name, 0) + result.upserted_count + result.modified_count + result.matched_count
            else:
                counts[collection_name] = 0
    return counts


def insert_fact_hotel_reservations(db: Database, facts: list[dict[str, Any]]) -> int:
    if not facts:
        return 0
    result = db.fact_hotel_reservations.insert_many(facts, ordered=False)
    return len(result.inserted_ids)


def insert_rejected_records(db: Database, rejected_records: list[dict[str, Any]]) -> int:
    if not rejected_records:
        return 0
    result = db.rejected_records.insert_many(rejected_records, ordered=False)
    return len(result.inserted_ids)


def insert_execution_report(db: Database, execution_report: dict[str, Any]) -> str:
    result = db.etl_executions.insert_one(execution_report)
    return str(result.inserted_id)


def insert_quality_report(db: Database, quality_report: dict[str, Any]) -> str:
    result = db.data_quality_reports.insert_one(quality_report)
    return str(result.inserted_id)


def collection_counts(db: Database, collection_names: list[str]) -> dict[str, int]:
    return {name: db[name].count_documents({}) for name in collection_names}
