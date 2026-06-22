from __future__ import annotations

from fastapi import APIRouter, Request
from src.app.template_utils import templates


router = APIRouter()


@router.get("/company")
def company(request: Request):
    return templates.TemplateResponse(request, "company/index.html", {})
