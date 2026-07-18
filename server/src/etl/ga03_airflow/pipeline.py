from __future__ import annotations

import time
from typing import Any

from src.etl.ga03_airflow import config
from src.etl.ga03_airflow.bootstrap import validate_environment_03
from src.etl.ga03_airflow.extract import extract_from_pocketbase_03, save_extract_jsonl_03
from src.etl.ga03_airflow.load import (
    create_indexes_03,
    load_dimensions_to_mongodb_03,
    load_fact_to_mongodb_03,
)
from src.etl.ga03_airflow.parquet import convert_to_parquet_03, validate_parquet_schema_03
from src.etl.ga03_airflow.progress import write_pipeline_progress
from src.etl.ga03_airflow.reports import run_quality_checks_03, save_execution_report_03
from src.etl.ga03_airflow.transform import transform_dimensions_03, transform_fact_reservations_03


def run_pipeline_03() -> dict[str, Any]:
    config.PIPELINE_STARTED_MONO = time.perf_counter()
    try:
        validate_environment_03()
        extract_from_pocketbase_03()
        save_extract_jsonl_03()
        convert_to_parquet_03()
        validate_parquet_schema_03()
        transform_dimensions_03()
        transform_fact_reservations_03()
        load_dimensions_to_mongodb_03()
        load_fact_to_mongodb_03()
        create_indexes_03()
        run_quality_checks_03()
        return save_execution_report_03()
    except Exception as exc:
        write_pipeline_progress(
            status="failed",
            section="error",
            percent=0,
            message=str(exc),
            detail={"error_type": type(exc).__name__},
        )
        raise
