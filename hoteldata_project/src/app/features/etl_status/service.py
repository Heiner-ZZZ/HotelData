from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

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


def raw_file_status() -> dict:
    settings = get_settings()
    raw_path = settings.raw_csv_path
    if not raw_path.exists():
        return {
            "exists": False,
            "path": str(raw_path),
            "filename": raw_path.name,
            "rows": 0,
            "actual_rows": 0,
            "demo_row_limit": settings.demo_row_limit,
            "columns": [],
        }

    with raw_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        try:
            columns = next(reader)
        except StopIteration:
            columns = []
            row_count = 0
        else:
            row_count = 0
            for _ in reader:
                row_count += 1
                if row_count >= settings.demo_row_limit:
                    break

    demo_rows = min(row_count, settings.demo_row_limit)
    actual_rows = demo_rows if row_count < settings.demo_row_limit else f">= {settings.demo_row_limit}"

    return {
        "exists": True,
        "path": str(raw_path),
        "filename": raw_path.name,
        "rows": demo_rows,
        "actual_rows": actual_rows,
        "demo_row_limit": settings.demo_row_limit,
        "columns": columns,
    }


def save_uploaded_raw_csv(filename: str, content: bytes) -> dict:
    settings = get_settings()
    raw_path = settings.raw_csv_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)
    status = raw_file_status()
    status["uploaded_filename"] = Path(filename).name
    return status


def save_ga03_source_csv(filename: str, content: bytes) -> dict:
    settings = get_settings()
    upload_path = settings.project_root / "data" / "uploads" / "ga03_source.csv"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)
    return {
        "uploaded_filename": Path(filename).name,
        "path": str(upload_path),
        "exists": upload_path.exists(),
    }


def _run_script(script_name: str) -> dict:
    settings = get_settings()
    script_path = settings.project_root / "scripts" / script_name
    command = [sys.executable, str(script_path)]
    result = subprocess.run(
        command,
        cwd=settings.project_root,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
    }


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_stale_timestamp(value: str | None, *, minutes: int) -> bool:
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - parsed > timedelta(minutes=minutes)


def _write_ga03_progress_seed(message: str) -> None:
    settings = get_settings()
    progress_path = settings.reports_dir / "progreso_preparacion_reservas_03.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_number": "03",
        "collection": settings.pocketbase_collection_03,
        "status": "running",
        "loaded_records": 0,
        "target_records": settings.target_records,
        "remaining_records": settings.target_records,
        "percent": 0,
        "last_batch_number": 0,
        "last_batch_records": 0,
        "csv_path": "",
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _start_script(script_name: str, args: list[str] | None = None, log_name: str = "preparacion_reservas_03.log") -> dict:
    settings = get_settings()
    script_path = settings.project_root / "scripts" / script_name
    logs_dir = settings.reports_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_name
    command = [sys.executable, str(script_path), *(args or [])]
    log_handle = log_path.open("ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=settings.project_root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
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


def _csv_path_candidates(path_value: str) -> list[Path]:
    settings = get_settings()
    raw_candidates = [
        path_value,
        str(settings.project_root / "data" / "uploads" / "ga03_source.csv"),
        str(settings.project_root / "data" / "processed" / "expedia_reservations_clean.csv"),
        str(settings.project_root.parent / "data" / "processed" / "expedia_reservations_clean.csv"),
        "/HotelData/data/processed/expedia_reservations_clean.csv",
        "C:/HotelData/data/processed/expedia_reservations_clean.csv",
        "/mnt/c/HotelData/data/processed/expedia_reservations_clean.csv",
    ]
    extra_candidates = os.getenv("GA03_SOURCE_CSV_CANDIDATES", "")
    if extra_candidates:
        raw_candidates.extend(candidate.strip() for candidate in extra_candidates.split(";") if candidate.strip())

    candidates: list[Path] = []
    seen: set[str] = set()
    for raw_candidate in raw_candidates:
        if not raw_candidate:
            continue
        candidate = Path(raw_candidate)
        key = str(candidate)
        if key not in seen:
            candidates.append(candidate)
            seen.add(key)
        if len(raw_candidate) > 2 and raw_candidate[1:3] == ":/":
            drive = raw_candidate[0].lower()
            rest = raw_candidate[3:]
            wsl_candidate = Path(f"/mnt/{drive}") / rest
            key = str(wsl_candidate)
            if key not in seen:
                candidates.append(wsl_candidate)
                seen.add(key)
    return candidates


def _resolve_available_path(path_value: str) -> tuple[Path, list[Path]]:
    candidates = _csv_path_candidates(path_value)
    for candidate in candidates:
        if candidate.exists():
            return candidate, candidates
    return candidates[0], candidates


def ga03_config_status() -> dict:
    settings = get_settings()
    configured_source_csv = os.getenv("GA03_SOURCE_CSV", "C:/HotelData/data/processed/expedia_reservations_clean.csv")
    upload_path = settings.project_root / "data" / "uploads" / "ga03_source.csv"
    source_csv = str(upload_path) if upload_path.exists() else configured_source_csv
    resolved_source_csv, source_csv_candidates = _resolve_available_path(source_csv)
    return {
        "task_number": settings.task_number,
        "target_records": settings.target_records,
        "pocketbase_collection": settings.pocketbase_collection_03,
        "source_csv": source_csv,
        "source_csv_configured": configured_source_csv,
        "uploaded_source_csv": str(upload_path),
        "uploaded_source_csv_exists": upload_path.exists(),
        "source_csv_resolved": str(resolved_source_csv),
        "source_csv_candidates": [str(candidate) for candidate in source_csv_candidates],
        "source_csv_exists": resolved_source_csv.exists(),
        "full_reload_facts": os.getenv("GA03_FULL_RELOAD_FACTS", "true").lower() == "true",
    }


def ga03_preparation_progress() -> dict:
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
    return {
        **default_progress,
        **payload,
        "exists": True,
        "path": str(progress_path),
        "is_running": status == "running",
    }


def ga03_pipeline_progress() -> dict:
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
    sections = {**default_sections, **payload.get("sections", {})}
    if status == "running" and _is_stale_timestamp(payload.get("updated_at"), minutes=stale_minutes):
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
            progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        if lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass
        status = "stopped"
    return {
        **default_progress,
        **payload,
        "exists": True,
        "path": str(progress_path),
        "sections": sections,
        "is_running": status == "running",
    }


def ga03_artifact_status() -> dict:
    settings = get_settings()
    parquet_path = settings.project_root / "data" / "processed" / "reservas_hoteleras_03.parquet"
    jsonl_path = settings.project_root / "data" / "staging" / "reservas_hoteleras_03_extract.jsonl"
    return {
        "jsonl": {
            "exists": jsonl_path.exists(),
            "path": str(jsonl_path),
        },
        "parquet": {
            "exists": parquet_path.exists(),
            "path": str(parquet_path),
        },
    }


def _pocketbase_headers() -> dict[str, str]:
    token = os.getenv("POCKETBASE_AUTH_TOKEN")
    if token:
        return {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    settings = get_settings()
    email = os.getenv("POCKETBASE_ADMIN_EMAIL")
    password = os.getenv("POCKETBASE_ADMIN_PASSWORD")
    if not email or not password:
        return {"Accept": "application/json"}
    response = requests.post(
        f"{settings.pocketbase_url.rstrip('/')}/api/collections/_superusers/auth-with-password",
        json={"identity": email, "password": password},
        timeout=5,
    )
    response.raise_for_status()
    return {"Accept": "application/json", "Authorization": f"Bearer {response.json()['token']}"}


def ga03_pocketbase_status() -> dict:
    settings = get_settings()
    collection = settings.pocketbase_collection_03
    target = settings.target_records
    if collection == "hotel_reservation_events__2":
        return {
            "available": False,
            "collection": collection,
            "count": None,
            "state": "error",
            "message": "La colección GA03 no puede apuntar a hotel_reservation_events__2.",
        }
    try:
        headers = _pocketbase_headers()
        response = requests.get(
            f"{settings.pocketbase_url.rstrip('/')}/api/collections/{collection}/records",
            params={"page": 1, "perPage": 1},
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        count = int(response.json().get("totalItems", 0) or 0)
    except requests.HTTPError as exc:
        detail = str(exc)
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            message = "Colección GA03 no creada todavía. Prepare la fuente para crearla."
            state = "not_found"
        else:
            message = "No disponible."
            state = "unavailable"
        return {
            "available": False,
            "collection": collection,
            "count": None,
            "state": state,
            "message": message,
            "technical_detail": detail,
        }
    except Exception as exc:
        return {
            "available": False,
            "collection": collection,
            "count": None,
            "state": "unavailable",
            "message": "No disponible.",
            "technical_detail": str(exc),
        }

    if count == target:
        state = "ready"
        message = "Fuente lista."
    elif count < target:
        state = "incomplete"
        message = "Fuente incompleta."
    else:
        state = "error"
        message = "Error: excede objetivo."
    return {
        "available": True,
        "collection": collection,
        "count": count,
        "target_records": target,
        "state": state,
        "message": message,
    }


def ga03_mongodb_status() -> dict:
    settings = get_settings()
    try:
        db = get_database()
        db.command("ping")
        collections = db.list_collection_names()
        fact_exists = "fact_hotel_reservations" in collections
        fact_count = db.fact_hotel_reservations.count_documents({}) if fact_exists else 0
        ga03_count = db.fact_hotel_reservations.count_documents({"phase": "GA03"}) if fact_exists else 0
        return {
            "available": True,
            "database": settings.mongo_database,
            "fact_exists": fact_exists,
            "fact_count": fact_count,
            "ga03_fact_count": ga03_count,
            "message": "MongoDB disponible.",
        }
    except Exception as exc:
        return {
            "available": False,
            "database": settings.mongo_database,
            "fact_exists": False,
            "fact_count": None,
            "ga03_fact_count": None,
            "message": "No disponible.",
            "technical_detail": str(exc),
        }


def ga03_report_status() -> dict:
    settings = get_settings()
    report_files = {
        "progress": settings.reports_dir / "progreso_preparacion_reservas_03.json",
        "pipeline_progress": settings.reports_dir / "progreso_pipeline_reservas_03.json",
        "validation": settings.reports_dir / "validacion_dataset_reservas_03.json",
        "quality": settings.reports_dir / "reporte_calidad_reservas_03.json",
        "execution": settings.reports_dir / "reporte_ejecucion_reservas_03.json",
    }
    reports = {}
    for name, path in report_files.items():
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"error": "JSON inválido"}
            reports[name] = {
                "exists": True,
                "path": str(path),
                "payload": payload,
            }
        else:
            reports[name] = {
                "exists": False,
                "path": str(path),
                "payload": {},
            }
    return reports


def clear_ga03_local_evidence() -> dict:
    settings = get_settings()
    paths = [
        settings.reports_dir / "progreso_preparacion_reservas_03.json",
        settings.reports_dir / "validacion_dataset_reservas_03.json",
        settings.reports_dir / "reporte_calidad_reservas_03.json",
        settings.reports_dir / "reporte_ejecucion_reservas_03.json",
        settings.reports_dir / "preparacion_reservas_03.log",
        settings.reports_dir / "progreso_pipeline_reservas_03.json",
        settings.reports_dir / "pipeline_reservas_03.log",
        settings.reports_dir / "pipeline_reservas_03.lock",
    ]
    deleted: list[str] = []
    missing: list[str] = []
    for path in paths:
        if path.exists() and path.is_file():
            path.unlink()
            deleted.append(str(path))
        else:
            missing.append(str(path))
    return {
        "command": "clear_ga03_local_evidence",
        "returncode": 0,
        "stdout": json.dumps({"deleted": deleted, "missing": missing}, indent=2, ensure_ascii=False),
        "stderr": "",
        "ok": True,
        "deleted": deleted,
        "missing": missing,
    }


def run_ga03_dataset_validation() -> dict:
    return _run_script("validar_dataset_reservas_03.py")


def run_ga03_pipeline() -> dict:
    return _run_script("run_reservas_03_pipeline.py")


def prepare_ga03_seed_source() -> dict:
    return _run_script("cargar_reservas_hoteleras_03.py")


def start_ga03_seed_source() -> dict:
    settings = get_settings()
    progress = ga03_preparation_progress()
    if progress.get("is_running"):
        return {
            "command": "scripts/cargar_reservas_hoteleras_03.py",
            "returncode": 1,
            "stdout": "",
            "stderr": "Ya existe una preparación GA03 en ejecución.",
            "ok": False,
        }
    _write_ga03_progress_seed("Preparación GA03 solicitada desde /etl-status.")
    uploaded_csv = settings.project_root / "data" / "uploads" / "ga03_source.csv"
    args = ["--csv", str(uploaded_csv)] if uploaded_csv.exists() else None
    return _start_script("cargar_reservas_hoteleras_03.py", args=args)


def start_ga03_pipeline() -> dict:
    settings = get_settings()
    lock_path = settings.reports_dir / "pipeline_reservas_03.lock"
    if lock_path.exists():
        progress = ga03_pipeline_progress()
        if progress.get("stale"):
            try:
                lock_path.unlink()
            except OSError:
                pass
        elif _is_stale_timestamp(datetime.fromtimestamp(lock_path.stat().st_mtime, tz=timezone.utc).isoformat(), minutes=15):
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
    return _start_script("run_reservas_03_pipeline.py", log_name="pipeline_reservas_03.log")
