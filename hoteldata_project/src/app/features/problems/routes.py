from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.app.features.quality.service import quality_summary


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


@router.get("/problems")
def problems(request: Request):
    return templates.TemplateResponse(
        request,
        "problems/index.html",
        {"quality": quality_summary()},
    )
