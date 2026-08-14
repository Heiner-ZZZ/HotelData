from __future__ import annotations

import uuid

from fastapi import Body, Depends, Form, HTTPException, Query, Request, status, UploadFile
from fastapi.responses import JSONResponse

from src.app.modules.partner.routes import api_router, web_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_room_type,
    create_roh_room_type,
    delete_room_type,
    partner_hotel_detail,
    partner_hotel_rooms,
    update_room_type,
)
from src.app.modules.partner.services.properties.listing import list_property_options
from src.app.security.dependencies import require_permission


@web_router.get("/hotels/{prop_id}/rooms")
def rooms(request: Request, prop_id: int):
    detail = partner_hotel_rooms(prop_id)
    if detail is None:
        return JSONResponse({"error": "Property not found"}, status_code=404)
    return detail


@web_router.get("/hotels/{prop_id}/rooms/new")
def rooms_new(request: Request, prop_id: int):
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return JSONResponse({"error": "Property not found"}, status_code=404)
    return detail


@web_router.post("/hotels/{prop_id}/rooms/new")
def rooms_new_submit(
    request: Request,
    prop_id: int,
    name: str = Form(default=""),
    description: str = Form(default=""),
    max_adults: int = Form(default=2),
    max_children: int = Form(default=0),
    base_capacity: int = Form(default=2),
    is_active: str = Form(default="on"),
    view: str = Form(default=""),
    smoking: str = Form(default="off"),
    accessible: str = Form(default="off"),
):
    try:
        saved = create_room_type(
            prop_id,
            name=name,
            description=description,
            max_adults=max_adults,
            max_children=max_children,
            base_capacity=base_capacity,
            is_active=is_active,
            view=view,
            smoking=smoking,
            accessible=accessible,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if saved is None:
        return JSONResponse({"error": "Property not found"}, status_code=404)
    return JSONResponse({"ok": True, "message": "Tipo de habitacion registrado"})


@api_router.get("/rooms")
def rooms_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_rooms(require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/rooms/options")
def rooms_options_api(current_user: dict = Depends(require_permission("rooms.read"))):
    # Lightweight path: only id+name needed; enriched listing cost ~9s at
    # page_size=200 (per-hotel performance/operational aggregates).
    properties = list_property_options("", page=1, page_size=200, user=current_user)
    return {
        "properties": [
            {
                "prop_id": item["prop_id"],
                "display_name": item.get("display_name") or item.get("hotel_name") or f"Hotel {item['prop_id']}",
            }
            for item in properties["items"]
        ]
    }


@api_router.post("/rooms", status_code=201)
def rooms_create_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rooms.manage")),
):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_room_type(
            prop_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            max_adults=payload.get("max_adults"),
            max_children=payload.get("max_children"),
            base_capacity=payload.get("base_capacity"),
            is_active=payload.get("is_active", True),
            room_number=str(payload.get("room_number") or ""),
            floor=str(payload.get("floor") or ""),
            view=str(payload.get("view") or ""),
            smoking=payload.get("smoking", False),
            accessible=payload.get("accessible", False),
            image_url=str(payload.get("image_url") or ""),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.get("/rooms/{room_type_id}")
def rooms_get_api(
    room_type_id: str,
    prop_id: int = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("rooms.read")),
):
    """Get a single room type by ID."""
    from src.app.modules.partner.services.rooms.types import _room_type_by_id
    detail = _room_type_by_id(room_type_id, prop_id=prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return detail


@api_router.put("/rooms/{room_type_id}")
def rooms_update_api(
    room_type_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rooms.update")),
):
    try:
        saved = update_room_type(
            room_type_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            max_adults=payload.get("max_adults"),
            max_children=payload.get("max_children"),
            base_capacity=payload.get("base_capacity"),
            base_rate=payload.get("base_rate"),
            is_active=payload.get("is_active", True),
            room_number=str(payload.get("room_number") or ""),
            floor=str(payload.get("floor") or ""),
            view=str(payload.get("view") or ""),
            smoking=payload.get("smoking", False),
            accessible=payload.get("accessible", False),
            image_url=str(payload.get("image_url") or ""),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return saved


@api_router.post("/rooms/{room_type_id}/rooms", status_code=201)
def rooms_create_hotel_room_api(
    room_type_id: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rooms.manage")),
):
    """Create a hotel_room (physical room) linked to an existing room type."""
    from src.app.modules.partner.services.rooms import create_hotel_room_for_type
    try:
        result = create_hotel_room_for_type(
            room_type_id,
            room_number=str(payload.get("room_number") or ""),
            floor=str(payload.get("floor") or ""),
            view=str(payload.get("view") or ""),
            smoking=payload.get("smoking", False),
            accessible=payload.get("accessible", False),
            is_active=payload.get("is_active", True),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return result


@api_router.post("/rooms/roh", status_code=201)
def rooms_roh_create_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("rooms.manage")),
):
    """Create or get the Run Of House (ROH) room type for a property."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_roh_room_type(
            prop_id,
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.delete("/rooms/{room_type_id}")
@api_router.post("/rooms/{room_type_id}/image", status_code=200)
async def rooms_image_upload_api(
    room_type_id: str,
    file: UploadFile,
    current_user: dict = Depends(require_permission("rooms.update")),
):
    """Upload an image for a room type. Saves to disk and updates the room_type's image_url."""
    from pathlib import Path
    from src.app.modules.partner.services._common import now_utc
    from src.database.connection import get_database

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se permiten archivos de imagen.")

    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"room_{room_type_id}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = Path("/app/data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    image_url = f"/uploads/{filename}"

    # Update only image_url — direct $set to avoid overwriting other fields
    db = get_database()
    result = db.room_types.update_one(
        {"room_type_id": room_type_id},
        {"$set": {"image_url": image_url, "updated_at": now_utc()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")

    return {"image_url": image_url}


def rooms_delete_api(
    room_type_id: str,
    current_user: dict = Depends(require_permission("rooms.manage")),
):
    try:
        saved = delete_room_type(room_type_id, changed_by=current_user.get("username", "system"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return saved
