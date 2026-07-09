from __future__ import annotations

from fastapi import APIRouter

from src.app.modules.partner.schemas import ModuleStatus
from src.app.modules.partner.services import module_status

router = APIRouter(prefix="/modules/partner", tags=["modules-partner"])
web_router = APIRouter(prefix="/partner", tags=["partner"])
api_router = APIRouter(prefix="/api/management", tags=["management-api"])
legacy_admin_api_router = APIRouter(prefix="/api/admin", tags=["admin-legacy-api"])


@router.get("/status", response_model=ModuleStatus)
def partner_status() -> ModuleStatus:
    return module_status()


from . import audit, hotels, content, rooms, availability, rates, policies, amenities, reports, room_features, guests

__all__ = [
    "api_router",
    "legacy_admin_api_router",
    "router",
    "web_router",
]
