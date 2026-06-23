from __future__ import annotations

from fastapi import APIRouter, File, Query, UploadFile

from src.app.features.etl_status.services import (
    artifact_status,
    clear_local_evidence,
    config_status,
    execution_status,
    mongodb_status,
    pipeline_progress,
    pocketbase_status,
    preparation_progress,
    raw_file_status,
    report_status,
    run_dataset_validation,
    run_local_etl,
    run_pipeline,
    run_seed_master_collections,
    save_ga03_source_csv,
    save_uploaded_raw_csv,
    start_pipeline,
    start_seed_source,
    stop_etl,
)

JSON_API = APIRouter(prefix="/api")


# JSON API endpoints for the Angular frontend


@JSON_API.get("/etl-status/services")
def api_etl_status_services():
    return {
        "config": config_status(),
        "pocketbase": pocketbase_status(),
        "mongodb": mongodb_status(),
        "artifacts": artifact_status(),
    }


@JSON_API.get("/etl-status/reports")
def api_etl_status_reports():
    return report_status()


@JSON_API.get("/etl-status/execution")
def api_etl_status_execution():
    return execution_status()


@JSON_API.get("/etl-status/ga03/progress")
def api_etl_status_ga03_progress():
    return {
        "preparation": preparation_progress(),
        "pipeline": pipeline_progress(),
    }


@JSON_API.post("/etl-status/ga03/upload-csv")
async def api_etl_status_ga03_upload_csv(ga03_source_file: UploadFile = File(...)):
    content = await ga03_source_file.read()
    uploaded = save_ga03_source_csv(ga03_source_file.filename or "ga03_source.csv", content)
    return {
        "ok": True,
        "uploaded_filename": uploaded.get("uploaded_filename", ""),
        "display_message": f"CSV fuente GA03 cargado: {uploaded.get('uploaded_filename', '')}",
    }


@JSON_API.post("/etl-status/ga03/validate")
def api_etl_status_ga03_validate(target: int = Query(0, ge=0)):
    pb_status = pocketbase_status()
    if pb_status.get("state") != "ready":
        return {
            "ok": False,
            "display_message": "Validación GA03 fallida.",
            "summary_output": "La fuente GA03 debe estar lista en PocketBase.",
        }
    result = run_dataset_validation(target_records=target)
    return {
        "ok": result.get("ok", False),
        "target_records": target,
        "display_message": "Validación GA03 ejecutada." if result.get("ok") else "Validación GA03 fallida.",
        "summary_output": result.get("stdout", "") or result.get("stderr", "") or "",
    }


@JSON_API.post("/etl-status/ga03/run")
def api_etl_status_ga03_run(target: int = Query(0, ge=0)):
    pb_status = pocketbase_status()
    if pb_status.get("state") != "ready":
        return {
            "ok": False,
            "display_message": "Pipeline GA03 fallido.",
            "summary_output": "La fuente GA03 debe estar lista en PocketBase.",
        }
    result = start_pipeline(target_records=target)
    return {
        "ok": result.get("ok", False),
        "target_records": target,
        "pid": result.get("pid"),
        "display_message": "Pipeline GA03 iniciado." if result.get("ok") else "Pipeline GA03 fallido.",
        "summary_output": "Pipeline GA03 iniciado en segundo plano." if result.get("ok") else (result.get("stderr", "") or ""),
    }


@JSON_API.post("/etl-status/ga03/seed")
def api_etl_status_ga03_seed(target: int = Query(0, ge=0)):
    result = start_seed_source(target_records=target)
    return {
        "ok": result.get("ok", False),
        "target_records": target,
        "display_message": "Preparación GA03 iniciada." if result.get("ok") else "Preparación GA03 fallida.",
        "summary_output": result.get("stdout", "") or result.get("stderr", "") or "",
    }


@JSON_API.post("/etl-status/ga03/clear-evidence")
def api_etl_status_ga03_clear_evidence():
    result = clear_local_evidence()
    return {
        "ok": result.get("ok", False),
        "deleted_count": len(result.get("deleted", [])),
        "display_message": "Evidencia local GA03 limpiada." if result.get("ok") else "No se pudo limpiar la evidencia.",
    }


@JSON_API.post("/etl-status/ga03/stop")
def api_etl_status_ga03_stop(process: str = Query("seed")):
    if process not in ("seed", "pipeline"):
        return {"ok": False, "display_message": f"Tipo de proceso inválido: {process}. Use 'seed' o 'pipeline'."}
    result = stop_etl(process)
    return {
        "ok": result.get("ok", False),
        "display_message": f"Detención de {process} solicitada." if result.get("ok") else f"No se pudo detener {process}.",
        "summary_output": result.get("stdout", ""),
    }
