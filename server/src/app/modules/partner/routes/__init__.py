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


from . import (
    amenities,
    audit,
    availability,
    content,
    currencies,
    guests,
    hotels,
    manual_reservations,
    policies,
    public_currencies,
    rates,
    reports,
    room_features,
    rooms,
)

# Wire the public router so it can be mounted from main.py (no auth required).
public_router = public_currencies.public_router

__all__ = [
    "api_router",
    "legacy_admin_api_router",
    "router",
    "web_router",
]
