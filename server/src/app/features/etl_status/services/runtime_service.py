from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from config.settings import get_settings
from src.app.features.etl_status.services._common import is_stale_timestamp
from src.app.features.etl_status.services.progress_service import (
    _write_pipeline_progress,
    _write_progress_seed,
    pipeline_progress,
    preparation_progress,
)


def _run_script(script_name: str, env: dict[str, str] | None = None) -> dict:
    settings = get_settings()
    script_path = settings.project_root / "scripts" / script_name
    command = [sys.executable, str(script_path)]
    proc_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        command,
        cwd=settings.project_root,
        capture_output=True,
        text=True,
        timeout=3600,
        env=proc_env,
    )
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
    }


def _start_script(
    script_name: str,
    args: list[str] | None = None,
    log_name: str = "preparacion_reservas_03.log",
    env: dict[str, str] | None = None,
) -> dict:
    settings = get_settings()
    script_path = settings.project_root / "scripts" / script_name
    logs_dir = settings.reports_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_name
    command = [sys.executable, str(script_path), *(args or [])]
    proc_env = {**os.environ, **(env or {})}
    log_handle = log_path.open("ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=settings.project_root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=proc_env,
        )
    finally:
        log_handle.close()
    return {
        "command": " ".join(command),
        "returncode": 0,
        "stdout": f"Proceso iniciado en segundo plano. Log: {log_path}",
        "stderr": "",
        "ok": True,
        "pid": process.pid,
    }


def run_seed_master_collections() -> dict:
    return _run_script("seed_master_collections.py")


def run_local_etl() -> dict:
    return _run_script("run_etl_local.py")


def _ga03_collection_name() -> str:
    """Nombre de la colección destino GA03.

    KEEP IN SYNC con ``server/scripts/cargar_reservas_hoteleras_03.py``
    (misma precedencia de env para ``COLLECTION_NAME``). Se usa para pasar el
    ``--confirm-reload`` exacto cuando el seed corre en modo full.
    """
    ta02 = "hotel_reservation_events__2"
    generic = os.getenv("POCKETBASE_COLLECTION")
    return os.getenv("POCKETBASE_COLLECTION_03") or (
        generic
        if os.getenv("TASK_NUMBER", "03") == "03" and generic and generic != ta02
        else "hotel_reservation_events_03"
    )


def run_dataset_validation(target_records: int = 0) -> dict:
    extra_env = {"META_PB": str(target_records)} if target_records > 0 else None
    return _run_script("validar_dataset_reservas_03.py", env=extra_env)


def run_pipeline(target_records: int = 0) -> dict:
    extra_env = {"TARGET_RECORDS": str(target_records)} if target_records > 0 else None
    return _run_script("run_reservas_03_pipeline.py", env=extra_env)


def prepare_seed_source() -> dict:
    return _run_script("cargar_reservas_hoteleras_03.py")


def start_seed_source(target_records: int = 0, incremental: bool = False) -> dict:
    settings = get_settings()
    progress = preparation_progress()
    if progress.get("is_running"):
        return {
            "command": "scripts/cargar_reservas_hoteleras_03.py",
            "returncode": 1,
            "stdout": "",
            "stderr": "Ya existe una preparación GA03 en ejecución.",
            "ok": False,
        }
    _write_progress_seed("Preparación GA03 solicitada desde /etl-status.", target_records=target_records)
    uploaded_csv = settings.project_root / "data" / "uploads" / "ga03_source.csv"
    args = ["--csv", str(uploaded_csv)] if uploaded_csv.exists() else []
    extra_env = {"META_PB": str(target_records)} if target_records > 0 else {}
    extra_env["GA03_INCREMENTAL_MODE"] = "true" if incremental else "false"
    if not incremental:
        # Modo full: recarga desde cero. El confirm del dialog de la UI es la
        # confirmación; el script exige el nombre exacto de la colección.
        args.extend(["--reload", "--confirm-reload", _ga03_collection_name()])
    return _start_script("cargar_reservas_hoteleras_03.py", args=args, env=extra_env)


def start_pipeline(target_records: int = 0, incremental: bool = False) -> dict:
    settings = get_settings()
    lock_path = settings.reports_dir / "pipeline_reservas_03.lock"
    if lock_path.exists():
        progress = pipeline_progress()
        if progress.get("stale"):
            try:
                lock_path.unlink()
            except OSError:
                pass
        elif is_stale_timestamp(
            datetime.fromtimestamp(lock_path.stat().st_mtime, tz=timezone.utc).isoformat(),
            minutes=15,
        ):
            try:
                lock_path.unlink()
            except OSError:
                pass
        else:
            return {
                "command": "scripts/run_reservas_03_pipeline.py",
                "returncode": 1,
                "stdout": "",
                "stderr": f"Pipeline GA03 ya parece estar en ejecución. Lock: {lock_path}",
                "ok": False,
            }
    if lock_path.exists():
        return {
            "command": "scripts/run_reservas_03_pipeline.py",
            "returncode": 1,
            "stdout": "",
            "stderr": f"Pipeline GA03 ya parece estar en ejecución. Lock: {lock_path}",
            "ok": False,
        }
    _write_pipeline_progress("Pipeline GA03 solicitado desde /etl-status.", target_records=target_records)
    extra_env = {"META_MONGO": str(target_records)} if target_records > 0 else {}
    extra_env["GA03_INCREMENTAL_MODE"] = "true" if incremental else "false"
    return _start_script("run_reservas_03_pipeline.py", log_name="pipeline_reservas_03.log", env=extra_env)


def stop_etl(process: str) -> dict:
    settings = get_settings()
    flag_name = "seed" if process == "seed" else "pipeline"
    flag_path = settings.reports_dir / f"ga03_{flag_name}_stop.flag"
    try:
        flag_path.write_text("stop")
        return {
            "command": f"stop_etl({process})",
            "returncode": 0,
            "stdout": f"Flag de detención creado: {flag_path}",
            "stderr": "",
            "ok": True,
        }
    except OSError as exc:
        return {
            "command": f"stop_etl({process})",
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "ok": False,
        }


def clear_local_evidence() -> dict:
    import subprocess
    from pathlib import Path
    settings = get_settings()
    try:
        result = subprocess.run(
            ["curl", "-s", "--unix-socket", "/var/run/docker.sock",
             "-X", "POST", "http://localhost/v1.41/build/prune",
             "-H", "Content-Type: application/json",
             "-d", '{"all":true,"filters":{},"keep-storage":0}'],
            capture_output=True, text=True, timeout=60
        )
        docker_prune_out = (result.stdout or result.stderr or "").strip()
    except Exception as exc:
        docker_prune_out = f"Docker prune no disponible: {exc}"
    json_paths = [
        settings.reports_dir / "progreso_preparacion_reservas_03.json",
        settings.reports_dir / "validacion_dataset_reservas_03.json",
        settings.reports_dir / "reporte_calidad_reservas_03.json",
        settings.reports_dir / "reporte_ejecucion_reservas_03.json",
        settings.reports_dir / "progreso_pipeline_reservas_03.json",
    ]
    other_paths = [
        settings.reports_dir / "preparacion_reservas_03.log",
        settings.reports_dir / "pipeline_reservas_03.log",
        settings.reports_dir / "pipeline_reservas_03.lock",
    ]
    etl_paths = [
        settings.staging_dir / "reservas_hoteleras_03_extract.jsonl",
        settings.staging_dir / "ga03_execution_state.json",
        settings.processed_dir / "reservas_hoteleras_03.parquet",
        settings.processed_dir / "reservas_hoteleras_03.parquet.meta.json",
        settings.processed_dir / "fact_hotel_reservations_ga03.jsonl",
        settings.processed_dir / "fact_hotel_reservations_ga03.meta.json",
        settings.processed_dir / "rejected_records_ga03.jsonl",
    ]
    paths: list[Path] = json_paths + other_paths + [p.with_suffix(".json.tmp") for p in json_paths] + etl_paths
    dimension_dir = settings.processed_dir / "ga03_dimensions"
    if dimension_dir.exists():
        for f in dimension_dir.iterdir():
            paths.append(f)
    deleted: list[str] = []
    missing: list[str] = []
    for path in paths:
        if path.exists() and path.is_file():
            path.unlink()
            deleted.append(str(path))
        else:
            missing.append(str(path))
    if dimension_dir.exists() and not any(dimension_dir.iterdir()):
        try:
            dimension_dir.rmdir()
            deleted.append(str(dimension_dir) + "/")
        except OSError:
            pass
    return {
        "command": "clear_ga03_local_evidence",
        "returncode": 0,
        "stdout": json.dumps({"deleted": deleted, "missing": missing, "docker_prune": docker_prune_out}, indent=2, ensure_ascii=False),
        "stderr": "",
        "ok": True,
        "deleted": deleted,
        "missing": missing,
        "docker_prune": docker_prune_out,
    }
