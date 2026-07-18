"""In-Stay (Mi Estancia) module — guest portal, chat, and service requests."""

from src.app.modules.instay.routes import guest_router, staff_router
from src.app.modules.instay.routes_impl._helpers import ensure_stay_collections

__all__ = [
    "ensure_stay_collections",
    "guest_router",
    "staff_router",
]
