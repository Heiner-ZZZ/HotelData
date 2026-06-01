from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Body, Form, HTTPException, Query, Request, status as http_status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.app.modules.partner.schemas import ModuleStatus
from src.app.modules.partner.service import (
    add_partner_hotel_image,
    create_blackout_block,
    create_room_type,
    ensure_hotel_content_collections,
    ensure_inventory_collections,
    list_partner_hotels,
    management_property_options,
    module_status,
    partner_hotel_content,
    partner_hotel_content_editor,
    partner_hotel_detail,
    partner_hotel_inventory,
    partner_hotel_images,
    partner_hotel_policies,
    partner_hotel_performance,
    partner_hotel_rooms,
    save_inventory_entry,
    save_partner_hotel_content,
    save_partner_hotel_amenities,
    save_partner_hotel_policies,
)


router = APIRouter(prefix="/modules/partner", tags=["modules-partner"])
web_router = APIRouter(prefix="/partner", tags=["partner"])
api_router = APIRouter(prefix="/api/management", tags=["management-api"])
legacy_admin_api_router = APIRouter(prefix="/api/admin", tags=["admin-legacy-api"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/status", response_model=ModuleStatus)
def partner_status() -> ModuleStatus:
    ensure_hotel_content_collections()
    ensure_inventory_collections()
    return module_status()


def _page_url(request: Request, page: int) -> str:
    params = dict(request.query_params)
    params["page"] = str(page)
    return f"{request.url.path}?{urlencode(params)}"


@web_router.get("/hotels")
def hotels(request: Request, q: str = "", page: int = Query(default=1, ge=1)):
    results = list_partner_hotels(q, page=page, page_size=20)
    return templates.TemplateResponse(
        request,
        "partner/hotels.html",
        {
            "results": results,
            "prev_url": _page_url(request, results["page"] - 1) if results["has_prev"] else None,
            "next_url": _page_url(request, results["page"] + 1) if results["has_next"] else None,
        },
    )


@web_router.get("/hotels/{prop_id}")
def hotel_detail(request: Request, prop_id: int):
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return templates.TemplateResponse(request, "partner/hotel_detail.html", detail)


@web_router.get("/hotels/{prop_id}/performance")
def performance(request: Request, prop_id: int):
    detail = partner_hotel_performance(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return templates.TemplateResponse(request, "partner/performance.html", detail)


@web_router.get("/hotels/{prop_id}/content")
def content(request: Request, prop_id: int):
    detail = partner_hotel_content(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return templates.TemplateResponse(request, "partner/content.html", detail)


@web_router.get("/hotels/{prop_id}/content/edit")
def content_edit(request: Request, prop_id: int):
    detail = partner_hotel_content_editor(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    detail["message"] = request.query_params.get("message")
    detail["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "partner/content_edit.html", detail)


@web_router.post("/hotels/{prop_id}/content/edit")
def content_edit_submit(
    request: Request,
    prop_id: int,
    description: str = Form(default=""),
    highlights: str = Form(default=""),
    amenities_text: str = Form(default=""),
):
    saved = save_partner_hotel_content(
        prop_id,
        description=description,
        highlights=highlights,
        amenities_text=amenities_text,
    )
    if saved is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return RedirectResponse(
        url=f"/partner/hotels/{prop_id}/content/edit?message=Contenido+actualizado",
        status_code=303,
    )


@web_router.get("/hotels/{prop_id}/policies")
def policies(request: Request, prop_id: int):
    detail = partner_hotel_policies(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    detail["message"] = request.query_params.get("message")
    detail["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "partner/policies.html", detail)


@web_router.post("/hotels/{prop_id}/policies")
def policies_submit(
    request: Request,
    prop_id: int,
    check_in_time: str = Form(default=""),
    check_out_time: str = Form(default=""),
    cancellation_policy: str = Form(default=""),
    pet_policy: str = Form(default=""),
    children_policy: str = Form(default=""),
):
    saved = save_partner_hotel_policies(
        prop_id,
        check_in_time=check_in_time,
        check_out_time=check_out_time,
        cancellation_policy=cancellation_policy,
        pet_policy=pet_policy,
        children_policy=children_policy,
    )
    if saved is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return RedirectResponse(
        url=f"/partner/hotels/{prop_id}/policies?message=Politicas+actualizadas",
        status_code=303,
    )


@web_router.get("/hotels/{prop_id}/images")
def images(request: Request, prop_id: int):
    detail = partner_hotel_images(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    detail["message"] = request.query_params.get("message")
    detail["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "partner/images.html", detail)


@web_router.post("/hotels/{prop_id}/images")
def images_submit(
    request: Request,
    prop_id: int,
    image_url: str = Form(default=""),
    title: str = Form(default=""),
):
    try:
        saved = add_partner_hotel_image(prop_id, image_url=image_url, title=title)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/partner/hotels/{prop_id}/images?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    if saved is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return RedirectResponse(
        url=f"/partner/hotels/{prop_id}/images?message=Imagen+registrada",
        status_code=303,
    )


@web_router.get("/hotels/{prop_id}/rooms")
def rooms(request: Request, prop_id: int):
    detail = partner_hotel_rooms(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    detail["message"] = request.query_params.get("message")
    detail["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "partner/rooms.html", detail)


@web_router.get("/hotels/{prop_id}/rooms/new")
def rooms_new(request: Request, prop_id: int):
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    detail["message"] = request.query_params.get("message")
    detail["error"] = request.query_params.get("error")
    detail["form_values"] = {
        "name": "",
        "description": "",
        "max_adults": 2,
        "max_children": 0,
        "base_capacity": 2,
        "is_active": True,
    }
    return templates.TemplateResponse(request, "partner/rooms_new.html", detail)


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
        return RedirectResponse(
            url=f"/partner/hotels/{prop_id}/rooms/new?error={str(exc).replace(' ', '+')}",
            status_code=303,
        )
    if saved is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    return RedirectResponse(
        url=f"/partner/hotels/{prop_id}/rooms?message=Tipo+de+habitacion+registrado",
        status_code=303,
    )


@web_router.get("/hotels/{prop_id}/inventory")
def inventory(request: Request, prop_id: int):
    detail = partner_hotel_inventory(prop_id)
    if detail is None:
        return RedirectResponse(url="/partner/hotels", status_code=303)
    detail["message"] = request.query_params.get("message")
    detail["error"] = request.query_params.get("error")
    return templates.TemplateResponse(request, "partner/inventory.html", detail)


@web_router.post("/hotels/{prop_id}/inventory")
def inventory_submit(
    request: Request,
    prop_id: int,
    room_type_id: str = Form(default=""),
    date: str = Form(default=""),
    total_rooms: int = Form(default=0),
    available_rooms: int = Form(default=0),
    blocked_rooms: int = Form(default=0),
):
    try:
        saved = save_inventory_entry(
            prop_id,
            room_type_id=room_type_id,
            date=date,
            total_rooms=total_rooms,
            available_rooms=available_rooms,
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


def _require_prop_id(prop_id: int | None) -> int:
    if prop_id is None or prop_id <= 0:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="prop_id is required")
    return prop_id


@api_router.get("/properties")
def properties_api(q: str = "", page: int = Query(default=1, ge=1)):
    return list_partner_hotels(q, page=page, page_size=20)


@api_router.get("/properties/{prop_id}")
def property_detail_api(prop_id: int):
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@legacy_admin_api_router.get("/properties")
def legacy_properties_api(q: str = "", page: int = Query(default=1, ge=1)):
    return properties_api(q=q, page=page)


@legacy_admin_api_router.get("/properties/{prop_id}")
def legacy_property_detail_api(prop_id: int):
    return property_detail_api(prop_id)


@api_router.get("/rooms")
def rooms_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_rooms(_require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/rooms/options")
def rooms_options_api():
    properties = list_partner_hotels("", page=1, page_size=100)
    return {
        "properties": [
            {
                "prop_id": item["prop_id"],
                "display_name": item.get("display_name") or item.get("hotel_name") or f"Hotel {item['prop_id']}",
            }
            for item in properties["items"]
        ]
    }


@api_router.post("/rooms", status_code=http_status.HTTP_201_CREATED)
def rooms_create_api(payload: dict = Body(...)):
    prop_id = _require_prop_id(int(payload.get("prop_id") or 0))
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
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.get("/availability")
def availability_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_inventory(_require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/availability/options")
def availability_options_api(prop_id: int | None = Query(default=None, ge=1)):
    response: dict[str, object] = {
        "properties": management_property_options()
    }
    if prop_id:
        rooms_detail = partner_hotel_rooms(_require_prop_id(prop_id))
        if rooms_detail is None:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
        response["room_types"] = rooms_detail.get("room_types", [])
    return response


def _availability_update(payload: dict):
    prop_id = _require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = save_inventory_entry(
            prop_id,
            room_type_id=str(payload.get("room_type_id") or ""),
            date=str(payload.get("date") or ""),
            total_rooms=payload.get("total_rooms"),
            available_rooms=payload.get("available_rooms"),
            blocked_rooms=payload.get("blocked_rooms"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/availability")
def availability_update_api(payload: dict = Body(...)):
    return _availability_update(payload)


@api_router.patch("/availability")
def availability_patch_api(payload: dict = Body(...)):
    return _availability_update(payload)


@api_router.post("/availability/blackouts")
def availability_blackout_api(payload: dict = Body(...)):
    prop_id = _require_prop_id(int(payload.get("prop_id") or 0))
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
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.get("/policies")
def policies_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_policies(_require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/policies/options")
def policies_options_api():
    return {"properties": management_property_options()}


@api_router.put("/policies")
def policies_update_api(payload: dict = Body(...)):
    prop_id = _require_prop_id(int(payload.get("prop_id") or 0))
    saved = save_partner_hotel_policies(
        prop_id,
        check_in_time=str(payload.get("check_in_time") or ""),
        check_out_time=str(payload.get("check_out_time") or ""),
        cancellation_policy=str(payload.get("cancellation_policy") or ""),
        pet_policy=str(payload.get("pet_policy") or ""),
        children_policy=str(payload.get("children_policy") or ""),
        extra_bed_policy=str(payload.get("extra_bed_policy") or ""),
        payment_policy=str(payload.get("payment_policy") or ""),
        house_rules=str(payload.get("house_rules") or ""),
        changed_by="angular_api",
    )
    if saved is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.get("/amenities")
def amenities_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_content(_require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/amenities/options")
def amenities_options_api(prop_id: int | None = Query(default=None, ge=1)):
    response: dict[str, object] = {"properties": management_property_options()}
    if prop_id:
        detail = partner_hotel_content(_require_prop_id(prop_id))
        if detail is None:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
        response["catalog"] = detail.get("amenities", {}).get("catalog", [])
        response["active_amenities"] = detail.get("amenities", {}).get("active_amenities", [])
    return response


@api_router.put("/amenities")
def amenities_update_api(payload: dict = Body(...)):
    prop_id = _require_prop_id(int(payload.get("prop_id") or 0))
    active_amenities = payload.get("active_amenities") or []
    if not isinstance(active_amenities, list):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="active_amenities must be a list")
    saved = save_partner_hotel_amenities(
        prop_id,
        active_amenities=[str(item) for item in active_amenities],
        amenities_text=str(payload.get("amenities_text") or ""),
        changed_by="angular_api",
    )
    if saved is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved
