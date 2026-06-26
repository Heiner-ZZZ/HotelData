from __future__ import annotations

from fastapi import Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from src.app.modules.partner.routes import api_router, legacy_admin_api_router, web_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    list_hotel_changes,
    get_change_detail,
    list_partner_hotels,
    partner_hotel_detail,
    partner_hotel_edit_profile,
    partner_hotel_performance,
    partner_hotel_profile,
    properties_dashboard,
    save_partner_hotel_profile,
)
from src.app.security.dependencies import require_login


@web_router.get("/hotels")
def hotels(request: Request, q: str = "", page: int = Query(default=1, ge=1)):
    results = list_partner_hotels(q, page=page, page_size=20)
    return results


@web_router.get("/hotels/{prop_id}")
def hotel_detail(request: Request, prop_id: int):
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return JSONResponse({"error": "Property not found"}, status_code=404)
    return detail


@web_router.get("/hotels/{prop_id}/performance")
def performance(request: Request, prop_id: int):
    detail = partner_hotel_performance(prop_id)
    if detail is None:
        return JSONResponse({"error": "Property not found"}, status_code=404)
    return detail


@api_router.get("/properties")
def properties_api(q: str = "", page: int = Query(default=1, ge=1), current_user: dict = Depends(require_login)):
    return list_partner_hotels(q, page=page, page_size=10, user=current_user)


@api_router.get("/properties/options")
def properties_options_api(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    results = list_partner_hotels(q, page=page, page_size=page_size, user=current_user)
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
def properties_dashboard_api(q: str = "", page: int = Query(default=1, ge=1), current_user: dict = Depends(require_login)):
    return properties_dashboard(q, page=page, page_size=10, user=current_user)


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
def property_detail_api(prop_id: int, current_user: dict = Depends(require_login)):
    detail = partner_hotel_detail(prop_id, user=current_user)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/properties/{prop_id}/history")
def property_history_api(
    prop_id: int,
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    field: str | None = Query(default=None),
    user: str | None = Query(default=None),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    current_user: dict = Depends(require_login),
):
    return list_hotel_changes(
        prop_id,
        from_date=from_date,
        to_date=to_date,
        field=field,
        user=user,
        source=source,
        page=page,
        per_page=per_page,
    )


@api_router.get("/properties/{prop_id}/history/{change_id}")
def property_history_detail_api(
    prop_id: int,
    change_id: str,
    current_user: dict = Depends(require_login),
):
    detail = get_change_detail(prop_id, change_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change record not found")
    return detail


@legacy_admin_api_router.get("/properties")
def legacy_properties_api(q: str = "", page: int = Query(default=1, ge=1)):
    return properties_api(q=q, page=page)


@legacy_admin_api_router.get("/properties/{prop_id}")
def legacy_property_detail_api(prop_id: int):
    return property_detail_api(prop_id)
