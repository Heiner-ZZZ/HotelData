from __future__ import annotations

import json

from config.settings import get_settings
from src.database.connection import get_database


def execution_status() -> dict:
    settings = get_settings()
    mongo_error = ""
    try:
        db = get_database()
        latest_execution = db.etl_executions.find_one({}, {"_id": 0}, sort=[("executed_at", -1)])
    except Exception as exc:
        latest_execution = None
        mongo_error = str(exc)
    if latest_execution:
        quality_report = latest_execution.get("reports", {}).get("quality_report.json", {})
        return {
            "available": True,
            "source": "mongodb",
            "legacy": False,
            "report": latest_execution,
            "summary": {
                "execution_id": latest_execution.get("execution_id"),
                "executed_at": latest_execution.get("executed_at"),
                "status": latest_execution.get("status", "unknown"),
                "valid_fact_records": quality_report.get("valid_fact_records", 0),
                "rejected_records": quality_report.get("rejected_records", 0),
                "source_rows": quality_report.get("source_rows", 0),
            },
        }

    report_path = settings.reports_dir / "execution_report.json"
    if not report_path.exists():
        message = (
            "No hay ejecuciones ETL registradas todavia. Ejecuta seed_master_collections.py "
            "y luego run_etl_local.py con el CSV transaccional."
        )
        if mongo_error:
            message = f"MongoDB no disponible para estado ETL general: {mongo_error}"
        return {
            "available": False,
            "message": message,
        }
    report = json.loads(report_path.read_text(encoding="utf-8"))
    is_legacy = "execution_id" not in report or "cleaning_report.json" in report.get("reports", {})
    return {
        "available": True,
        "source": "local_file",
        "legacy": is_legacy,
        "report": report,
        "summary": {
            "executed_at": report.get("executed_at"),
            "status": "legacy_report",
        },
    }
