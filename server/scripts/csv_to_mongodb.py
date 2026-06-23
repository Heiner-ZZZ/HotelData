from __future__ import annotations

import math
import os
from typing import Any

import pandas as pd
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "hoteldata_hub")
CSV_PATH = os.getenv("GA03_SOURCE_CSV", "data/uploads/ga03_source.csv")
TARGET = int(os.getenv("TARGET_RECORDS", "300000"))
BATCH_SIZE = 5000

BOOL_FIELDS = {"prop_brand_bool", "promotion_flag", "click_bool", "reserva_bool"}
NUMBER_FIELDS = {
    "srch_id", "site_id", "visitor_location_country_id",
    "visitor_hist_starrating", "visitor_hist_adr_usd",
    "prop_country_id", "prop_id", "prop_starrating", "prop_review_score",
    "prop_location_score1", "price_usd", "srch_destination_id",
    "srch_length_of_stay", "srch_booking_window", "srch_adults_count",
    "srch_children_count", "srch_room_count", "reservas_brutas_usd",
}


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for field, value in row.items():
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        if field in BOOL_FIELDS:
            cleaned[field] = bool(int(value)) if not isinstance(value, bool) else value
        elif field in NUMBER_FIELDS:
            cleaned[field] = float(value)
        else:
            cleaned[field] = str(value)
    return cleaned


def main():
    csv_path = CSV_PATH
    if not os.path.isabs(csv_path):
        root = os.getenv("HOTELDATA_PROJECT_ROOT", ".")
        csv_path = os.path.join(root, csv_path)

    print(f"Connecting to {MONGO_URI}/{MONGO_DB}")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    print(f"Reading {TARGET} records from {csv_path}")
    chunks = pd.read_csv(csv_path, chunksize=BATCH_SIZE, nrows=TARGET)
    total = 0
    for i, chunk in enumerate(chunks):
        rows = chunk.to_dict("records")
        batch = [clean_row(r) for r in rows]
        try:
            db["fact_hotel_events"].insert_many(batch, ordered=False)
        except Exception as e:
            print(f"Batch {i} insert error: {e}")
        total += len(batch)
        print(f"Imported {total}/{TARGET}", flush=True)
        if total >= TARGET:
            break

    print(f"\nDone! {total} records -> fact_hotel_events")

    prop_ids = db.fact_hotel_events.distinct("prop_id")
    print(f"Distinct prop_ids: {len(prop_ids)}")

    existing = set(d["prop_id"] for d in db.dim_hotels.find({}, {"prop_id": 1, "_id": 0}))
    new_ids = [pid for pid in prop_ids if pid not in existing]
    if new_ids:
        docs = [{"prop_id": int(pid), "hotel_name": f"Hotel {int(pid)}", "display_name": f"Hotel {int(pid)}"} for pid in new_ids[:100]]
        if docs:
            db.dim_hotels.insert_many(docs, ordered=False)
            print(f"Created {len(docs)} dim_hotels entries")
    print(f"Total dim_hotels: {db.dim_hotels.count_documents({})}")


if __name__ == "__main__":
    main()
