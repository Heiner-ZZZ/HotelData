from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.database.connection import get_database
from src.etl.ga03_audit import (
    build_execution_report,
    build_quality_report,
    insert_ga03_reports,
    utc_now_iso,
    write_json_report,
)
from src.etl.ga03_airflow.config import PIPELINE_PROGRESS_STEPS, paths
from src.etl.ga03_airflow.progress import write_pipeline_progress, read_state, write_state
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS
from src.etl.ta02_load_mongodb import collection_counts


def run_quality_checks_03() -> dict[str, Any]:
    all_paths = paths()
    state = read_state()
    schema = state.get("schema_report", {})
    fact_counts = state.get("fact_transform_counts", {})
    dimension_counts = state.get("dimension_counts", {})
    report = build_quality_report(
        execution_id=state["execution_id"],
        source_path=str(all_paths["parquet"]),
        source_rows=int(schema.get("records", 0) or 0),
        valid_fact_records=int(fact_counts.get("fact_hotel_reservations", 0) or 0),
        rejected_records=int(fact_counts.get("rejected_records", 0) or 0),
        dimensions=dimension_counts,
        schema=schema,
        extract=state.get("extract_report", {}),
        parquet=state.get("parquet_report", {}),
    )
    write_json_report(all_paths["quality_report"], report)
    write_pipeline_progress(
        status="running",
        section="reports",
        percent=96,
        message="Reporte de calidad generado.",
        detail={"valid_fact_records": report.get("valid_fact_records"), "rejected_records": report.get("rejected_records")},
    )
    write_state({"quality_report": report})
    return report


def save_execution_report_03() -> dict[str, Any]:
    all_paths = paths()
    state = read_state()
    db = get_database()
    completed_at = utc_now_iso()
    started = datetime.fromisoformat(state["started_at"])
    completed = datetime.fromisoformat(completed_at)
    collections = [*DIMENSION_KEY_FIELDS.keys(), "fact_hotel_reservations", "rejected_records", "etl_executions", "data_quality_reports"]
    final_counts = collection_counts(db, collections)
    execution_report = build_execution_report(
        execution_id=state["execution_id"],
        started_at=state["started_at"],
        completed_at=completed_at,
        duration_seconds=(completed - started).total_seconds(),
        database=state["database"],
        source_path=str(all_paths["parquet"]),
        loaded_collections={**state.get("dimension_load_counts", {}), **state.get("fact_load_counts", {})},
        final_counts=final_counts,
    )
    quality_report = state.get("quality_report")
    if quality_report is None:
        raise RuntimeError("No existe reporte de calidad GA03 en estado")
    insert_ga03_reports(db, quality_report, execution_report)
    write_json_report(all_paths["execution_report"], execution_report)
    write_pipeline_progress(
        status="completed",
        section="reports",
        percent=PIPELINE_PROGRESS_STEPS["reports"],
        message="Pipeline GA03 completado.",
        detail={"execution_id": state["execution_id"], "duration_seconds": execution_report.get("duration_seconds")},
    )
    write_state({"execution_report": execution_report})
    return {"status": "success", "execution_id": state["execution_id"], "report_saved": True}
