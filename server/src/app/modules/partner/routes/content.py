from __future__ import annotations

from fastapi import Body, Form, Query, Request
from fastapi.responses import RedirectResponse

from src.app.modules.partner.routes import api_router, templates, web_router
from src.app.modules.partner.services import (
    add_partner_hotel_image,
    delete_partner_hotel_image,
    partner_hotel_content,
    partner_hotel_content_editor,
    partner_hotel_images,
    save_partner_hotel_content,
)


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


@api_router.put("/properties/{prop_id}/content")
def property_content_update_api(prop_id: int, payload: dict = Body(...)):
    saved = save_partner_hotel_content(
        prop_id,
        description=str(payload.get("description") or ""),
        highlights=str(payload.get("highlights") or ""),
        amenities_text=str(payload.get("amenities_text") or ""),
        changed_by="angular_api",
    )
    if saved is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/properties/{prop_id}/images")
def property_image_add_api(prop_id: int, payload: dict = Body(...)):
    image_url = str(payload.get("image_url") or "")
    title = str(payload.get("title") or "")
    try:
        saved = add_partner_hotel_image(prop_id, image_url=image_url, title=title, changed_by="angular_api")
    except ValueError as exc:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.delete("/properties/{prop_id}/images")
def property_image_delete_api(prop_id: int, image_url: str = Query(...)):
    deleted = delete_partner_hotel_image(prop_id, image_url=image_url, changed_by="angular_api")
    return {"deleted": deleted}
