from __future__ import annotations

from fastapi import APIRouter, Request
from src.app.template_utils import templates

from src.app.features.quality.service import quality_summary


router = APIRouter()


@router.get("/quality")
def quality(request: Request):
    return templates.TemplateResponse(
        request,
        "quality/index.html",
        {"quality": quality_summary()},
    )
