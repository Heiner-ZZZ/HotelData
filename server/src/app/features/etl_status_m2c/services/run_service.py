"""Disparo y detención del pipeline mongo_to_clickhouse.

El pipeline se ejecuta en un SUBPROCESO separado (``python -m
src.etl.mongo_to_clickhouse.runner``) con ``start_new_session=True``: así un
reinicio del ``--reload`` de uvicorn (p.ej. al editar cualquier archivo) NO
mata la corrida en curso — el subproceso sobrevive, sigue escribiendo el
progreso JSON y reporta al finalizar. El subproceso es dueño del lock
``pipeline_m2c.lock`` y lo limpia en su ``finally``. El stop flag sigue
funcionando: el pipeline lo revisa entre etapas.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone

from config.settings import get_settings
from src.app.features.etl_status_m2c.services._common import is_stale_timestamp
from src.app.features.etl_status_m2c.services.progress_service import m2c_progress
from src.etl.mongo_to_clickhouse.config import (
    PIPELINE_PROGRESS_LABELS,
    PIPELINE_PROGRESS_ORDER,
    paths,
)


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
    # Subproceso aislado: sobrevive al --reload de uvicorn y es dueño del lock
    # (lo limpia en su finally). stderr se anexa a un log para diagnóstico.
    log_path = settings.reports_dir / "pipeline_m2c_subprocess.log"
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.etl.mongo_to_clickhouse.runner"],
            stdout=open(log_path, "ab"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=settings.project_root,
        )
    except OSError as exc:
        try:
            lock_path.unlink()
        except OSError:
            pass
        return {
            "ok": False,
            "pid": None,
            "display_message": "No se pudo lanzar el subproceso del pipeline mongo→clickhouse.",
            "summary_output": str(exc),
        }
    return {
        "ok": True,
        "pid": proc.pid,
        "display_message": "Pipeline mongo→clickhouse iniciado en segundo plano (subproceso).",
        "summary_output": f"Progreso: /etl-status/m2c/progress · Log: {log_path}",
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
