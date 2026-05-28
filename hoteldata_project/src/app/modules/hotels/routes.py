from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.hotels.schemas import ModuleStatus
from src.app.modules.hotels.service import module_status


router = APIRouter(prefix="/modules/hotels", tags=["modules-hotels"])


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
