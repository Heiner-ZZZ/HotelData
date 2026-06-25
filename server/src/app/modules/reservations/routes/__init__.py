"""Reservations routes package — split into focused submodules."""

from __future__ import annotations

from .reservations import router, api_router
from .management import management_api_router

__all__ = ["router", "api_router", "management_api_router"]
