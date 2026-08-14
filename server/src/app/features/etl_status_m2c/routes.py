"""Rutas API del pipeline mongo_to_clickhouse (prefijo propio ``/etl-status/m2c``).

Mismo contrato visual que ``etl_status`` pero con identidad separada.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.app.features.etl_status_m2c.services import (
    consolidated,
    m2c_progress,
    start_pipeline,
    stop_pipeline,
    update_schedule,
)
from src.etl.mongo_to_clickhouse.config import REFRESH_MODES

JSON_API = APIRouter(prefix="/api")


class ScheduleUpdateRequest(BaseModel):
    schedule_cron: str = Field(..., min_length=5, max_length=64, description="Cron expression")
    enabled: bool = True
    # Modo de refresco de los KPIs: "full" (barrido con TRUNCATE) o
    # "incremental" (INSERT + dedup, sin borrar historial). El DAG horario
    # lee este mismo valor en cada corrida.
    refresh_mode: str = Field("full", description="full | incremental")


@JSON_API.get("/etl-status/m2c/consolidated")
def api_etl_status_m2c_consolidated():
    return consolidated()


@JSON_API.get("/etl-status/m2c/progress")
def api_etl_status_m2c_progress():
    return m2c_progress()


@JSON_API.post("/etl-status/m2c/run")
def api_etl_status_m2c_run():
    result = start_pipeline()
    return {
        "ok": result.get("ok", False),
        "pid": result.get("pid"),
        "display_message": result.get("display_message", ""),
        "summary_output": result.get("summary_output", ""),
    }


@JSON_API.post("/etl-status/m2c/stop")
def api_etl_status_m2c_stop():
    result = stop_pipeline()
    return {
        "ok": result.get("ok", False),
        "display_message": result.get("display_message", ""),
        "summary_output": result.get("summary_output", ""),
    }


@JSON_API.get("/etl-status/m2c/schedule")
def api_etl_status_m2c_schedule_get():
    from src.app.features.etl_status_m2c.services import get_schedule

    return get_schedule()


@JSON_API.put("/etl-status/m2c/schedule")
def api_etl_status_m2c_schedule_put(payload: ScheduleUpdateRequest):
    if payload.refresh_mode not in REFRESH_MODES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "message": f"refresh_mode inválido: {payload.refresh_mode!r} (válidos: {', '.join(REFRESH_MODES)})",
                "refresh_mode": payload.refresh_mode,
            },
        )
    result = update_schedule(
        payload.schedule_cron,
        payload.enabled,
        refresh_mode=payload.refresh_mode,
    )
    return {
        "ok": True,
        "schedule": result,
        "display_message": "Horario del pipeline mongo→clickhouse actualizado.",
        "summary_output": (
            f"Cron interno: {payload.schedule_cron} · habilitado: {payload.enabled} · "
            f"modo: {payload.refresh_mode}"
        ),
    }
