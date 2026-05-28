from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.templating import Jinja2Templates

from src.app.features.etl_status.service import (
    clear_ga03_local_evidence,
    execution_status,
    ga03_artifact_status,
    ga03_config_status,
    ga03_mongodb_status,
    ga03_pocketbase_status,
    ga03_pipeline_progress,
    ga03_preparation_progress,
    ga03_report_status,
    raw_file_status,
    run_ga03_dataset_validation,
    run_ga03_pipeline,
    run_local_etl,
    run_seed_master_collections,
    save_ga03_source_csv,
    save_uploaded_raw_csv,
    start_ga03_pipeline,
    start_ga03_seed_source,
)


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


def _summarize_output(result: dict) -> str:
    output = result.get("stderr") or result.get("stdout") or ""
    output = output.strip()
    if "hotel_reservation_events_03" in output and "404 Client Error" in output:
        return "Colección GA03 no creada todavía. Prepare la fuente antes de continuar."
    if len(output) > 1200:
        return f"{output[:1200].rstrip()}\n..."
    return output


def _ga03_action_result(result: dict, *, success_message: str, failure_message: str) -> dict:
    result["display_message"] = success_message if result.get("ok") else failure_message
    result["summary_output"] = _summarize_output(result)
    return result


def _etl_context(request: Request, *, upload_message: str = "", action_result: dict | None = None) -> dict:
    return {
        "status": execution_status(),
        "raw_file": raw_file_status(),
        "upload_message": upload_message,
        "action_result": action_result,
        "ga03_config": ga03_config_status(),
        "ga03_pocketbase": ga03_pocketbase_status(),
        "ga03_mongodb": ga03_mongodb_status(),
        "ga03_progress": ga03_preparation_progress(),
        "ga03_pipeline_progress": ga03_pipeline_progress(),
        "ga03_artifacts": ga03_artifact_status(),
        "ga03_reports": ga03_report_status(),
        "ga03_seed_confirm_token": "PREPARAR_GA03",
    }


@router.get("/etl-status")
def etl_status(request: Request):
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, upload_message=request.query_params.get("message", "")),
    )


@router.post("/etl-status/upload")
async def upload_raw_csv(request: Request, dataset_file: UploadFile = File(...)):
    content = await dataset_file.read()
    raw_file = save_uploaded_raw_csv(dataset_file.filename or "dataset.csv", content)
    message = f"Archivo cargado: {raw_file.get('uploaded_filename', raw_file['filename'])}"
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        {**_etl_context(request, upload_message=message), "raw_file": raw_file},
    )


@router.post("/etl-status/seed")
def trigger_seed(request: Request):
    result = run_seed_master_collections()
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, action_result=result),
    )


@router.post("/etl-status/run")
def trigger_etl(request: Request):
    result = run_local_etl()
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, action_result=result),
    )


@router.post("/etl-status/ga03/validate")
def trigger_ga03_validation(request: Request):
    pocketbase_status = ga03_pocketbase_status()
    if pocketbase_status.get("state") != "ready":
        result = {
            "command": "scripts/validar_dataset_reservas_03.py",
            "returncode": 1,
            "stdout": "",
            "stderr": "",
            "ok": False,
            "display_message": "Validación GA03 fallida.",
            "summary_output": "No se ejecutó la validación: la fuente GA03 debe estar lista en PocketBase.",
        }
    else:
        result = _ga03_action_result(
            run_ga03_dataset_validation(),
            success_message="Validación GA03 ejecutada.",
            failure_message="Validación GA03 fallida.",
        )
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, action_result=result),
    )


@router.post("/etl-status/ga03/run")
def trigger_ga03_pipeline(request: Request):
    pocketbase_status = ga03_pocketbase_status()
    if pocketbase_status.get("state") != "ready":
        result = {
            "command": "scripts/run_reservas_03_pipeline.py",
            "returncode": 1,
            "stdout": "",
            "stderr": "",
            "ok": False,
            "display_message": "Pipeline GA03 fallido.",
            "summary_output": "No se ejecutó el pipeline: la fuente GA03 debe estar lista en PocketBase.",
        }
    else:
        result = _ga03_action_result(
            start_ga03_pipeline(),
            success_message="Pipeline GA03 iniciado.",
            failure_message="Pipeline GA03 fallido.",
        )
        result["summary_output"] = "Pipeline GA03 iniciado en segundo plano. Use Actualizar para revisar MongoDB y reportes."
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, action_result=result),
    )


@router.post("/etl-status/ga03/seed")
def trigger_ga03_seed(request: Request):
    result = _ga03_action_result(
        start_ga03_seed_source(),
        success_message="Preparación GA03 iniciada.",
        failure_message="Preparación GA03 fallida.",
    )
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, action_result=result),
    )


@router.post("/etl-status/ga03/upload-csv")
async def upload_ga03_source_csv(request: Request, ga03_source_file: UploadFile = File(...)):
    content = await ga03_source_file.read()
    uploaded = save_ga03_source_csv(ga03_source_file.filename or "ga03_source.csv", content)
    message = f"CSV fuente GA03 cargado: {uploaded['uploaded_filename']}"
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, upload_message=message),
    )


@router.post("/etl-status/ga03/clear-evidence")
def clear_ga03_evidence(request: Request):
    result = clear_ga03_local_evidence()
    deleted_count = len(result.get("deleted", []))
    result = _ga03_action_result(
        result,
        success_message="Evidencia local GA03 limpiada.",
        failure_message="No se pudo limpiar la evidencia local GA03.",
    )
    result["summary_output"] = f"Se eliminaron {deleted_count} archivos locales GA03."
    return templates.TemplateResponse(
        request,
        "etl_status/index.html",
        _etl_context(request, action_result=result),
    )
