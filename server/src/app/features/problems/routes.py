from __future__ import annotations

from fastapi import APIRouter, Request
from src.app.template_utils import templates

from src.app.features.quality.service import quality_summary


router = APIRouter()


@router.get("/problems")
def problems(request: Request):
    return templates.TemplateResponse(
        request,
        "problems/index.html",
        {"quality": quality_summary()},
    )
