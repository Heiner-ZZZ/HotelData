from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config.settings import get_settings


PHASE = "GA03"
INSERT_BATCH_SIZE = 5000
PIPELINE_PROGRESS_STEPS = {
    "environment": 5,
    "extract": 30,
    "parquet": 45,
    "transform": 65,
    "load_mongodb": 88,
    "reports": 100,
}

PIPELINE_STARTED_MONO: float | None = None


def paths() -> dict[str, Path]:
    settings = get_settings()
    dimension_dir = settings.processed_dir / "ga03_dimensions"
    return {
        "state": settings.staging_dir / "ga03_execution_state.json",
        "extract_jsonl": settings.staging_dir / "reservas_hoteleras_03_extract.jsonl",
        "parquet": settings.processed_dir / "reservas_hoteleras_03.parquet",
        "fact_jsonl": settings.processed_dir / "fact_hotel_reservations_ga03.jsonl",
        "rejected_jsonl": settings.processed_dir / "rejected_records_ga03.jsonl",
        "dimension_dir": dimension_dir,
        "parquet_meta": settings.processed_dir / "reservas_hoteleras_03.parquet.meta.json",
        "fact_meta": settings.processed_dir / "fact_hotel_reservations_ga03.meta.json",
        "quality_report": settings.reports_dir / "reporte_calidad_reservas_03.json",
        "execution_report": settings.reports_dir / "reporte_ejecucion_reservas_03.json",
        "pipeline_progress": settings.reports_dir / "progreso_pipeline_reservas_03.json",
    }


def pocketbase_config() -> dict[str, str | int | None]:
    settings = get_settings()
    expected = settings.target_records
    return {
        "base_url": settings.pocketbase_url,
        "collection": settings.pocketbase_collection_03,
        "page_size": settings.pocketbase_page_size,
        "auth_token": settings.pocketbase_auth_token,
        "admin_email": os.environ.get("POCKETBASE_ADMIN_EMAIL"),
        "admin_password": os.environ.get("POCKETBASE_ADMIN_PASSWORD"),
        "task_number": settings.task_number or "03",
        "expected_records": expected,
        "meta_pb": expected,
        "meta_mongo": expected,
        "incremental_mode": os.environ.get("GA03_INCREMENTAL_MODE", "false").lower() in {"1", "true", "yes"},
    }
