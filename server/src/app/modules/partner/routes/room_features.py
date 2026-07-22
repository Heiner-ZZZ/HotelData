"""Room features API endpoints."""

from __future__ import annotations

from fastapi import Body, Depends, HTTPException, Query, status

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services.rooms.features import (
    add_custom_feature,
    get_all_features,
    get_room_type_features,
    update_room_type_features,
)
from src.app.security.dependencies import require_permission


@api_router.get("/room-features")
def room_features_list_api(
    current_user: dict = Depends(require_permission("rooms.read")),
):
    """Return the master catalog of available features, grouped by category."""
    return {"features": get_all_features()}


@api_router.get("/room-features/{room_type_id}")
def room_features_get_api(
    room_type_id: str,
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_permission("rooms.read")),
):
    """Return feature tags for a specific room type."""
    features = get_room_type_features(require_prop_id(prop_id), room_type_id)
    return {"room_type_id": room_type_id, "features": features}


@api_router.put("/room-features/{room_type_id}")
def room_features_update_api(
    room_type_id: str,
    prop_id: int = Query(..., ge=1),
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rooms.update")),
):
    """Set feature tags for a room type. Accepts a list of strings (legacy) or
    list of objects with ``label`` and optional ``unit_price``."""
    features_raw = payload.get("features", [])
    if not isinstance(features_raw, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="features must be a list")

    # Preserve objects; convert strings to objects in update_room_type_features
    result = update_room_type_features(
        require_prop_id(prop_id),
        room_type_id,
        features=features_raw,
        changed_by=current_user.get("username", "angular_api"),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return result


@api_router.post("/room-features/custom")
def room_features_add_custom_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rooms.update")),
):
    """Add a custom feature to the master catalog."""
    try:
        result = add_custom_feature(
            label=str(payload.get("label", "")),
            category=str(payload.get("category", "")),
            icon=str(payload.get("icon", "")),
            changed_by=current_user.get("username", "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result
