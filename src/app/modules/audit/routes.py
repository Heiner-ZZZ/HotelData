from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.app.modules.audit.schemas import ModuleStatus, RecentActivity
from src.app.modules.audit.service import module_status, recent_activity


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
templates.env.cache = None


@router.get("/audit", response_model=None)
def audit(request: Request):
    return templates.TemplateResponse(
        request,
        "audit/index.html",
        {"activity": recent_activity().model_dump()},
    )


@router.get("/api/audit/activity", response_model=RecentActivity)
def api_audit_activity() -> RecentActivity:
    return recent_activity()


@router.get("/modules/audit/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
