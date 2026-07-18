from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.etl.ga03_airflow._common import AtomicJsonState, elapsed_ms, _json_default
from src.etl.ga03_airflow.config import PIPELINE_PROGRESS_STEPS, PIPELINE_STARTED_MONO, paths


def _elapsed() -> int:
    return elapsed_ms(PIPELINE_STARTED_MONO)


def write_pipeline_progress(
    *,
    status: str,
    section: str,
    percent: float,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    progress_path = paths()["pipeline_progress"]
    payload = {
        "task_number": "03",
        "status": status,
        "section": section,
        "percent": round(percent, 2),
        "elapsed_ms": _elapsed(),
        "message": message,
        "detail": detail or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {
            "extract": {"label": "Extract", "complete": percent >= PIPELINE_PROGRESS_STEPS["extract"]},
            "parquet": {"label": "Parquet", "complete": percent >= PIPELINE_PROGRESS_STEPS["parquet"]},
            "transform": {"label": "Transform", "complete": percent >= PIPELINE_PROGRESS_STEPS["transform"]},
            "load_mongodb": {"label": "Carga MongoDB", "complete": percent >= PIPELINE_PROGRESS_STEPS["load_mongodb"]},
            "reports": {"label": "Reportes", "complete": percent >= PIPELINE_PROGRESS_STEPS["reports"]},
        },
    }
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = progress_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    tmp.replace(progress_path)


def write_state(update: dict[str, Any]) -> dict[str, Any]:
    return AtomicJsonState(paths()["state"]).write(update)


def read_state() -> dict[str, Any]:
    return AtomicJsonState(paths()["state"]).read()
