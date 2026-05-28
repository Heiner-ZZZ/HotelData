from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.app.features.collections.service import collection_counts
from src.app.features.dashboard.service import dashboard_overview
from src.app.features.quality.service import quality_summary


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


@router.get("/")
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
