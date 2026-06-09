from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo.database import Database


PHASE = "GA03"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def write_json_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")


def build_quality_report(
    *,
    execution_id: str,
    source_path: str,
    source_rows: int,
    valid_fact_records: int,
    rejected_records: int,
    dimensions: dict[str, int],
    schema: dict[str, Any],
    extract: dict[str, Any],
    parquet: dict[str, Any],
) -> dict[str, Any]:
    valid_dimension_records = sum(int(value or 0) for value in dimensions.values())
    return {
        "execution_id": execution_id,
        "phase": PHASE,
        "generated_at": utc_now_iso(),
        "source": source_path,
        "source_rows": source_rows,
        "valid_fact_records": valid_fact_records,
        "invalid_fact_records": rejected_records,
        "rejected_records": rejected_records,
        "valid_dimension_records": valid_dimension_records,
        "invalid_dimension_records": 0,
        "completeness_score": round(valid_fact_records / source_rows, 4) if source_rows else 0,
        "dimensions": dimensions,
        "schema": schema,
        "extract": extract,
        "parquet": parquet,
    }


def build_execution_report(
    *,
    execution_id: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    database: str,
    source_path: str,
    loaded_collections: dict[str, int],
    final_counts: dict[str, int],
    status: str = "success",
    error_message: str | None = None,
) -> dict[str, Any]:
    records_processed = int(loaded_collections.get("final_fact_hotel_reservations") or loaded_collections.get("fact_hotel_reservations") or 0)
    records_rejected = int(loaded_collections.get("rejected_records") or 0)
    report = {
        "execution_id": execution_id,
        "phase": PHASE,
        "executed_at": completed_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": round(duration_seconds, 3),
        "status": status,
        "database": database,
        "source": source_path,
        "records_processed": records_processed,
        "records_rejected": records_rejected,
        "loaded_collections": loaded_collections,
        "final_counts": final_counts,
    }
    if error_message:
        report["error_message"] = error_message
    return report


def insert_ga03_reports(db: Database, quality_report: dict[str, Any], execution_report: dict[str, Any]) -> dict[str, str]:
    quality_id = db.data_quality_reports.insert_one(quality_report).inserted_id
    execution_id = db.etl_executions.insert_one(execution_report).inserted_id
    return {"data_quality_reports": str(quality_id), "etl_executions": str(execution_id)}
