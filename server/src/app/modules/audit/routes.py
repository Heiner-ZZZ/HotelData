from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.audit.schemas import ModuleStatus, RecentActivity
from src.app.modules.audit.service import module_status, recent_activity


router = APIRouter()


@router.get("/audit")
def audit():
    return {"activity": recent_activity().model_dump()}


@router.get("/api/audit/activity", response_model=RecentActivity)
def api_audit_activity() -> RecentActivity:
    return recent_activity()


@router.get("/modules/audit/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
