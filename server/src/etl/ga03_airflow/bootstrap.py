from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.etl.ga03_audit import utc_now_iso
from src.etl.ga03_airflow.config import PHASE, PIPELINE_PROGRESS_STEPS, paths, pocketbase_config
from src.etl.ga03_airflow.progress import write_pipeline_progress, write_state


def validate_environment_03() -> dict[str, Any]:
    settings = get_settings()
    config = pocketbase_config()
    all_paths = paths()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    all_paths["dimension_dir"].mkdir(parents=True, exist_ok=True)
    for key in ["quality_report", "execution_report"]:
        if all_paths[key].exists():
            all_paths[key].unlink()
    if all_paths["pipeline_progress"].exists():
        all_paths["pipeline_progress"].unlink()
    for dimension_file in all_paths["dimension_dir"].glob("*.jsonl"):
        dimension_file.unlink()
    started_at = utc_now_iso()
    expected = int(config.get("expected_records", 0) or 0)
    state = {
        "execution_id": f"ga03_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "phase": PHASE,
        "task_number": config["task_number"],
        "started_at": started_at,
        "loaded_at": started_at,
        "database": settings.mongo_database,
        "expected_records": expected,
        "paths": {name: str(path) for name, path in all_paths.items()},
    }
    write_pipeline_progress(
        status="running",
        section="environment",
        percent=PIPELINE_PROGRESS_STEPS["environment"],
        message="Entorno GA03 validado.",
        detail={"database": settings.mongo_database, "expected_records": expected},
    )
    return write_state(state)
