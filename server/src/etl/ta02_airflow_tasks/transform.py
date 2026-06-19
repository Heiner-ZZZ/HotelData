from __future__ import annotations

from typing import Any

import pandas as pd

from src.etl.ta02_airflow_tasks._state import _paths, _read_state, _write_state, _write_jsonl
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS, build_ta02_dimensions
from src.etl.ta02_fact import REQUIRED_FACT_COLUMNS, transform_fact_hotel_reservations


def convert_to_parquet() -> dict[str, Any]:
    paths = _paths()
    if not paths["extract_jsonl"].exists():
        raise FileNotFoundError(f"No existe JSONL de extraccion: {paths['extract_jsonl']}")
    dataframe = pd.read_json(paths["extract_jsonl"], lines=True, dtype=False)
    dataframe.to_parquet(paths["parquet"], index=False)
    report = {"records": len(dataframe), "columns": list(dataframe.columns), "parquet_path": str(paths["parquet"])}
    _write_state({"parquet_report": report})
    return report


def validate_parquet_schema() -> dict[str, Any]:
    paths = _paths()
    if not paths["parquet"].exists():
        raise FileNotFoundError(f"No existe Parquet: {paths['parquet']}")
    dataframe = pd.read_parquet(paths["parquet"])
    missing = [column for column in REQUIRED_FACT_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Parquet TA 02 sin columnas requeridas: {missing}")
    report = {"valid": True, "records": len(dataframe), "columns": list(dataframe.columns)}
    _write_state({"schema_report": report})
    return report


def transform_dimensions() -> dict[str, int]:
    paths = _paths()
    state = _read_state()
    dataframe = pd.read_parquet(paths["parquet"])
    _, _, valid_fact_frame = transform_fact_hotel_reservations(
        dataframe,
        state["execution_id"],
        state["loaded_at"],
    )
    dimensions = build_ta02_dimensions(valid_fact_frame, state["loaded_at"])
    counts = {}
    for collection_name, documents in dimensions.items():
        counts[collection_name] = _write_jsonl(paths["dimension_dir"] / f"{collection_name}.jsonl", documents)
    _write_state({"dimension_counts": counts})
    return counts


def transform_fact_reservations() -> dict[str, int]:
    paths = _paths()
    state = _read_state()
    dataframe = pd.read_parquet(paths["parquet"])
    facts, rejected, _ = transform_fact_hotel_reservations(dataframe, state["execution_id"], state["loaded_at"])
    fact_count = _write_jsonl(paths["fact_jsonl"], facts)
    rejected_count = _write_jsonl(paths["rejected_jsonl"], rejected)
    report = {"fact_hotel_reservations": fact_count, "rejected_records": rejected_count}
    _write_state({"fact_transform_counts": report})
    return report
