from __future__ import annotations

from fastapi import APIRouter, Depends

from src.app.modules.audit.schemas import ModuleStatus, RecentActivity
from src.app.modules.audit.service import module_status, recent_activity
from src.app.security.dependencies import require_permission


router = APIRouter()


@router.get("/audit")
def audit(current_user: dict = Depends(require_permission("audit.read"))):
    return {"activity": recent_activity().model_dump()}


@router.get("/api/audit/activity", response_model=RecentActivity)
def api_audit_activity(current_user: dict = Depends(require_permission("audit.read"))) -> RecentActivity:
    return recent_activity()


@router.get("/modules/audit/status", response_model=ModuleStatus)
def status(current_user: dict = Depends(require_permission("audit.read"))) -> ModuleStatus:
    return module_status()
