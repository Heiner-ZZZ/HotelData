"""In-Stay (Mi Estancia) module — guest portal, chat, and service requests."""

from src.app.modules.instay.routes import (
    ensure_stay_collections,
    guest_router,
    staff_router,
)

__all__ = [
    "ensure_stay_collections",
    "guest_router",
    "staff_router",
]
