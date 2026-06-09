from __future__ import annotations

import json
from pathlib import Path

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.transform_collections import BUSINESS_COLLECTIONS


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


def load_fact_events() -> dict[str, int]:
    from config.settings import get_settings

    settings = get_settings()
    db = get_database()
    if settings.full_reload:
        db.fact_hotel_events.delete_many({})
    path = settings.processed_dir / "fact_hotel_events.jsonl"
    return {"fact_hotel_events": _insert_jsonl_batches(db.fact_hotel_events, path, settings.batch_size)}


def load_rejected_records() -> dict[str, int]:
    from config.settings import get_settings

    settings = get_settings()
    db = get_database()
    paths = [
        settings.processed_dir / "rejected_records_transform.jsonl",
        settings.processed_dir / "rejected_records_keys.jsonl",
    ]
    inserted = 0
    for path in paths:
        inserted += _insert_jsonl_batches(db.rejected_records, path, settings.batch_size)
    return {"rejected_records": inserted}


def load_business_collections() -> dict[str, int]:
    settings = get_settings()
    db = get_database()
    if settings.full_reload:
        for collection_name in BUSINESS_COLLECTIONS:
            db[collection_name].delete_many({})

    inserted: dict[str, int] = {}
    for collection_name in BUSINESS_COLLECTIONS:
        path = settings.processed_dir / f"{collection_name}.jsonl"
        inserted[collection_name] = _insert_jsonl_batches(db[collection_name], path, settings.batch_size)
    return inserted
