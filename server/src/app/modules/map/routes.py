"""Map & Geo-localization routes — CU-O35 to CU-O38.

- CU-O35: Edit destination metadata (name, coordinates, country, city, description)
- CU-O36: Edit hotel visible name (manual_override) — handled by partner module
- CU-O37: View world map with destinations and hotels geolocated
- CU-O38: Select destination location on interactive map
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.app.modules.map.schemas import DestinationUpdate
from src.app.modules.map.service import (
    get_destination,
    list_destinations,
    list_geo_destinations,
    list_hotels_with_geo,
    update_destination,
)
from src.app.security.dependencies import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/map", tags=["map"])


# ═══════════════════════════════════════════════
# CU-O35 & CU-O38: Destinations CRUD + Geo editor
# ═══════════════════════════════════════════════


@router.get("/destinations")
def destinations_list_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None),
    has_geo: bool | None = Query(default=None),
    current_user: dict = Depends(require_permission("settings.read")),
):
    """List destinations with optional search and geo filter (CU-O35)."""
    return list_destinations(page=page, page_size=page_size, search=search, has_geo=has_geo)


@router.get("/destinations/{destination_id}")
def destination_get_api(
    destination_id: int,
    current_user: dict = Depends(require_permission("settings.read")),
):
    """Get a single destination by ID."""
    result = get_destination(destination_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destino no encontrado")
    return result


@router.put("/destinations/{destination_id}")
def destination_update_api(
    destination_id: int,
    payload: DestinationUpdate = Body(...),
    current_user: dict = Depends(require_permission("settings.manage")),
):
    """Update destination metadata — name, coordinates, country, city, description (CU-O35, CU-O38)."""
    data = payload.model_dump(exclude_unset=True)
    result = update_destination(destination_id, data)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destino no encontrado")
    return result


# ═══════════════════════════════════════════════
# CU-O37: World map data
# ═══════════════════════════════════════════════


@router.get("/geo/destinations")
def geo_destinations_api(
    current_user: dict = Depends(require_permission("settings.read")),
):
    """List destinations with coordinates for map display (CU-O37)."""
    return {"items": list_geo_destinations()}


@router.get("/geo/hotels")
def geo_hotels_api(
    current_user: dict = Depends(require_permission("settings.read")),
):
    """List hotels with geo location (via destination) for map display (CU-O37)."""
    return {"items": list_hotels_with_geo()}
