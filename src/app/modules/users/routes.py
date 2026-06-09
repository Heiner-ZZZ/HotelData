from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.users.schemas import ModuleStatus
from src.app.modules.users.service import module_status


router = APIRouter(prefix="/modules/users", tags=["modules-users"])


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
    return module_status()
