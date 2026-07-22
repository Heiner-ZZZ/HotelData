"""Guest-facing amenity catalog, request, and stock management endpoints."""

from __future__ import annotations

import logging

import gridfs
from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response

from src.database.connection import get_database
from src.app.security.dependencies import require_permission
from .service import (
    get_guest_amenity_catalog,
    list_amenity_stock,
    request_amenities,
    set_amenity_stock,
)

logger = logging.getLogger(__name__)

# Public guest router — no authentication required
guest_router = APIRouter(prefix="/api/amenities/guest", tags=["amenities-guest"])

# Public photos router — serves amenity photos by gridfs_id
photos_router = APIRouter(prefix="/api/amenities/photos", tags=["amenities-photos"])

# Admin/protected router for stock management
admin_router = APIRouter(prefix="/api/amenities/stock", tags=["amenities-stock"])


@guest_router.get("/catalog")
def guest_amenity_catalog_api(
    booking_id: str = Query(..., min_length=1),
):
    """Return the amenity catalog available for a guest's active booking.

    Includes available stock and prices, grouped by category.
    """
    result = get_guest_amenity_catalog(booking_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )
    return result


@guest_router.get("/catalog/by-prop")
def guest_amenity_catalog_by_prop_api(
    prop_id: int = Query(..., ge=1),
):
    """Return the amenity catalog for a given property (no booking needed).

    Used during booking creation to let guests/staff select amenities
    before a booking exists. Includes prices and stock but no booking context.
    """
    from src.app.modules.partner.services.content.amenities import amenities_payload_for_prop

# Note: the public amenity photos endpoint is now under photos_router (/api/amenities/photos/property/{prop_id})
# to avoid auth middleware — /api/amenities/guest requires authenticated roles.

    amenities_data = amenities_payload_for_prop(prop_id)
    catalog = amenities_data.get("catalog", [])

    # Enrich with stock info
    stock_list = list_amenity_stock(prop_id=prop_id)
    stock_map: dict[str, int] = {}
    for rec in stock_list:
        label = rec.get("amenity_label", "")
        avail = rec.get("available_stock", 0)
        if label and avail is not None:
            stock_map[label] = int(avail)

    for category in catalog:
        for item in category.get("items", []):
            label = item.get("label", "")
            item["available_stock"] = stock_map.get(label)  # None = unlimited

    return {
        "catalog": catalog,
        "active_amenities": amenities_data.get("active_amenities", []),
    }


@guest_router.post("/request")
def guest_amenity_request_api(
    payload: dict = Body(...),
):
    """Process an amenity request with stock validation.

    Validates stock for ALL items before creating charges.
    If any item lacks stock, the entire request is rejected.

    Request body:
    ```json
    {
      "booking_id": "BK-...",
      "items": [
        {"label": "Desayuno", "quantity": 2},
        {"label": "Spa", "quantity": 1}
      ]
    }
    ```
    """
    booking_id = str(payload.get("booking_id") or "")
    items = payload.get("items", [])

    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id is required.")
    if not items or not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a non-empty array.")

    try:
        result = request_amenities(booking_id, items)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to process amenity request for booking %s", booking_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Stock management (partner/staff only) ─────────────────────────


@admin_router.get("")
def stock_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    amenity_label: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("amenities.read")),
):
    """List amenity stock records with optional filters."""
    return list_amenity_stock(prop_id=prop_id, amenity_label=amenity_label)


@admin_router.put("")
def stock_set_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("amenities.manage")),
):
    """Set stock for an amenity (create or reset).

    Body: {"prop_id": 1, "amenity_label": "Spa", "total_stock": 10, "room_type_id": ""}
    When ``room_type_id`` is empty, applies hotel-wide.
    """
    try:
        result = set_amenity_stock(
            int(payload.get("prop_id") or 0),
            str(payload.get("amenity_label") or ""),
            total_stock=int(payload.get("total_stock") or 0),
            room_type_id=str(payload.get("room_type_id") or ""),
        )
        return result
    except ValueError as exc:            raise HTTPException(status_code=400, detail=str(exc)) from exc


# ═══ Public amenity photo serving ═══

@photos_router.get("/{photo_id}")
def serve_amenity_photo(photo_id: str):
    """Serve an amenity photo by its gridfs_id. Public — no auth."""
    try:
        oid = ObjectId(photo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de foto inválido.")
    fs = gridfs.GridFS(get_database())
    if not fs.exists(oid):
        raise HTTPException(status_code=404, detail="Foto no encontrada.")
    gf = fs.get(oid)
    return Response(
        content=gf.read(),
        media_type=gf.content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@photos_router.get("/property/{prop_id}")
def public_amenity_photos(prop_id: int):
    """Public endpoint — return amenity photo URLs for a property.
    Used by the hotel card to show real amenity images after placeholder pics."""
    db = get_database()
    docs = db.amenity_photos.find(
        {"prop_id": prop_id},
        {"_id": 0, "gridfs_id": 1, "amenity_label": 1},
    ).sort("uploaded_at", 1)
    return {
        "ok": True,
        "photos": [
            {
                "photo_id": str(d["gridfs_id"]),
                "amenity_label": d["amenity_label"],
                "url": f"/api/amenities/photos/{d['gridfs_id']}",
            }
            for d in docs
        ],
    }

