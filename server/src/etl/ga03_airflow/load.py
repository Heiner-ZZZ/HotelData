from __future__ import annotations

import os
from typing import Any

from pymongo import UpdateOne

from src.database.connection import get_database
from src.etl.ga03_airflow._common import (
    count_jsonl,
    dimension_collection_counts,
    dimension_jsonl_counts,
    iter_jsonl,
)
from src.etl.ga03_airflow.config import INSERT_BATCH_SIZE, PHASE, PIPELINE_PROGRESS_STEPS, paths
from src.etl.ga03_airflow.progress import write_pipeline_progress, read_state, write_state
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS
from src.etl.ta02_load_mongodb import create_ta02_indexes, upsert_dimensions


def _insert_fact_jsonl(db, path: Path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    from pathlib import Path
    inserted = 0
    batch: list[dict[str, Any]] = []
    expected = int(read_state().get("expected_records", 0) or 0)
    for document in iter_jsonl(path):
        document["phase"] = PHASE
        batch.append(document)
        if len(batch) >= batch_size:
            result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
            batch = []
            print(f"GA03 hechos insertados: {inserted}")
            load_percent = 76 + ((inserted / expected) * 12 if expected else 0)
            write_pipeline_progress(
                status="running",
                section="load_mongodb",
                percent=min(load_percent, PIPELINE_PROGRESS_STEPS["load_mongodb"]),
                message="Cargando hecho en MongoDB.",
                detail={"inserted": inserted, "expected_records": expected, "elapsed_ms": 0},
            )
    if batch:
        result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
        write_pipeline_progress(
            status="running",
            section="load_mongodb",
            percent=PIPELINE_PROGRESS_STEPS["load_mongodb"],
            message="Cargando hecho en MongoDB.",
            detail={"inserted": inserted, "expected_records": expected, "elapsed_ms": 0},
        )
    return inserted


def _upsert_fact_jsonl_by_source_record_id(db, path: Path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    processed = 0
    operations: list[UpdateOne] = []
    for document in iter_jsonl(path):
        source_record_id = document.get("source_record_id")
        if source_record_id is None:
            raise ValueError("GA03 no puede hacer upsert sin source_record_id")
        document["phase"] = PHASE
        operations.append(UpdateOne({"source_record_id": source_record_id}, {"$set": document}, upsert=True))
        if len(operations) >= batch_size:
            db.fact_hotel_reservations.bulk_write(operations, ordered=False)
            processed += len(operations)
            operations = []
            print(f"GA03 hechos procesados por upsert: {processed}")
    if operations:
        db.fact_hotel_reservations.bulk_write(operations, ordered=False)
        processed += len(operations)
    return processed


def load_dimensions_to_mongodb_03() -> dict[str, int]:
    all_paths = paths()
    db = get_database()
    state = read_state()
    incremental = bool(state.get("last_extracted_at"))

    jsonl_counts = dimension_jsonl_counts(all_paths)
    mongo_counts = dimension_collection_counts(db)

    if not incremental:
        needs_load = not all(
            jsonl_counts.get(name, 0) > 0 and mongo_counts.get(name, 0) >= jsonl_counts.get(name, 0)
            for name in DIMENSION_KEY_FIELDS
        )
        if not needs_load:
            message = "Dimensiones en MongoDB ya tienen los registros esperados; carga omitida."
            write_pipeline_progress(
                status="running",
                section="load_mongodb",
                percent=72,
                message=message,
                detail={"skipped": True, "dimension_counts": mongo_counts},
            )
            write_state(
                {
                    "dimension_load_counts": mongo_counts,
                    "dimension_load_skipped": True,
                    "dimension_load_skip_reason": message,
                }
            )
            return mongo_counts
    else:
        print(f"GA03 incremental: cargando dimensiones con upsert")

    dimensions: dict[str, list[dict[str, Any]]] = {}
    for collection_name in DIMENSION_KEY_FIELDS:
        dimensions[collection_name] = list(iter_jsonl(all_paths["dimension_dir"] / f"{collection_name}.jsonl") or [])
    counts = upsert_dimensions(db, dimensions, full_reload=False if incremental else None)
    write_pipeline_progress(
        status="running",
        section="load_mongodb",
        percent=72,
        message="Dimensiones cargadas en MongoDB.",
        detail=counts,
    )
    write_state({"dimension_load_counts": counts})
    return counts


def load_fact_to_mongodb_03() -> dict[str, int]:
    all_paths = paths()
    db = get_database()
    state = read_state()
    expected = int(state["expected_records"])
    incremental = bool(state.get("last_extracted_at"))
    full_reload_env = os.getenv("GA03_FULL_RELOAD_FACTS", "true").lower() == "true"
    full_reload = full_reload_env and not incremental
    previous_count = db.fact_hotel_reservations.count_documents({})
    expected_new_count = count_jsonl(all_paths["fact_jsonl"])
    if expected_new_count != expected:
        raise ValueError(f"JSONL hecho GA03 esperado={expected}, actual={expected_new_count}")
    deleted = 0
    print(f"GA03 conteo anterior fact_hotel_reservations: {previous_count}")
    if full_reload:
        deleted = db.fact_hotel_reservations.delete_many({}).deleted_count
        write_pipeline_progress(
            status="running",
            section="load_mongodb",
            percent=76,
            message="Hecho anterior limpiado para full reload.",
            detail={"deleted": deleted, "previous_count": previous_count},
        )
        fact_count = _insert_fact_jsonl(db, all_paths["fact_jsonl"])
    else:
        db.fact_hotel_reservations.create_index("source_record_id")
        fact_count = _upsert_fact_jsonl_by_source_record_id(db, all_paths["fact_jsonl"])
    rejected_count = count_jsonl(all_paths["rejected_jsonl"])
    if rejected_count:
        rejected_batch = []
        for rejected in iter_jsonl(all_paths["rejected_jsonl"]):
            rejected["phase"] = PHASE
            rejected_batch.append(rejected)
        if rejected_batch:
            db.rejected_records.insert_many(rejected_batch, ordered=False)
    final_count = db.fact_hotel_reservations.count_documents({})
    if full_reload:
        if final_count != expected:
            raise RuntimeError(f"GA03 conteo final inesperado: esperado={expected}, actual={final_count}")
    else:
        if final_count < previous_count:
            raise RuntimeError(f"GA03 conteo final decrecio: previo={previous_count}, actual={final_count}")
    counts = {
        "previous_fact_hotel_reservations": previous_count,
        "deleted_facts_before_load": deleted,
        "fact_hotel_reservations": fact_count,
        "expected_fact_hotel_reservations": expected_new_count,
        "final_fact_hotel_reservations": final_count,
        "rejected_records": rejected_count,
        "incremental": incremental,
    }
    write_pipeline_progress(
        status="running",
        section="load_mongodb",
        percent=PIPELINE_PROGRESS_STEPS["load_mongodb"],
        message="Carga de hecho en MongoDB completada.",
        detail=counts,
    )
    write_state({"fact_load_counts": counts})
    return counts


def create_indexes_03() -> dict[str, list[str]]:
    result = create_ta02_indexes(get_database())
    write_pipeline_progress(
        status="running",
        section="reports",
        percent=92,
        message="Índices MongoDB creados.",
        detail=result,
    )
    write_state({"indexes": result})
    return result
