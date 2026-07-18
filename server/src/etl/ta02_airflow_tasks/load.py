from __future__ import annotations

import os
from typing import Any

from pymongo import UpdateOne

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.ta02_airflow_tasks._state import _count_jsonl, _iter_jsonl, _paths, _write_state
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS
from src.etl.ta02_load_mongodb import (
    create_ta02_indexes,
    insert_rejected_records,
    upsert_dimensions,
)

INSERT_BATCH_SIZE = 5000


def _insert_fact_jsonl(db, path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    inserted = 0
    batch: list[dict[str, Any]] = []
    for document in _iter_jsonl(path):
        batch.append(document)
        if len(batch) >= batch_size:
            result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
            batch = []
            print(f"Hechos insertados: {inserted}")
    if batch:
        result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
    return inserted


def _upsert_fact_jsonl_by_source_record_id(db, path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    processed = 0
    operations = []
    for document in _iter_jsonl(path):
        source_record_id = document.get("source_record_id")
        if source_record_id is None:
            raise ValueError("No se puede hacer upsert del hecho sin source_record_id")
        operations.append(
            UpdateOne(
                {"source_record_id": source_record_id},
                {"$set": document},
                upsert=True,
            )
        )
        if len(operations) >= batch_size:
            db.fact_hotel_reservations.bulk_write(operations, ordered=False)
            processed += len(operations)
            operations = []
            print(f"Hechos procesados por upsert: {processed}")
    if operations:
        db.fact_hotel_reservations.bulk_write(operations, ordered=False)
        processed += len(operations)
    return processed


def load_dimensions_to_mongodb() -> dict[str, int]:
    paths = _paths()
    dimensions: dict[str, list[dict[str, Any]]] = {}
    for collection_name in DIMENSION_KEY_FIELDS:
        dimensions[collection_name] = list(_iter_jsonl(paths["dimension_dir"] / f"{collection_name}.jsonl") or [])
    counts = upsert_dimensions(get_database(), dimensions)
    _write_state({"dimension_load_counts": counts})
    return counts


def load_fact_to_mongodb() -> dict[str, int]:
    paths = _paths()
    db = get_database()
    settings = get_settings()
    full_reload = settings.full_reload or os.getenv("TA02_FULL_RELOAD_FACTS", "true").lower() == "true"
    previous_count = db.fact_hotel_reservations.count_documents({})
    expected_new_count = _count_jsonl(paths["fact_jsonl"])
    deleted = 0

    print(f"Conteo anterior de fact_hotel_reservations: {previous_count}")
    print(f"Full reload de hechos habilitado: {full_reload}")
    print(f"Conteo final esperado de fact_hotel_reservations: {expected_new_count if full_reload else 'sin duplicados por upsert'}")

    if full_reload:
        deleted = db.fact_hotel_reservations.delete_many({}).deleted_count
        print(f"Limpieza ejecutada sobre fact_hotel_reservations: {deleted} documentos borrados")
        fact_count = _insert_fact_jsonl(db, paths["fact_jsonl"])
    else:
        print("Limpieza no ejecutada. Se usara upsert por source_record_id para evitar duplicados.")
        db.fact_hotel_reservations.create_index("source_record_id")
        fact_count = _upsert_fact_jsonl_by_source_record_id(db, paths["fact_jsonl"])

    final_count = db.fact_hotel_reservations.count_documents({})
    print(f"Conteo final de fact_hotel_reservations: {final_count}")
    if full_reload and final_count != expected_new_count:
        raise RuntimeError(
            "Conteo final inesperado en fact_hotel_reservations: "
            f"esperado={expected_new_count}, actual={final_count}"
        )

    rejected = list(_iter_jsonl(paths["rejected_jsonl"]) or [])
    rejected_count = insert_rejected_records(db, rejected)
    counts = {
        "previous_fact_hotel_reservations": previous_count,
        "deleted_facts_before_load": deleted,
        "fact_hotel_reservations": fact_count,
        "expected_fact_hotel_reservations": expected_new_count,
        "final_fact_hotel_reservations": final_count,
        "rejected_records": rejected_count,
    }
    _write_state({"fact_load_counts": counts})
    return counts


def create_indexes() -> dict[str, list[str]]:
    result = create_ta02_indexes(get_database())
    _write_state({"indexes": result})
    return result
