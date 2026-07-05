from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import Body, Depends, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse

from src.app.modules.partner.routes import api_router, web_router
from src.app.modules.partner.services import (
    add_partner_hotel_image,
    delete_partner_hotel_image,
    partner_hotel_content,
    partner_hotel_content_editor,
    partner_hotel_detail,
    partner_hotel_images,
    reorder_partner_hotel_images,
    save_partner_hotel_content,
)
from src.app.security.dependencies import require_login


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
def property_content_update_api(prop_id: int, payload: dict = Body(...), current_user: dict = Depends(require_login)):
    saved = save_partner_hotel_content(
        prop_id,
        description=str(payload.get("description") or ""),
        highlights=str(payload.get("highlights") or ""),
        amenities_text=str(payload.get("amenities_text") or ""),
        changed_by=current_user.get("username", "angular_api"),
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/properties/{prop_id}/images")
def property_image_add_api(prop_id: int, payload: dict = Body(...), current_user: dict = Depends(require_login)):
    image_url = str(payload.get("image_url") or "")
    title = str(payload.get("title") or "")
    try:
        saved = add_partner_hotel_image(prop_id, image_url=image_url, title=title, changed_by=current_user.get("username", "angular_api"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.post("/properties/{prop_id}/images/upload")
async def property_image_upload_api(prop_id: int, file: UploadFile, current_user: dict = Depends(require_login)):
    """Upload an image file and store it for a property."""
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se permiten archivos de imagen.")

    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"prop_{prop_id}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = Path("/app/data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    image_url = f"/uploads/{filename}"
    title = Path(file.filename or "image").stem.replace("-", " ").replace("_", " ").title()

    saved = add_partner_hotel_image(prop_id, image_url=image_url, title=title, changed_by=current_user.get("username", "angular_api"))
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.delete("/properties/{prop_id}/images")
def property_image_delete_api(prop_id: int, image_url: str = Query(...), current_user: dict = Depends(require_login)):
    deleted = delete_partner_hotel_image(prop_id, image_url=image_url, changed_by=current_user.get("username", "angular_api"))
    return {"deleted": deleted}


@api_router.put("/properties/{prop_id}/images/reorder")
def property_image_reorder_api(prop_id: int, payload: dict = Body(...), current_user: dict = Depends(require_login)):
    """RF-004: Reorder images. First image becomes primary (portada)."""
    image_order = payload.get("image_order")
    if not isinstance(image_order, list) or not image_order:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_order must be a non-empty list of image URLs.")
    try:
        result =        reorder_partner_hotel_images(
            prop_id,
            image_order=[str(url) for url in image_order],
            changed_by=current_user.get("username", "angular_api"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"images": result, "primary_image": result[0]["image_url"] if result else None}
