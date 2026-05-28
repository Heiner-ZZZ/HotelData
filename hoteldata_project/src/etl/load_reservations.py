from __future__ import annotations

import json
from pathlib import Path

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.reservations import DIMENSION_COLLECTIONS


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _insert_jsonl_batches(collection, path: Path, batch_size: int) -> int:
    inserted = 0
    batch = []
    for document in _iter_jsonl(path):
        batch.append(document)
        if len(batch) >= batch_size:
            collection.insert_many(batch, ordered=False)
            inserted += len(batch)
            batch = []
    if batch:
        collection.insert_many(batch, ordered=False)
        inserted += len(batch)
    return inserted


def load_reservation_dimensions() -> dict[str, int]:
    settings = get_settings()
    db = get_database()
    if settings.full_reload:
        for collection_name in DIMENSION_COLLECTIONS:
            db[collection_name].delete_many({})

    inserted = {}
    for collection_name in DIMENSION_COLLECTIONS:
        inserted[collection_name] = _insert_jsonl_batches(
            db[collection_name],
            settings.processed_dir / f"{collection_name}.jsonl",
            settings.batch_size,
        )
    return inserted


def load_fact_hotel_reservations() -> dict[str, int]:
    settings = get_settings()
    db = get_database()
    if settings.full_reload:
        db.fact_hotel_reservations.delete_many({})
    inserted = _insert_jsonl_batches(
        db.fact_hotel_reservations,
        settings.processed_dir / "fact_hotel_reservations.jsonl",
        settings.batch_size,
    )
    return {"fact_hotel_reservations": inserted}
