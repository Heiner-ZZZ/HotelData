"""Servicios del módulo ``etl_status_m2c`` (mismo patrón de exports que etl_status)."""

from src.app.features.etl_status_m2c.services.consolidated_service import consolidated
from src.app.features.etl_status_m2c.services.progress_service import m2c_progress
from src.app.features.etl_status_m2c.services.run_service import start_pipeline, stop_pipeline
from src.app.features.etl_status_m2c.services.schedule_service import get_schedule, update_schedule

__all__ = [
    "consolidated",
    "m2c_progress",
    "start_pipeline",
    "stop_pipeline",
    "get_schedule",
    "update_schedule",
]
