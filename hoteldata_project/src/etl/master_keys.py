from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config.settings import get_settings
from src.database.connection import get_database


def _load_key_set(collection_name: str, field_name: str) -> set[int]:
    db = get_database()
    return {item[field_name] for item in db[collection_name].find({}, {field_name: 1, "_id": 0})}


def _append_jsonl(path: Path, documents: list[dict]) -> int:
    if not documents:
        return 0
    with path.open("a", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False) + "\n")
    return len(documents)


def seed_master_collections_check() -> dict:
    db = get_database()
    required = {
        "dim_hotels": db.dim_hotels.count_documents({}),
        "dim_destinations": db.dim_destinations.count_documents({}),
        "dim_visitor_countries": db.dim_visitor_countries.count_documents({}),
        "dim_dates": db.dim_dates.count_documents({}),
        "dim_promotions": db.dim_promotions.count_documents({}),
        "dim_reservation_status": db.dim_reservation_status.count_documents({}),
        "dim_stay_length_category": db.dim_stay_length_category.count_documents({}),
        "dim_booking_window_category": db.dim_booking_window_category.count_documents({}),
        "dim_price_category": db.dim_price_category.count_documents({}),
    }
    empty = [name for name, count in required.items() if count == 0]
    if empty:
        raise ValueError(
            "Master collections must be seeded before running ETL. "
            f"Empty collections: {empty}. Run scripts/seed_master_collections.py"
        )
    return required


def validate_master_keys() -> dict:
    settings = get_settings()
    candidate_path = settings.processed_dir / "fact_hotel_events_candidate.jsonl"
    valid_path = settings.processed_dir / "fact_hotel_events.jsonl"
    rejected_path = settings.processed_dir / "rejected_records_keys.jsonl"
    for path in [valid_path, rejected_path]:
        if path.exists():
            path.unlink()

    hotel_keys = _load_key_set("dim_hotels", "prop_id")
    destination_keys = _load_key_set("dim_destinations", "srch_destination_id")
    country_keys = _load_key_set("dim_visitor_countries", "visitor_location_country_id")
    date_keys = _load_key_set("dim_dates", "date_key")
    promotion_keys = _load_key_set("dim_promotions", "promotion_flag")
    reservation_keys = _load_key_set("dim_reservation_status", "reserva_bool")
    occupancy_keys = _load_key_set("dim_occupancy_profile", "occupancy_profile_id")
    stay_keys = _load_key_set("dim_stay_length_category", "stay_length_category_id")
    booking_window_keys = _load_key_set("dim_booking_window_category", "booking_window_category_id")
    price_keys = _load_key_set("dim_price_category", "price_category_id")

    valid_count = 0
    rejected_count = 0
    loaded_at = datetime.now(timezone.utc).isoformat()
    valid_batch = []
    rejected_batch = []

    with candidate_path.open("r", encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            document = json.loads(line)
            reasons = []
            if document["prop_id"] not in hotel_keys:
                reasons.append("missing_dim_hotels.prop_id")
            if document["srch_destination_id"] not in destination_keys:
                reasons.append("missing_dim_destinations.srch_destination_id")
            if document["visitor_location_country_id"] not in country_keys:
                reasons.append("missing_dim_visitor_countries.visitor_location_country_id")
            if document["date_key"] not in date_keys:
                reasons.append("missing_dim_dates.date_key")
            if document["promotion_flag"] not in promotion_keys:
                reasons.append("missing_dim_promotions.promotion_flag")
            if document["reserva_bool"] not in reservation_keys:
                reasons.append("missing_dim_reservation_status.reserva_bool")
            if document.get("occupancy_profile_id") is not None and document["occupancy_profile_id"] not in occupancy_keys:
                reasons.append("missing_dim_occupancy_profile.occupancy_profile_id")
            if document.get("stay_length_category_id") is not None and document["stay_length_category_id"] not in stay_keys:
                reasons.append("missing_dim_stay_length_category.stay_length_category_id")
            if document.get("booking_window_category_id") is not None and document["booking_window_category_id"] not in booking_window_keys:
                reasons.append("missing_dim_booking_window_category.booking_window_category_id")
            if document.get("price_category_id") is not None and document["price_category_id"] not in price_keys:
                reasons.append("missing_dim_price_category.price_category_id")

            if reasons:
                rejected_batch.append({
                    "reason": "invalid_master_key",
                    "details": reasons,
                    "raw_record": document,
                    "loaded_at": loaded_at,
                    "execution_id": document["execution_id"],
                })
            else:
                valid_batch.append(document)

            if len(valid_batch) >= settings.batch_size:
                valid_count += _append_jsonl(valid_path, valid_batch)
                valid_batch = []
            if len(rejected_batch) >= settings.batch_size:
                rejected_count += _append_jsonl(rejected_path, rejected_batch)
                rejected_batch = []

    valid_count += _append_jsonl(valid_path, valid_batch)
    rejected_count += _append_jsonl(rejected_path, rejected_batch)
    return {
        "valid_records": valid_count,
        "master_key_rejected_records": rejected_count,
        "valid_path": str(valid_path),
        "master_key_rejected_path": str(rejected_path),
    }
