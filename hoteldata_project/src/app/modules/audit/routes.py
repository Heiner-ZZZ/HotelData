from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.audit.schemas import ModuleStatus
from src.app.modules.audit.service import module_status


router = APIRouter(prefix="/modules/audit", tags=["modules-audit"])


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
