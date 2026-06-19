from __future__ import annotations

import json
from typing import Any

from src.database.connection import get_database
from src.etl.ta02_airflow_tasks._state import _count_jsonl, _paths, _read_state, _write_state
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS
from src.etl.ta02_load_mongodb import collection_counts, insert_execution_report, insert_quality_report
from src.etl.ta02_fact import utc_now_iso


def run_quality_checks() -> dict[str, Any]:
    paths = _paths()
    state = _read_state()
    schema = state.get("schema_report", {})
    fact_counts = state.get("fact_transform_counts", {})
    dimension_counts = state.get("dimension_counts", {})
    source_rows = int(schema.get("records", 0) or 0)
    valid_records = int(fact_counts.get("fact_hotel_reservations", 0) or 0)
    rejected_records = int(fact_counts.get("rejected_records", 0) or 0)
    report = {
        "execution_id": state["execution_id"],
        "generated_at": utc_now_iso(),
        "source": str(paths["parquet"]),
        "source_rows": source_rows,
        "valid_fact_records": valid_records,
        "rejected_records": rejected_records,
        "completeness_score": round(valid_records / source_rows, 4) if source_rows else 0,
        "dimensions": dimension_counts,
        "schema": schema,
        "extract": state.get("extract_report", {}),
        "parquet": state.get("parquet_report", {}),
    }
    paths["quality_report"].write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _write_state({"quality_report": report})
    return report


def save_execution_report() -> dict[str, Any]:
    paths = _paths()
    state = _read_state()
    db = get_database()
    collections = [
        *DIMENSION_KEY_FIELDS.keys(),
        "fact_hotel_reservations",
        "rejected_records",
        "etl_executions",
        "data_quality_reports",
    ]
    final_counts = collection_counts(db, collections)
    execution_report = {
        "execution_id": state["execution_id"],
        "executed_at": state["loaded_at"],
        "status": "success",
        "database": state["database"],
        "source": str(paths["parquet"]),
        "loaded_collections": {
            **state.get("dimension_load_counts", {}),
            **state.get("fact_load_counts", {}),
        },
        "final_counts": final_counts,
    }
    quality_report = state.get("quality_report")
    if quality_report is None:
        raise RuntimeError("No existe quality_report en estado. Ejecute run_quality_checks antes.")
    insert_quality_report(db, quality_report)
    insert_execution_report(db, execution_report)
    paths["execution_report"].write_text(
        json.dumps(execution_report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    _write_state({"execution_report": execution_report})
    return {
        "status": "success",
        "execution_id": state["execution_id"],
        "report_saved": True,
    }
