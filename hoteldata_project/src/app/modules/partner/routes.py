from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.partner.schemas import ModuleStatus
from src.app.modules.partner.service import module_status


router = APIRouter(prefix="/modules/partner", tags=["modules-partner"])


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
