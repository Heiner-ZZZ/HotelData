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


# ─── Visitor Countries (dim_visitor_countries) ─────────────────────────


@api_router.get("/visitor-countries", status_code=200)
def list_visitor_countries(
    current_user: dict = Depends(require_permission("users.manage")),
):
    """List visitor country dimensions from MongoDB dim_visitor_countries collection."""
    from src.database.connection import get_database

    db = get_database()
    cursor = db.dim_visitor_countries.find({}, {"_id": 0}).sort("visitor_location_country_id", 1)
    items = []
    for doc in cursor:
        items.append({
            "visitor_location_country_id": doc["visitor_location_country_id"],
            "country_display_name": doc.get("visitor_country_label") or doc.get("country_display_name") or f"País {doc['visitor_location_country_id']}"
        })
    return {"items": items}


@api_router.put("/visitor-countries/{country_id}", status_code=200)
def update_visitor_country(
    country_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Update country_display_name in dim_visitor_countries collection globally."""
    from src.database.connection import get_database

    db = get_database()
    new_name = payload.get("country_display_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="El nombre del país es requerido")

    db.dim_visitor_countries.update_one(
        {"visitor_location_country_id": country_id},
        {
            "$set": {
                "country_display_name": new_name,
                "country_name": new_name,
                "visitor_country_label": new_name,
            }
        },
    )
    return {"ok": True, "message": "Nombre del país actualizado exitosamente"}


# ─── Visitor Destinations (dim_destinations) ───────────────────────────


@api_router.get("/visitor-destinations", status_code=200)
def list_visitor_destinations(
    current_user: dict = Depends(require_permission("users.manage")),
):
    """List visitor destinations from dim_destinations collection."""
    from src.database.connection import get_database

    db = get_database()
    cursor = db.dim_destinations.find({}, {"_id": 0}).sort("srch_destination_id", 1)
    items = []
    for doc in cursor:
        items.append({
            "srch_destination_id": doc["srch_destination_id"],
            "destination_display_name": doc.get("destination_label") or doc.get("destination_display_name") or f"Destino {doc['srch_destination_id']}"
        })
    return {"items": items}


@api_router.put("/visitor-destinations/{dest_id}", status_code=200)
def update_visitor_destination(
    dest_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Update destination display name in dim_destinations collection."""
    from src.database.connection import get_database

    db = get_database()
    new_name = payload.get("destination_display_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="El nombre del destino es requerido")

    db.dim_destinations.update_one(
        {"srch_destination_id": dest_id},
        {
            "$set": {
                "destination_display_name": new_name,
                "destination_name": new_name,
                "destination_label": new_name,
            }
        },
    )
    return {"ok": True, "message": "Nombre del destino actualizado exitosamente"}


# ─── Visitor Sites (dim_sites) ─────────────────────────────────────────


@api_router.get("/visitor-sites", status_code=200)
def list_visitor_sites(
    current_user: dict = Depends(require_permission("users.manage")),
):
    """List visitor sites (channels) from dim_sites collection."""
    from src.database.connection import get_database

    db = get_database()
    cursor = db.dim_sites.find({}, {"_id": 0}).sort("site_id", 1)
    items = []
    for doc in cursor:
        items.append({
            "site_id": doc["site_id"],
            "site_display_name": doc.get("site_label") or doc.get("site_display_name") or f"Sitio {doc['site_id']}"
        })
    return {"items": items}


@api_router.put("/visitor-sites/{site_id}", status_code=200)
def update_visitor_site(
    site_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Update site display name in dim_sites collection."""
    from src.database.connection import get_database

    db = get_database()
    new_name = payload.get("site_display_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="El nombre del sitio es requerido")

    db.dim_sites.update_one(
        {"site_id": site_id},
        {
            "$set": {
                "site_display_name": new_name,
                "site_name": new_name,
                "site_label": new_name,
            }
        },
    )
    return {"ok": True, "message": "Nombre del sitio/canal actualizado exitosamente"}


# ─── Visitor Hotels (dim_hotels) ───────────────────────────────────────


@api_router.get("/visitor-hotels", status_code=200)
def list_visitor_hotels(
    current_user: dict = Depends(require_permission("users.manage")),
):
    """List visitor hotels from dim_hotels collection."""
    from src.database.connection import get_database

    db = get_database()
    cursor = db.dim_hotels.find({}, {"_id": 0}).sort("prop_id", 1)
    items = []
    for doc in cursor:
        items.append({
            "prop_id": doc["prop_id"],
            "hotel_name": doc.get("display_name") or doc.get("hotel_name") or doc.get("hotel_label") or f"Hotel {doc['prop_id']}"
        })
    return {"items": items}


@api_router.put("/visitor-hotels/{prop_id}", status_code=200)
def update_visitor_hotel(
    prop_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Update hotel name in dim_hotels collection."""
    from src.database.connection import get_database

    db = get_database()
    new_name = payload.get("hotel_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="El nombre del hotel es requerido")

    db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {
            "$set": {
                "hotel_name": new_name,
                "hotel_label": new_name,
                "display_name": new_name,
            }
        },
    )
    return {"ok": True, "message": "Nombre del hotel actualizado exitosamente"}


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
