"""Guests route — list guests by property with search and pagination."""

from __future__ import annotations

from fastapi import Depends, Query

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services.guests import list_guests_for_prop
from src.app.security.dependencies import require_login


@api_router.get("/guests")
def guests_list_api(
    prop_id: int = Query(..., ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List guests (deduplicated by email) for a property, with search + pagination."""
    return list_guests_for_prop(prop_id, q=q, page=page, page_size=page_size)
