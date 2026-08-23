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
    soft_delete_inventory_entry,
)
from src.app.modules.partner.services.rooms.queries import hotel_rooms_by_type
from src.app.modules.partner.services.rooms.availability import update_blackout_block
from src.app.modules.partner.services.audit import register_action
from src.app.security.dependencies import require_permission, require_prop_permission


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
    user = getattr(request.state, "current_user", None) or {}
    changed_by = user.get("username", "system")
    try:
        saved = save_inventory_entry(
            prop_id,
            room_type_id=room_type_id,
            date=date,
            total_rooms=total_rooms,
            available_rooms=available_rooms,
            blocked_rooms=blocked_rooms,
            expected_version=version or None,
            changed_by=changed_by,
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
    user = getattr(request.state, "current_user", None) or {}
    changed_by = user.get("username", "system")
    try:
        saved = create_blackout_block(
            prop_id,
            room_type_id=room_type_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            blocked_rooms=blocked_rooms,
            changed_by=changed_by,
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


def _check_body_prop_id(query_prop_id: int | None, payload: dict) -> None:
    """Consistencia gate(query) ↔ body: el prop_id del query es autoritativo."""
    try:
        body_prop_id = int(str(payload.get("prop_id") or 0))
    except (TypeError, ValueError):
        body_prop_id = 0
    if query_prop_id is not None and body_prop_id != query_prop_id:
        raise HTTPException(status_code=400, detail="prop_id del query y del body no coinciden")


@api_router.get("/availability")
def availability_api(
    request: Request,
    prop_id: int = Query(..., ge=1),
    days: int = Query(default=90, ge=1, le=365),
    start_date: str = Query(default=""),
    end_date: str = Query(default=""),
    current_user: dict = Depends(require_prop_permission("inventory.read")),
):
    detail = partner_hotel_inventory(require_prop_id(prop_id), days=days, start_date=start_date, end_date=end_date)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    user = current_user or getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id,
        entity_type="availability",
        entity_id=f"prop_{prop_id}",
        action="read",
        summary=f"Consulta de disponibilidad para prop_id={prop_id} (días={days})",
        changed_by=user.get("username", "anonymous"),
        metadata={"days": days, "start_date": start_date, "end_date": end_date, "url": str(request.url)},
    )
    return detail


@api_router.get("/availability/options")
def availability_options_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_permission("inventory.read")),
):
    """Vista MULTI-HOTEL del picker de Disponibilidad (excepción global
    documentada): sin prop_id lista los hoteles accesibles del usuario, no
    opera un hotel concreto. Con prop_id añade los room types del hotel."""
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
    audit_prop_id = prop_id if prop_id else (response["properties"][0]["prop_id"] if response["properties"] else 0)
    register_action(
        prop_id=audit_prop_id,
        entity_type="availability_options",
        entity_id=f"page_{page}",
        action="read",
        summary=f"Consulta de opciones de disponibilidad (q={q}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"q": q, "page": page, "page_size": page_size, "prop_id": prop_id, "url": str(request.url)},
    )
    return response


def _availability_update(payload: dict, changed_by: str = "system"):
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
            changed_by=changed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/availability")
def availability_update_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("inventory.manage")),
):
    _check_body_prop_id(query_prop_id, payload)
    return _availability_update(payload, changed_by=current_user.get("username", "system"))


@api_router.patch("/availability")
def availability_patch_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("inventory.manage")),
):
    """Partial update of inventory (used by Angular frontend)."""
    _check_body_prop_id(query_prop_id, payload)
    return _availability_update(payload, changed_by=current_user.get("username", "system"))


@api_router.get("/availability/blackouts")
def availability_blackouts_list_api(
    request: Request,
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_prop_permission("inventory.read")),
):
    """List all blackout blocks for a property."""
    items = list_property_blackouts(require_prop_id(prop_id))
    user = current_user or getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id,
        entity_type="blackout_block",
        entity_id=f"prop_{prop_id}",
        action="read",
        summary=f"Listado de bloqueos para prop_id={prop_id}",
        changed_by=user.get("username", "anonymous"),
        metadata={"count": len(items), "url": str(request.url)},
    )
    return {"items": items, "total": len(items)}


@api_router.get("/availability/hotel-rooms")
def availability_hotel_rooms_api(
    request: Request,
    prop_id: int = Query(..., ge=1),
    room_type_id: str = Query(...),
    current_user: dict = Depends(require_prop_permission("inventory.read")),
):
    """Return individual hotel rooms for a given room type (used by multi-select in frontend)."""
    items = hotel_rooms_by_type(require_prop_id(prop_id), room_type_id)
    user = current_user or getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id,
        entity_type="hotel_room",
        entity_id=f"{room_type_id}",
        action="read",
        summary=f"Consulta de habitaciones para room_type_id={room_type_id}",
        changed_by=user.get("username", "anonymous"),
        metadata={"room_type_id": room_type_id, "count": len(items), "url": str(request.url)},
    )
    return {"items": items, "total": len(items)}


@api_router.post("/availability/blackouts")
def availability_blackout_api(
    request: Request,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("inventory.manage")),
):
    _check_body_prop_id(query_prop_id, payload)
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    # Accept room_numbers array or blocked_rooms count
    room_numbers = payload.get("room_numbers")
    if room_numbers is not None and isinstance(room_numbers, list) and len(room_numbers) > 0:
        blocked_rooms = len(room_numbers)
    else:
        blocked_rooms = payload.get("blocked_rooms")
    user = current_user or getattr(request.state, "current_user", None) or {}
    changed_by = user.get("username", "system")
    try:
        saved = create_blackout_block(
            prop_id,
            room_type_id=str(payload.get("room_type_id") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            reason=str(payload.get("reason") or ""),
            blocked_rooms=blocked_rooms,
            changed_by=changed_by,
        )
        # Store room_numbers in the blackout record for future editing
        if saved and room_numbers:
            from src.database.connection import get_database as _get_db
            _get_db().blackout_dates.update_one(
                {"prop_id": prop_id, "room_type_id": saved.get("room_type_id"),
                 "start_date": saved.get("start_date"), "end_date": saved.get("end_date")},
                {"$set": {"room_numbers": room_numbers}},
            )
            saved["room_numbers"] = room_numbers
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.put("/availability/blackouts/{blackout_id}")
def availability_blackout_update_api(
    request: Request,
    blackout_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("inventory.manage")),
):
    """Update a future blackout block (dates, reason, room numbers)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from src.database.connection import get_database

    db = get_database()
    try:
        before = db.blackout_dates.find_one({"_id": ObjectId(blackout_id)}, {"prop_id": 1})
    except InvalidId:
        before = None
    # E 2026-08 cross-hotel: el bloqueo debe pertenecer al hotel pedido (404).
    if before is None or before.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bloqueo no encontrado")

    user = current_user or getattr(request.state, "current_user", None) or {}
    changed_by = user.get("username", "system")
    try:
        room_numbers = payload.get("room_numbers")
        blocked_rooms = len(room_numbers) if (room_numbers and isinstance(room_numbers, list)) else payload.get("blocked_rooms")
        saved = update_blackout_block(
            blackout_id,
            start_date=str(payload.get("start_date")) if payload.get("start_date") else None,
            end_date=str(payload.get("end_date")) if payload.get("end_date") else None,
            reason=str(payload.get("reason")) if payload.get("reason") else None,
            blocked_rooms=blocked_rooms,
            room_numbers=room_numbers if (room_numbers and isinstance(room_numbers, list)) else None,
            changed_by=changed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blackout not found")
    return saved


@api_router.delete("/availability/inventory")
def availability_inventory_delete_api(
    prop_id: int = Query(..., ge=1),
    room_type_id: str = Query(...),
    date: str = Query(...),
    current_user: dict = Depends(require_prop_permission("inventory.manage")),
):
    """Soft-delete an inventory entry."""
    try:
        result = soft_delete_inventory_entry(prop_id, room_type_id=room_type_id, date=date, changed_by=current_user.get("username", "system"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory entry not found")
    return result


@api_router.delete("/availability/blackouts/{blackout_id}")
def availability_blackout_delete_api(
    request: Request,
    blackout_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("inventory.manage")),
):
    """Delete a blackout block and reverse its effect on inventory."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from src.database.connection import get_database

    db = get_database()
    try:
        before = db.blackout_dates.find_one({"_id": ObjectId(blackout_id)}, {"prop_id": 1})
    except InvalidId:
        before = None
    # E 2026-08 cross-hotel: el bloqueo debe pertenecer al hotel pedido (404).
    if before is None or before.get("prop_id") != query_prop_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bloqueo no encontrado")

    user = current_user or getattr(request.state, "current_user", None) or {}
    changed_by = user.get("username", "system")
    try:
        result = delete_blackout_block(blackout_id, changed_by=changed_by)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blackout not found")
    return result
