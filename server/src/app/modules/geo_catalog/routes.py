"""FastAPI routes for the geographic catalog module."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.app.modules.geo_catalog.schemas import GeoEntryCreate, GeoEntryUpdate
from src.app.modules.geo_catalog.service import (
    create_geo_entry,
    delete_geo_entry,
    get_geo_entry,
    list_geo_entries,
    resolve_display_names,
    update_geo_entry,
)
from src.app.security.dependencies import require_permission

api_router = APIRouter(prefix="/api/geo", tags=["geo-catalog"])


@api_router.get("/entries", status_code=200)
def geo_list(
    type: str | None = Query(default=None, alias="type"),
    country_code: str | None = Query(default=None),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """List geographic catalog entries with optional filtering."""
    return list_geo_entries(
        geo_type=type,
        country_code=country_code,
        q=q,
        page=page,
        page_size=page_size,
    )


@api_router.post("/entries", status_code=201)
def geo_create(
    payload: GeoEntryCreate = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Create a new geographic catalog entry."""
    try:
        return create_geo_entry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@api_router.get("/entries/{entry_id}")
def geo_get(
    entry_id: str,
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Get a single geographic catalog entry."""
    result = get_geo_entry(entry_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    return result


@api_router.put("/entries/{entry_id}")
def geo_update(
    entry_id: str,
    payload: GeoEntryUpdate = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Update a geographic catalog entry."""
    try:
        result = update_geo_entry(entry_id, payload)
        if result is None:
            raise HTTPException(status_code=404, detail="Entrada no encontrada")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@api_router.delete("/entries/{entry_id}")
def geo_delete(
    entry_id: str,
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Delete a geographic catalog entry."""
    deleted = delete_geo_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    return {"ok": True, "message": "Entrada eliminada"}


# ─── Resolve IDs to display names ──────────────────────────────────────


@api_router.post("/resolve")
def geo_resolve(
    body: dict[str, Any] = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Resolve numeric IDs (srch_destination_id, visitor_location_country_id, site_id) to display names."""
    destination_ids = body.get("destination_ids", [])
    country_ids = body.get("country_ids", [])
    site_ids = body.get("site_ids", [])
    return resolve_display_names(
        destination_ids=destination_ids,
        country_ids=country_ids,
        site_ids=site_ids,
    )
