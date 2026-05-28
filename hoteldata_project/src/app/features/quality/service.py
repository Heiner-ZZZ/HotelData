from __future__ import annotations

from typing import Any

from src.database.connection import get_database


def quality_summary() -> dict:
    db = get_database()
    latest_report = db.data_quality_reports.find_one({}, {"_id": 0}, sort=[("generated_at", -1)]) or {}
    execution = db.etl_executions.find_one({}, {"_id": 0}, sort=[("executed_at", -1)]) or {}

    issue_breakdown: list[dict[str, Any]] = list(
        db.rejected_records.aggregate(
            [
                {"$group": {"_id": "$reason", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
        )
    )
    issues = {item["_id"] or "unknown": item["count"] for item in issue_breakdown}

    valid_records = int(latest_report.get("valid_fact_records", 0) or 0)
    rejected_records = int(latest_report.get("rejected_records", 0) or 0)
    source_rows = int(latest_report.get("source_rows", 0) or 0)
    transform_rejected = int(latest_report.get("transform_rejected_records", 0) or 0)
    key_rejected = int(latest_report.get("master_key_rejected_records", 0) or 0)
    completion_rate = round(float(latest_report.get("completeness_score", 0) or 0) * 100, 2)

    levels = {
        "valid": valid_records,
        "rejected": rejected_records,
        "source_rows": source_rows,
    }

    return {
        "levels": levels,
        "issues": issues,
        "nulls_by_column": latest_report.get("nulls_by_column", {}),
        "completeness_score": latest_report.get("completeness_score", 0),
        "completion_rate": completion_rate,
        "source_rows": source_rows,
        "valid_records": valid_records,
        "rejected_records": rejected_records,
        "transform_rejected_records": transform_rejected,
        "master_key_rejected_records": key_rejected,
        "latest_execution": execution,
        "latest_report": latest_report,
    }
