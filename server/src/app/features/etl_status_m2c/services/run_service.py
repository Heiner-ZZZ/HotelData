"""Disparo y detención del pipeline mongo_to_clickhouse.

El pipeline se ejecuta en un thread daemon (en proceso, no subprocess) porque el
paquete ``src.etl.mongo_to_clickhouse`` vive en el mismo contenedor. Lock de
archivo + stop flag para control desde la UI.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from config.settings import get_settings
from src.app.features.etl_status_m2c.services._common import is_stale_timestamp
from src.app.features.etl_status_m2c.services.progress_service import m2c_progress
from src.etl.mongo_to_clickhouse.config import (
    PIPELINE_PROGRESS_LABELS,
    PIPELINE_PROGRESS_ORDER,
    paths,
)

_lock = threading.Lock()
_worker: threading.Thread | None = None


def _write_progress_started() -> None:
    from src.etl.mongo_to_clickhouse._common import write_json_file

    write_json_file(
        paths()["progress"],
        {
            "status": "running",
            "percent": 0,
            "section": "validate_config",
            "elapsed_ms": 0,
            "message": "Pipeline mongo→clickhouse solicitado desde /etl-status/m2c.",
            "sections": {
                key: {"label": PIPELINE_PROGRESS_LABELS[key], "complete": False}
                for key in PIPELINE_PROGRESS_ORDER
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def start_pipeline() -> dict:
    settings = get_settings()
    lock_path = settings.reports_dir / "pipeline_m2c.lock"
    progress = m2c_progress()
    if progress.get("is_running") or lock_path.exists():
        if lock_path.exists() and is_stale_timestamp(
            progress.get("updated_at"), minutes=15
        ):
            try:
                lock_path.unlink()
            except OSError:
                pass
        else:
            return {
                "ok": False,
                "pid": None,
                "display_message": "Pipeline mongo→clickhouse ya está en ejecución.",
                "summary_output": str(lock_path),
            }
    _write_progress_started()
    lock_path.touch()
    global _worker

    def _run() -> None:
        from src.etl.mongo_to_clickhouse._common import write_json_file

        try:
            from src.etl.mongo_to_clickhouse import run_pipeline

            result = run_pipeline()
            if not result.get("ok"):
                # El pipeline ya escribió progress con status=failed en estos casos.
                pass
        except Exception as exc:  # pragma: no cover - estado de error
            write_json_file(
                paths()["progress"],
                {
                    "status": "failed",
                    "message": f"Pipeline fallido: {exc}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        finally:
            try:
                lock_path.unlink()
            except OSError:
                pass

    with _lock:
        _worker = threading.Thread(target=_run, name="m2c-pipeline", daemon=True)
        _worker.start()
    return {
        "ok": True,
        "pid": _worker.native_id,
        "display_message": "Pipeline mongo→clickhouse iniciado en segundo plano.",
        "summary_output": "Progreso disponible en /etl-status/m2c/progress.",
    }


def stop_pipeline() -> dict:
    settings = get_settings()
    flag_path = settings.reports_dir / "m2c_stop.flag"
    try:
        flag_path.write_text("stop")
        return {
            "ok": True,
            "display_message": "Detención solicitada. El pipeline revisa el flag entre etapas.",
            "summary_output": str(flag_path),
        }
    except OSError as exc:
        return {
            "ok": False,
            "display_message": "No se pudo crear el flag de detención.",
            "summary_output": str(exc),
        }
