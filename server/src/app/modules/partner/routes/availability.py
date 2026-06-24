from __future__ import annotations

from fastapi import Body, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from fastapi import Depends

from src.app.modules.partner.routes import api_router, web_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_blackout_block,
    delete_blackout_block,
    list_partner_hotels,
    list_property_blackouts,
    partner_hotel_inventory,
    partner_hotel_rooms,
    save_inventory_entry,
)
from src.app.security.dependencies import require_login


@web_router.post("/hotels/{prop_id}/inventory")
def inventory_submit(
    request: Request,
    prop_id: int,
    room_type_id: str = Form(default=""),
    date: str = Form(default=""),
    total_rooms: int = Form(default=0),
    available_rooms: int = Form(default=0),
    blocked_rooms: int = Form(default=0),
    version: int = Form(default=0),
):
    try:
        saved = save_inventory_entry(
            prop_id,
            room_type_id=room_type_id,
            date=date,
            total_rooms=total_rooms,
            available_rooms=available_rooms,
            blocked_rooms=blocked_rooms,
            expected_version=version or None,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/partner/hotels/{prop_id}/inventory?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    if saved is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return RedirectResponse(
        url=f"/partner/hotels/{prop_id}/inventory?message=Inventario+actualizado",
        status_code=303,
    )


@web_router.post("/hotels/{prop_id}/blackout-dates")
def blackout_dates_submit(
    request: Request,
    prop_id: int,
    room_type_id: str = Form(default=""),
    start_date: str = Form(default=""),
    end_date: str = Form(default=""),
    reason: str = Form(default=""),
    blocked_rooms: int = Form(default=0),
):
    try:
        saved = create_blackout_block(
            prop_id,
            room_type_id=room_type_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            blocked_rooms=blocked_rooms,
        )
    except ValueError as exc:
        return RedirectResponse(
            url=f"/partner/hotels/{prop_id}/inventory?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    if saved is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return RedirectResponse(
        url=f"/partner/hotels/{prop_id}/inventory?message=Bloqueo+registrado",
        status_code=303,
    )


@api_router.get("/availability")
def availability_api(
    prop_id: int = Query(..., ge=1),
    days: int = Query(default=90, ge=1, le=365),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
):
    detail = partner_hotel_inventory(require_prop_id(prop_id), days=days, start_date=start_date, end_date=end_date)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/availability/options")
def availability_options_api(
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    results = list_partner_hotels(q, page=page, page_size=page_size, user=current_user)
    response: dict[str, object] = {
        "properties": [
            {
                "prop_id": item["prop_id"],
                "display_name": item.get("display_name") or f"Hotel {item['prop_id']}",
            }
            for item in results["items"]
        ],
        "total": results["total"],
        "page": results["page"],
        "page_size": results["page_size"],
        "has_next": results["has_next"],
    }
    if prop_id:
        rooms_detail = partner_hotel_rooms(require_prop_id(prop_id))
        if rooms_detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        response["room_types"] = rooms_detail.get("room_types", [])
    return response


def _availability_update(payload: dict):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = save_inventory_entry(
            prop_id,
            room_type_id=str(payload.get("room_type_id") or ""),
            date=str(payload.get("date") or ""),
            total_rooms=payload.get("total_rooms"),
            available_rooms=payload.get("available_rooms"),
            blocked_rooms=payload.get("blocked_rooms"),
            expected_version=payload.get("version") or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/availability")
def availability_update_api(payload: dict = Body(...)):
    return _availability_update(payload)


@api_router.patch("/availability")
def availability_patch_api(payload: dict = Body(...)):
    """Partial update of inventory (used by Angular frontend)."""
    return _availability_update(payload)


@api_router.get("/availability/blackouts")
def availability_blackouts_list_api(
    prop_id: int = Query(..., ge=1),
):
    """List all blackout blocks for a property."""
    items = list_property_blackouts(require_prop_id(prop_id))
    return {"items": items, "total": len(items)}


@api_router.post("/availability/blackouts")
def availability_blackout_api(payload: dict = Body(...)):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_blackout_block(
            prop_id,
            room_type_id=str(payload.get("room_type_id") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            reason=str(payload.get("reason") or ""),
            blocked_rooms=payload.get("blocked_rooms"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.delete("/availability/blackouts/{blackout_id}")
def availability_blackout_delete_api(blackout_id: str):
    """Delete a blackout block and reverse its effect on inventory."""
    try:
        result = delete_blackout_block(blackout_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blackout not found")
    return result
