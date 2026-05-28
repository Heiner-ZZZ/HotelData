from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.app.features.audit.service import recent_activity


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


@router.get("/audit")
def audit(request: Request):
    return templates.TemplateResponse(
        request,
        "audit/index.html",
        {"activity": recent_activity()},
    )
