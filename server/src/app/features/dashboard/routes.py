from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from src.app.features.collections.service import collection_counts
from src.app.features.dashboard.kpi_service import get_kpis, refresh_kpis
from src.app.features.dashboard.service import dashboard_overview
from src.app.features.quality.service import quality_summary


logger = logging.getLogger(__name__)
router = APIRouter()
api_router = APIRouter(prefix="/api/dashboard", tags=["dashboard-api"])


def _build_dashboard_response() -> dict[str, Any]:
    """Build the full dashboard payload with error boundary."""
    return {
        "counts": collection_counts(),
        "quality": quality_summary(),
        "overview": dashboard_overview(),
    }


@router.get("/dashboard")
def dashboard():
    try:
        return _build_dashboard_response()
    except Exception:
        logger.exception("Dashboard page failed")
        return {"error": "Error interno al cargar el dashboard. Revisa los logs del servidor."}


@api_router.get("/kpis")
def dashboard_kpis():
    try:
        return get_kpis()
    except Exception:
        logger.exception("Dashboard KPIs failed")
        return {"error": "Error al leer KPIs cacheados."}


@api_router.post("/kpis/refresh")
def dashboard_kpis_refresh():
    try:
        return refresh_kpis()
    except Exception:
        logger.exception("Dashboard KPIs refresh failed")
        return {"error": "Error al refrescar KPIs."}


@api_router.get("/overview")
def dashboard_overview_api():
    try:
        return _build_dashboard_response()
    except Exception:
        logger.exception("Dashboard API failed")
        return {"error": "Error interno al cargar el dashboard. Revisa los logs del servidor."}
