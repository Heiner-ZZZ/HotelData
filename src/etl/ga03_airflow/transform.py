from __future__ import annotations

from typing import Any

import pandas as pd

from src.database.connection import get_database
from src.etl.ga03_airflow._common import (
    existing_dimensions_ready,
    reuse_existing_dimensions_enabled,
    write_jsonl,
)
from src.etl.ga03_airflow.config import PHASE, PIPELINE_PROGRESS_STEPS, paths
from src.etl.ga03_airflow.progress import write_pipeline_progress, read_state, write_state
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS, build_ta02_dimensions
from src.etl.ga03_audit import utc_now_iso
from src.etl.ta02_fact import transform_fact_hotel_reservations


def transform_dimensions_03() -> dict[str, int]:
    all_paths = paths()
    state = read_state()
    db = get_database()
    dimensions_ready, existing_counts = existing_dimensions_ready(db)
    if reuse_existing_dimensions_enabled() and dimensions_ready:
        message = "Dimensiones existentes detectadas; transformación de dimensiones omitida."
        write_pipeline_progress(
            status="running",
            section="transform",
            percent=58,
            message=message,
            detail={"skipped": True, "dimension_counts": existing_counts},
        )
        write_state(
            {
                "dimension_counts": existing_counts,
                "dimension_transform_skipped": True,
                "dimension_skip_reason": message,
            }
        )
        return existing_counts
    dataframe = pd.read_parquet(all_paths["parquet"])
    _, _, valid_fact_frame = transform_fact_hotel_reservations(dataframe, state["execution_id"], state["loaded_at"])
    dimensions = build_ta02_dimensions(valid_fact_frame, state["loaded_at"])
    counts = {}
    total_dimensions = max(len(DIMENSION_KEY_FIELDS), 1)
    for collection_name, documents in dimensions.items():
        counts[collection_name] = write_jsonl(all_paths["dimension_dir"] / f"{collection_name}.jsonl", documents)
        progress = 50 + (len(counts) / total_dimensions) * 8
        write_pipeline_progress(
            status="running",
            section="transform",
            percent=progress,
            message="Transformando dimensiones.",
            detail={"dimension": collection_name, "count": counts[collection_name], "processed_dimensions": len(counts)},
        )
    write_state({"dimension_counts": counts})
    return counts


def transform_fact_reservations_03() -> dict[str, int]:
    all_paths = paths()
    state = read_state()
    expected = int(state["expected_records"])
    parquet_report = state.get("parquet_report", {})
    from src.etl.ga03_airflow._common import read_json_file, file_sha256
    fact_meta = read_json_file(all_paths["fact_meta"])
    fact_cache_valid = (
        all_paths["fact_jsonl"].exists()
        and all_paths["rejected_jsonl"].exists()
        and fact_meta.get("parquet_sha256") == parquet_report.get("parquet_sha256")
        and int(fact_meta.get("fact_hotel_reservations", -1)) == expected
        and int(fact_meta.get("rejected_records", -1)) == 0
        and int(fact_meta.get("fact_jsonl_bytes", -1)) == all_paths["fact_jsonl"].stat().st_size
        and int(fact_meta.get("rejected_jsonl_bytes", -1)) == all_paths["rejected_jsonl"].stat().st_size
    )
    if fact_cache_valid:
        report = {
            "fact_hotel_reservations": expected,
            "rejected_records": 0,
            "cached": True,
        }
        write_pipeline_progress(
            status="running",
            section="transform",
            percent=PIPELINE_PROGRESS_STEPS["transform"],
            message="Hecho transformado existente validado y reutilizado.",
            detail=report,
        )
        write_state({"fact_transform_counts": report})
        return report
    write_pipeline_progress(
        status="running",
        section="transform",
        percent=60,
        message="Transformando hecho fact_hotel_reservations.",
        detail={"fact_collection": "fact_hotel_reservations"},
    )
    dataframe = pd.read_parquet(all_paths["parquet"])
    facts, rejected, _ = transform_fact_hotel_reservations(dataframe, state["execution_id"], state["loaded_at"])
    for document in facts:
        document["phase"] = PHASE
    for document in rejected:
        document["phase"] = PHASE
    fact_count = write_jsonl(all_paths["fact_jsonl"], facts)
    rejected_count = write_jsonl(all_paths["rejected_jsonl"], rejected)
    if fact_count != expected or rejected_count != 0:
        raise ValueError(f"Transformacion GA03 invalida: hechos={fact_count}, rechazados={rejected_count}, esperado={expected}")
    report = {"fact_hotel_reservations": fact_count, "rejected_records": rejected_count, "cached": False}
    from src.etl.ga03_airflow._common import write_json_file, file_sha256
    write_json_file(
        all_paths["fact_meta"],
        {
            "fact_hotel_reservations": fact_count,
            "rejected_records": rejected_count,
            "fact_jsonl_bytes": all_paths["fact_jsonl"].stat().st_size,
            "rejected_jsonl_bytes": all_paths["rejected_jsonl"].stat().st_size,
            "fact_jsonl_sha256": file_sha256(all_paths["fact_jsonl"]),
            "rejected_jsonl_sha256": file_sha256(all_paths["rejected_jsonl"]),
            "parquet_sha256": parquet_report.get("parquet_sha256"),
            "collection": state.get("extract_report", {}).get("collection"),
            "expected_records": expected,
            "created_at": utc_now_iso(),
        },
    )
    write_pipeline_progress(
        status="running",
        section="transform",
        percent=PIPELINE_PROGRESS_STEPS["transform"],
        message="Transformación de hecho completada.",
        detail=report,
    )
    write_state({"fact_transform_counts": report})
    return report
