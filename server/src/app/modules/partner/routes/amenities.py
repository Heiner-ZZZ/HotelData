from __future__ import annotations

import uuid
from datetime import UTC, datetime

import gridfs
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    management_property_options,
    partner_hotel_content,
    save_partner_hotel_amenities,
)
from src.app.modules.partner.services.content.amenities import (
    _GLOBAL_DEFAULTS_PROP_ID,
    _get_price_defaults,
    _load_price_defaults_from_db,
    invalidate_price_defaults_cache,
)
from src.app.security.dependencies import (
    require_login,
    require_permission,
    require_prop_permission,
)
from src.app.security.hotel_filter import user_can_access_hotel
from src.database.connection import get_database


@api_router.get("/amenities")
def amenities_api(prop_id: int = Query(..., ge=1), room_type_id: str = Query(default="")):
    detail = partner_hotel_content(require_prop_id(prop_id), room_type_id=room_type_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/amenities/options")
def amenities_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    """Selector de amenities: login-only, catálogo por asignación.

    Opción 2 (2026-08): sin prop_id devuelve la lista ligera de propiedades
    del scope del usuario (sin códigos globales). Con prop_id el catálogo del
    hotel se restringe por ASIGNACIÓN (``user_can_access_hotel``): un usuario
    sin ese hotel asignado recibe 403 (sin fuga cross-hotel).
    """
    if prop_id is not None and not user_can_access_hotel(current_user, prop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este hotel",
        )
    response: dict[str, object] = {"properties": management_property_options(user=current_user)}
    if prop_id:
        detail = partner_hotel_content(require_prop_id(prop_id))
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        response["catalog"] = detail.get("amenities", {}).get("catalog", [])
        response["active_amenities"] = detail.get("amenities", {}).get("active_amenities", [])
    return response


@api_router.put("/amenities/special-requests")
def special_requests_update_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("amenities.manage")),
):
    """Replace the hotel's special-requests catalog.

    Body: ``{"prop_id", "special_requests": [{label, unit_price, flags}]}``.
    Returns the normalized catalog. Migración E: prop_id por QUERY + consistencia
    query↔body.
    """
    from src.app.modules.partner.services.content.save import save_special_requests
    from src.app.modules.partner.services.content.special_requests import (
        special_requests_payload_for_prop,
    )

    prop_id = require_prop_id(query_prop_id)
    body_prop_id = int(payload.get("prop_id") or 0)
    if body_prop_id != prop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prop_id del query y del body no coinciden",
        )
    raw = payload.get("special_requests")
    if not isinstance(raw, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="special_requests debe ser una lista")
    try:
        saved = save_special_requests(
            prop_id,
            special_requests=raw,
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return {
        "special_requests": special_requests_payload_for_prop(prop_id),
    }


@api_router.put("/amenities")
def amenities_update_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("amenities.manage")),
):
    """Update hotel amenities (Migración E: prop_id por QUERY + consistencia)."""
    prop_id = require_prop_id(query_prop_id)
    body_prop_id = int(payload.get("prop_id") or 0)
    if body_prop_id != prop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prop_id del query y del body no coinciden",
        )
    active_amenities = payload.get("active_amenities") or []
    if not isinstance(active_amenities, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="active_amenities must be a list")
    room_type_id = str(payload.get("room_type_id") or "")
    amenity_prices: dict[str, float] = {}
    raw_prices = payload.get("amenity_prices")
    if isinstance(raw_prices, dict):
        for k, v in raw_prices.items():
            try:
                amenity_prices[str(k)] = float(v)
            except (ValueError, TypeError):
                pass

    saved = save_partner_hotel_amenities(
        prop_id,
        active_amenities=[str(item) for item in active_amenities],
        amenities_text=str(payload.get("amenities_text") or ""),
        amenity_prices=amenity_prices,
        room_type_id=room_type_id,
        changed_by=current_user.get("username", "system"),
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    # Return the full detail format (same as GET) so the frontend mapper
    # can parse it as AmenitiesDto without crashing.
    return partner_hotel_content(prop_id, room_type_id=room_type_id)


# ═══ Amenity Photos ═══

_PHOTO_MAX_COUNT = 5
_PHOTO_MAX_SIZE = 2 * 1024 * 1024  # 2 MB
_PHOTO_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _ensure_amenity_photos_indexes():
    db = get_database()
    existing = db.amenity_photos.index_information()
    if "prop_amenity_label" not in existing:
        db.amenity_photos.create_index(
            [("prop_id", 1), ("amenity_label", 1)],
            name="prop_amenity_label",
        )


@api_router.post("/amenities/photos")
async def upload_amenity_photo(
    prop_id: int = Query(..., ge=1),
    amenity_label: str = Query(..., min_length=1),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_prop_permission("amenities.manage")),
):
    """Upload a photo for a specific active amenity. Max 5 per amenity."""
    if file.content_type not in _PHOTO_ALLOWED_TYPES:
        return JSONResponse(
            {"ok": False, "message": "Formato no permitido. Usa JPG, PNG o WebP."},
            status_code=400,
        )
    content = await file.read()
    if len(content) > _PHOTO_MAX_SIZE:
        return JSONResponse(
            {"ok": False, "message": "La imagen no puede superar los 2 MB."},
            status_code=400,
        )

    db = get_database()
    _ensure_amenity_photos_indexes()

    # Limit to max 5 photos per amenity
    existing_count = db.amenity_photos.count_documents(
        {"prop_id": prop_id, "amenity_label": amenity_label}
    )
    if existing_count >= _PHOTO_MAX_COUNT:
        return JSONResponse(
            {"ok": False, "message": f"Máximo {_PHOTO_MAX_COUNT} fotos por amenidad."},
            status_code=400,
        )

    fs = gridfs.GridFS(db)
    filename = f"amenity_{prop_id}_{amenity_label[:20]}_{uuid.uuid4().hex[:8]}"
    gridfs_id = fs.put(content, filename=filename, content_type=file.content_type)

    doc = {
        "prop_id": prop_id,
        "amenity_label": amenity_label,
        "gridfs_id": gridfs_id,
        "content_type": file.content_type,
        "filename": filename,
        "uploaded_by": current_user.get("username", "system"),
        "uploaded_at": datetime.now(UTC),
    }
    db.amenity_photos.insert_one(doc)
    return {"ok": True, "photo_id": str(gridfs_id), "message": "Foto subida."}


@api_router.delete("/amenities/photos/{photo_id}")
def delete_amenity_photo(
    photo_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("amenities.manage")),
):
    """Delete an amenity photo by its gridfs_id.

    Migración E: la foto debe pertenecer al hotel pedido (404 cross-hotel;
    el doc ``amenity_photos`` guarda ``prop_id``).
    """
    db = get_database()
    _ensure_amenity_photos_indexes()
    try:
        oid = ObjectId(photo_id)
    except (InvalidId, ValueError):
        return JSONResponse({"ok": False, "message": "ID inválido."}, status_code=400)

    doc = db.amenity_photos.find_one({"gridfs_id": oid}, {"prop_id": 1})
    if not doc:
        return JSONResponse({"ok": False, "message": "Foto no encontrada."}, status_code=404)
    # Cross-hotel (Migración E): la foto debe pertenecer al hotel pedido — 404
    # para no filtrar la existencia.
    if doc.get("prop_id") != query_prop_id:
        return JSONResponse({"ok": False, "message": "Foto no encontrada."}, status_code=404)

    db.amenity_photos.delete_one({"gridfs_id": oid})
    fs = gridfs.GridFS(db)
    if fs.exists(oid):
        fs.delete(oid)
    return {"ok": True, "message": "Foto eliminada."}


# ═══ Amenity Price Defaults (global, not per-hotel) ═══


@api_router.get("/amenities/default-prices")
def get_amenity_default_prices_api(
    current_user: dict = Depends(require_permission("amenities.read")),
):
    """Return all global amenity price defaults from MongoDB."""
    defaults = _get_price_defaults()
    items = [
        {"label": label, "default_price": price}
        for label, price in sorted(defaults.items(), key=lambda x: x[0])
    ]
    return {"ok": True, "defaults": items, "count": len(items)}


@api_router.put("/amenities/default-prices")
def update_amenity_default_prices_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("amenities.manage")),
):
    """Update global amenity price defaults.

    Accepts a list of {label, default_price} objects.
    Upserts each one into the ``amenity_price_defaults`` collection.
    Invalidates the in-memory cache so subsequent lookups use fresh data.

    Body example:
    ```json
    {
      "defaults": [
        {"label": "spa", "default_price": 45.0},
        {"label": "taxi", "default_price": 20.0}
      ]
    }
    ```
    """
    items = payload.get("defaults")
    if not isinstance(items, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'defaults' debe ser una lista de {label, default_price}.",
        )

    db = get_database()
    existing = db.hotel_content_pages.find_one(
        {"prop_id": _GLOBAL_DEFAULTS_PROP_ID},
        {"_id": 0, "amenity_prices": 1},
    )
    prices: dict[str, float] = dict((existing or {}).get("amenity_prices") or {})
    upserted = 0
    for item in items:
        label = (item.get("label") or "").strip()
        if not label:
            continue
        try:
            price = float(item.get("default_price", 0))
        except (ValueError, TypeError):
            price = 0.0
        prices[label] = price
        upserted += 1

    db.hotel_content_pages.update_one(
        {"prop_id": _GLOBAL_DEFAULTS_PROP_ID},
        {
            "$set": {
                "amenity_prices": prices,
                "updated_at": datetime.now(UTC),
                "updated_by": current_user.get("username", "system"),
            },
            "$setOnInsert": {"prop_id": _GLOBAL_DEFAULTS_PROP_ID, "created_at": datetime.now(UTC)},
        },
        upsert=True,
    )

    # Invalidate cache so the next read picks up changes
    invalidate_price_defaults_cache()
    # Reload immediately so the response reflects new state
    reloaded = _load_price_defaults_from_db()

    return {
        "ok": True,
        "upserted": upserted,
        "count": len(reloaded),
        "message": f"{upserted} precio(s) por defecto actualizado(s).",
    }


@api_router.get("/amenities/photos")
def list_amenity_photos(
    prop_id: int = Query(..., ge=1),
    amenity_label: str = Query(default=""),
    current_user: dict = Depends(require_prop_permission("amenities.read")),
):
    """List photos for amenities of a property. Optionally filter by amenity_label.
    Returns list of {photo_id, amenity_label, url}."""
    db = get_database()
    _ensure_amenity_photos_indexes()
    query: dict = {"prop_id": prop_id}
    if amenity_label:
        query["amenity_label"] = amenity_label
    docs = db.amenity_photos.find(query, {"_id": 0}).sort("uploaded_at", 1)
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
