from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.revenue.schemas import ModuleStatus
from src.app.modules.revenue.service import module_status


router = APIRouter(prefix="/modules/revenue", tags=["modules-revenue"])


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
