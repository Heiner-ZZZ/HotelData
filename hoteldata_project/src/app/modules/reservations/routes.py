from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.reservations.schemas import ModuleStatus
from src.app.modules.reservations.service import module_status


router = APIRouter(prefix="/modules/reservations", tags=["modules-reservations"])


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
