from __future__ import annotations

from fastapi import Body, Form, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from fastapi import Depends

from src.app.modules.partner.routes import api_router, web_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_room_type,
    list_partner_hotels,
    partner_hotel_detail,
    partner_hotel_rooms,
    update_room_type,
)
from src.app.security.dependencies import require_login


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
def rooms_options_api(current_user: dict = Depends(require_login)):
    properties = list_partner_hotels("", page=1, page_size=200, user=current_user)
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
def rooms_create_api(payload: dict = Body(...)):
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.put("/rooms/{room_type_id}")
def rooms_update_api(room_type_id: str, payload: dict = Body(...)):
    try:
        saved = update_room_type(
            room_type_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            max_adults=payload.get("max_adults"),
            max_children=payload.get("max_children"),
            base_capacity=payload.get("base_capacity"),
            is_active=payload.get("is_active", True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return saved
