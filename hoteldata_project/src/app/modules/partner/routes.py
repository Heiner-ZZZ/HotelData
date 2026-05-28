from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request
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
    save_partner_hotel_policies,
)


router = APIRouter(prefix="/modules/partner", tags=["modules-partner"])
web_router = APIRouter(prefix="/partner", tags=["partner"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/status", response_model=ModuleStatus)
def status() -> ModuleStatus:
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
