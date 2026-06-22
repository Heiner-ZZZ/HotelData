from __future__ import annotations

from fastapi import APIRouter, Request
from src.app.template_utils import templates

from src.app.features.collections.service import collection_counts
from src.app.features.dashboard.service import dashboard_overview
from src.app.features.quality.service import quality_summary


router = APIRouter()
api_router = APIRouter(prefix="/api/dashboard", tags=["dashboard-api"])


@router.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "counts": collection_counts(),
            "quality": quality_summary(),
            "overview": dashboard_overview(),
        },
    )


@api_router.get("/overview")
def dashboard_overview_api():
    return {
        "counts": collection_counts(),
        "quality": quality_summary(),
        "overview": dashboard_overview(),
    }
