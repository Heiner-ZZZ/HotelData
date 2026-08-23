from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from config.settings import get_settings
from src.app.features.etl_status.services._common import is_stale_timestamp


def _write_progress_seed(message: str, target_records: int = 0) -> None:
    settings = get_settings()
    progress_path = settings.reports_dir / "progreso_preparacion_reservas_03.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    target = target_records if target_records > 0 else settings.target_records
    payload = {
        "task_number": "03",
        "collection": settings.pocketbase_collection_03,
        "status": "running",
        "loaded_records": 0,
        "target_records": target,
        "remaining_records": target,
        "percent": 0,
        "last_batch_number": 0,
        "last_batch_records": 0,
        "csv_path": "",
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_pipeline_progress(message: str, target_records: int = 0) -> None:
    settings = get_settings()
    progress_path = settings.reports_dir / "progreso_pipeline_reservas_03.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    target = target_records if target_records > 0 else settings.target_records
    payload = {
        "task_number": "03",
        "status": "running",
        "percent": 0,
        "elapsed_ms": 0,
        "message": message,
        "sections": {
            "extract": {"label": "Extract", "complete": False},
            "parquet": {"label": "Parquet", "complete": False},
            "transform": {"label": "Transform", "complete": False},
            "load_mongodb": {"label": "Carga MongoDB", "complete": False},
            "reports": {"label": "Reportes", "complete": False},
        },
        "target_records": target,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def preparation_progress() -> dict:
    settings = get_settings()
    progress_path = settings.reports_dir / "progreso_preparacion_reservas_03.json"
    default_progress = {
        "exists": False,
        "path": str(progress_path),
        "status": "pending",
        "loaded_records": 0,
        "target_records": settings.target_records,
        "remaining_records": settings.target_records,
        "percent": 0,
        "last_batch_number": 0,
        "last_batch_records": 0,
        "message": "Preparación pendiente.",
        "updated_at": "",
        "csv_path": "",
        "is_running": False,
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
    result = {
        **default_progress,
        **payload,
        "exists": True,
        "path": str(progress_path),
        "is_running": status == "running",
    }
    if not result.get("target_records"):
        result["target_records"] = result.get("loaded_records", 0) or 0
        result["remaining_records"] = max(result["target_records"] - result.get("loaded_records", 0), 0)
    return result


def _normalize_sections(raw_sections: object, default_sections: dict) -> dict:
    """Normalize ``sections`` to the canonical ``{key: {label, complete}}`` shape.

    The canonical writer (``ga03_airflow.progress``) emits a dict. The legacy
    ``_write_pipeline_progress`` emitted a list of ``{key, label, complete}``
    and used ``mongodb`` instead of ``load_mongodb``; both are tolerated here.
    """
    if isinstance(raw_sections, dict):
        return {**default_sections, **raw_sections}
    if isinstance(raw_sections, list):
        normalized = dict(default_sections)
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            if key == "mongodb":
                key = "load_mongodb"
            if key in normalized:
                normalized[key] = {
                    "label": item.get("label") or normalized[key]["label"],
                    "complete": bool(item.get("complete", False)),
                }
        return normalized
    return dict(default_sections)


def pipeline_progress() -> dict:
    settings = get_settings()
    progress_path = settings.reports_dir / "progreso_pipeline_reservas_03.json"
    lock_path = settings.reports_dir / "pipeline_reservas_03.lock"
    stale_minutes = int(os.getenv("GA03_PROGRESS_STALE_MINUTES", "15"))
    default_sections = {
        "extract": {"label": "Extract", "complete": False},
        "parquet": {"label": "Parquet", "complete": False},
        "transform": {"label": "Transform", "complete": False},
        "load_mongodb": {"label": "Carga MongoDB", "complete": False},
        "reports": {"label": "Reportes", "complete": False},
    }
    default_progress = {
        "exists": False,
        "path": str(progress_path),
        "status": "pending",
        "section": "pending",
        "percent": 0,
        "elapsed_ms": 0,
        "message": "Pipeline pendiente.",
        "detail": {},
        "updated_at": "",
        "sections": default_sections,
        "is_running": False,
        "target_records": settings.target_records,
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
            "message": "El archivo de progreso del pipeline no es JSON válido.",
        }
    status = payload.get("status", "pending")
    sections = _normalize_sections(payload.get("sections"), default_sections)
    if status == "running" and is_stale_timestamp(payload.get("updated_at"), minutes=stale_minutes):
        stale_message = (
            "Ejecución anterior detenida o sin actualización reciente. "
            "Use Actualizar para limpiar el estado visual o ejecute el pipeline nuevamente."
        )
        payload = {
            **payload,
            "status": "stopped",
            "message": stale_message,
            "stale": True,
            "stale_after_minutes": stale_minutes,
        }
        try:
            tmp = progress_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.rename(progress_path)
        except OSError:
            pass
        if lock_path.exists():
            try:
                lock_path.unlink()
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
    if not result.get("target_records"):
        result["target_records"] = result.get("finally_count") or 0
    return result
