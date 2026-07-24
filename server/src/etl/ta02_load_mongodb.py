from __future__ import annotations

import os
from typing import Any

from pymongo import ASCENDING, UpdateOne
from pymongo.database import Database
from pymongo.errors import OperationFailure

from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS

INSERT_BATCH_SIZE = int(os.getenv("GA03_INSERT_BATCH_SIZE", "5000"))

# Fields that the ETL manages for dim_hotels — geo fields are preserved across runs
ETL_HOTEL_FIELDS = {
    "prop_id", "prop_country_id", "prop_starrating", "prop_review_score",
    "prop_brand_bool", "prop_location_score1", "display_name", "loaded_at",
}


def _resolve_geo_country_for_hotels(db: Database, hotels: list[dict[str, Any]]) -> None:
    """Resolve geo_country_code and geo_catalog_id for dim_hotels documents.

    Looks up existing dim_visitor_countries (which may have been manually named
    via the admin API) and matches against geo_catalog to find the country code.
    Hotels without a matching geo_catalog entry are left with None values.
    """
    if not hotels:
        return

    # Collect unique prop_country_ids
    country_ids = set()
    for h in hotels:
        cid = h.get("prop_country_id")
        if cid is not None:
            country_ids.add(int(cid))

    if not country_ids:
        return

    # Look up real country names from dim_visitor_countries (already loaded)
    vid_to_name: dict[int, str] = {}
    for doc in db.dim_visitor_countries.find(
        {"visitor_location_country_id": {"$in": list(country_ids)}},
        {"visitor_location_country_id": 1, "visitor_country_label": 1, "country_display_name": 1, "country_name": 1},
    ):
        vid = doc.get("visitor_location_country_id")
        name = doc.get("country_display_name") or doc.get("country_name") or doc.get("visitor_country_label", "")
        if vid is not None:
            vid_to_name[int(vid)] = name.strip()

    if not vid_to_name:
        return

    # Build geo_catalog country lookup (name → code, name → _id)
    geo_name_to_code: dict[str, str] = {}
    geo_name_to_id: dict[str, object] = {}
    for doc in db.geo_catalog.find({"type": "country"}, {"code": 1, "name": 1}):
        name = doc.get("name", "").strip().lower()
        code = doc.get("code", "")
        if name and code:
            geo_name_to_code[name] = code
            geo_name_to_id[name] = doc["_id"]

    # Resolve for each hotel
    for h in hotels:
        cid = h.get("prop_country_id")
        if cid is None:
            continue
        country_name = vid_to_name.get(int(cid), "").strip().lower()
        if country_name and country_name in geo_name_to_code:
            h["geo_country_code"] = geo_name_to_code[country_name]
            h["geo_catalog_id"] = geo_name_to_id[country_name]
        else:
            # Clear if previously set but no longer resolvable
            h["geo_country_code"] = None
            h["geo_catalog_id"] = None

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


def upsert_dimensions(db: Database, dimensions: dict[str, list[dict[str, Any]]], *, full_reload: bool | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    if full_reload is None:
        full_reload = os.getenv("GA03_FULL_RELOAD_DIMENSIONS", "true").lower() in {"1", "true", "yes"}

    # Resolve geo_country_code for dim_hotels before loading (reads existing dim_visitor_countries)
    if "dim_hotels" in dimensions:
        _resolve_geo_country_for_hotels(db, dimensions["dim_hotels"])

    for collection_name, documents in dimensions.items():
        if not documents:
            counts[collection_name] = 0
            continue
        if full_reload:
            # Preserve manual overrides before wiping (hotel profile edits only —
            # geo fields are already resolved by _resolve_geo_country_for_hotels above)
            preserved_overrides: list[dict[str, Any]] = []
            if collection_name == "dim_hotels":
                preserved_overrides = list(
                    db[collection_name].find(
                        {"manual_override": True},
                        {"_id": 0},
                    )
                )
            db[collection_name].delete_many({})
            inserted = 0
            for start in range(0, len(documents), INSERT_BATCH_SIZE):
                batch = documents[start:start + INSERT_BATCH_SIZE]
                result = db[collection_name].insert_many(batch, ordered=False)
                inserted += len(result.inserted_ids)
            # Reapply manual overrides after reload
            for override in preserved_overrides:
                prop_id = override.get("prop_id")
                if prop_id is not None:
                    db[collection_name].update_one(
                        {"prop_id": prop_id},
                        {"$set": override},
                        upsert=True,
                    )
            counts[collection_name] = inserted
        else:
            key_field = DIMENSION_KEY_FIELDS[collection_name]
            if collection_name == "dim_hotels":
                # For dim_hotels, only $set ETL-managed fields — preserve geo fields
                operations = [
                    UpdateOne(
                        {key_field: doc[key_field]},
                        {"$set": {k: v for k, v in doc.items() if k in ETL_HOTEL_FIELDS}},
                        upsert=True,
                    )
                    for doc in documents
                    if doc.get(key_field) is not None
                ]
                # Also set geo fields if resolved (only for existing docs — new docs get them via upsert below)
                geo_ops = [
                    UpdateOne(
                        {key_field: doc[key_field]},
                        {"$set": {"geo_country_code": doc.get("geo_country_code"), "geo_catalog_id": doc.get("geo_catalog_id")}},
                        upsert=False,
                    )
                    for doc in documents
                    if doc.get(key_field) is not None and (doc.get("geo_country_code") or doc.get("geo_catalog_id"))
                ]
            else:
                operations = [
                    UpdateOne({key_field: doc[key_field]}, {"$set": doc}, upsert=True)
                    for doc in documents
                    if doc.get(key_field) is not None
                ]
                geo_ops = []
            if operations:
                for start in range(0, len(operations), INSERT_BATCH_SIZE):
                    batch = operations[start:start + INSERT_BATCH_SIZE]
                    result = db[collection_name].bulk_write(batch, ordered=False)
                    counts[collection_name] = counts.get(collection_name, 0) + result.upserted_count + result.modified_count + result.matched_count
                # Apply geo field updates separately (not upserts, only for existing docs)
                if geo_ops:
                    for start in range(0, len(geo_ops), INSERT_BATCH_SIZE):
                        geo_batch = geo_ops[start:start + INSERT_BATCH_SIZE]
                        db[collection_name].bulk_write(geo_batch, ordered=False)
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
