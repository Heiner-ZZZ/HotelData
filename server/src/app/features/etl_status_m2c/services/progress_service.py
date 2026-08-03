"""Progreso de la corrida mongo_to_clickhouse en curso.

Mismo contrato visual que GA03 pero con paths propios (config.paths()['progress']).
"""

from __future__ import annotations

import json
import os

from config.settings import get_settings
from src.app.features.etl_status_m2c.services._common import is_stale_timestamp
from src.etl.mongo_to_clickhouse.config import (
    PIPELINE_PROGRESS_LABELS,
    PIPELINE_PROGRESS_ORDER,
    paths,
)

_STALE_MINUTES = int(os.getenv("M2C_PROGRESS_STALE_MINUTES", "15"))

_DEFAULT_SECTIONS = {
    key: {"label": PIPELINE_PROGRESS_LABELS[key], "complete": False}
    for key in PIPELINE_PROGRESS_ORDER
}


def m2c_progress() -> dict:
    settings = get_settings()
    progress_path = paths()["progress"]
    default_progress = {
        "exists": False,
        "path": str(progress_path),
        "status": "pending",
        "section": "pending",
        "percent": 0,
        "elapsed_ms": 0,
        "message": "Pipeline mongo→clickhouse pendiente.",
        "detail": {},
        "updated_at": "",
        "sections": _DEFAULT_SECTIONS,
        "is_running": False,
        "clickhouse_database": settings.clickhouse_database,
        "tables": [],
    }
    if not progress_path.exists():
        return default_progress
    try:
        payload = json.loads(progress_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            **default_progress,
            "exists": True,
            "status": "failed",
            "message": "El archivo de progreso no es JSON válido.",
        }
    status = payload.get("status", "pending")
    stored_sections = payload.get("sections", {})
    sections = {
        key: {
            "label": PIPELINE_PROGRESS_LABELS[key],
            "complete": bool(stored_sections.get(key, {}).get("complete", False)),
        }
        for key in PIPELINE_PROGRESS_ORDER
    }
    if status == "running" and is_stale_timestamp(payload.get("updated_at"), minutes=_STALE_MINUTES):
        payload = {
            **payload,
            "status": "stopped",
            "message": "Ejecución anterior detenida o sin actualización reciente.",
            "stale": True,
            "stale_after_minutes": _STALE_MINUTES,
        }
        try:
            tmp = progress_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.rename(progress_path)
        except OSError:
            pass
        status = "stopped"
    result = {
        **default_progress,
        **payload,
        "exists": True,
        "path": str(progress_path),
        "sections": sections,
        "is_running": status == "running",
    }
    if not result.get("tables"):
        result["tables"] = []
    return result
