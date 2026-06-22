from __future__ import annotations

from fastapi import Body, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from src.app.modules.partner.routes import api_router, legacy_admin_api_router, templates, web_router
from src.app.modules.partner.routes._common import page_url, require_prop_id
from src.app.modules.partner.services import (
    list_partner_hotels,
    management_property_options,
    partner_hotel_detail,
    partner_hotel_edit_profile,
    partner_hotel_performance,
    partner_hotel_profile,
    properties_dashboard,
    save_partner_hotel_profile,
)


@web_router.get("/hotels")
def hotels(request: Request, q: str = "", page: int = Query(default=1, ge=1)):
    results = list_partner_hotels(q, page=page, page_size=20)
    return templates.TemplateResponse(
        request,
        "partner/hotels.html",
        {
            "results": results,
            "prev_url": page_url(request, results["page"] - 1) if results["has_prev"] else None,
            "next_url": page_url(request, results["page"] + 1) if results["has_next"] else None,
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


@api_router.get("/properties")
def properties_api(q: str = "", page: int = Query(default=1, ge=1)):
    return list_partner_hotels(q, page=page, page_size=20)


@api_router.get("/properties/options")
def properties_options_api(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    results = list_partner_hotels(q, page=page, page_size=page_size)
    return {
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


@api_router.get("/properties/dashboard")
def properties_dashboard_api(q: str = "", page: int = Query(default=1, ge=1)):
    return properties_dashboard(q, page=page, page_size=20)


@api_router.get("/properties/{prop_id}/edit")
def property_edit_api(prop_id: int):
    detail = partner_hotel_edit_profile(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/properties/{prop_id}/profile")
def property_profile_api(prop_id: int):
    detail = partner_hotel_profile(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.put("/properties/{prop_id}/profile")
def property_profile_update_api(prop_id: int, payload: dict = Body(...)):
    saved = save_partner_hotel_profile(
        prop_id,
        hotel_name=str(payload.get("hotel_name") or ""),
        display_name=str(payload.get("display_name") or ""),
        description=str(payload.get("description") or ""),
        display_country_label=str(payload.get("display_country_label") or ""),
        changed_by=str(payload.get("changed_by") or "angular_api"),
        reason=str(payload.get("reason") or "Actualización manual de perfil hotelero"),
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.get("/properties/{prop_id}")
def property_detail_api(prop_id: int):
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@legacy_admin_api_router.get("/properties")
def legacy_properties_api(q: str = "", page: int = Query(default=1, ge=1)):
    return properties_api(q=q, page=page)


@legacy_admin_api_router.get("/properties/{prop_id}")
def legacy_property_detail_api(prop_id: int):
    return property_detail_api(prop_id)
