"""Reservations routes package — split into focused submodules."""

from __future__ import annotations

from .management import management_api_router
from .reservations import api_router, router

__all__ = ["api_router", "management_api_router", "router"]
