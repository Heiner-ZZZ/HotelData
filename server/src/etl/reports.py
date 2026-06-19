from __future__ import annotations

import json
from datetime import datetime, timezone

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.quality import generate_quality_report


def save_execution_report() -> dict:
    settings = get_settings()
    quality_report = generate_quality_report()
    report_files = ["quality_report.json", "extract_metadata.json"]
    reports = {}
    for filename in report_files:
        path = settings.reports_dir / filename
        if not path.exists() and filename == "extract_metadata.json":
            path = settings.staging_dir / filename
        if path.exists():
            reports[filename] = json.loads(path.read_text(encoding="utf-8"))

    execution_report = {
        "execution_id": quality_report.get("execution_id", f"etl_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "database": settings.mongo_database,
        "reports": reports,
    }
    target = settings.reports_dir / "execution_report.json"
    target.write_text(json.dumps(execution_report, indent=2, ensure_ascii=False), encoding="utf-8")

    db = get_database()
    db.data_quality_reports.insert_one(quality_report)
    db.etl_executions.insert_one(execution_report)
    quality_report.pop("_id", None)
    execution_report.pop("_id", None)
    return execution_report
