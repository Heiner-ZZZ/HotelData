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


@api_router.get("/properties/context")
def properties_context_api(
    current_user: dict = Depends(require_login),
):
    """Return the property context for the current user.

    Determines the access mode:
    - "all": super_admin, admin_sistema — can browse all hotels
    - "single": user has exactly 1 assigned hotel → auto-select
    - "multi": user has 2+ assigned hotels → show limited selector
    """
    from src.app.security.hotel_filter import assigned_hotels_for_user, UNFILTERED_ROLES
    from src.app.modules.partner.services.properties.listing import list_partner_hotels

    role = (current_user or {}).get("primary_role", "")

    # Roles sin restricción (super_admin, admin_sistema, cliente)
    if role in UNFILTERED_ROLES:
        return {"mode": "all", "assigned_properties": [], "default_prop_id": 0}

    assigned = assigned_hotels_for_user(current_user)

    if not assigned:
        # Tiene rol restringido pero sin assigned_hotels → no puede ver nada
        return {"mode": "none", "assigned_properties": [], "default_prop_id": 0}

    # Obtener nombres de los hoteles asignados
    results = list_partner_hotels("", page=1, page_size=200, user=current_user)
    properties = []
    for item in results.get("items", []):
        prop_id = item.get("prop_id")
        if prop_id and prop_id in assigned:
            properties.append({
                "prop_id": prop_id,
                "label": item.get("display_name") or item.get("hotel_name") or f"Hotel {prop_id}",
            })

    # Ordenar por prop_id para consistencia
    properties.sort(key=lambda p: p["prop_id"])

    if len(assigned) == 1:
        return {
            "mode": "single",
            "assigned_properties": properties,
            "default_prop_id": properties[0]["prop_id"] if properties else assigned[0],
        }

    return {
        "mode": "multi",
        "assigned_properties": properties,
        "default_prop_id": 0,
    }


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
def property_profile_update_api(
    prop_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    saved = save_partner_hotel_profile(
        prop_id,
        hotel_name=str(payload.get("hotel_name") or ""),
        display_name=str(payload.get("display_name") or ""),
        description=str(payload.get("description") or ""),
        display_country_label=str(payload.get("display_country_label") or ""),
        changed_by=str(payload.get("changed_by") or current_user.get("username", "system")),
        reason=str(payload.get("reason") or "Actualización manual de perfil hotelero"),
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


@api_router.get("/properties/{prop_id}/operational-calendar")
def property_operational_calendar_api(
    prop_id: int,
    year: int = Query(default=None),
    month: int = Query(default=None),
    current_user: dict = Depends(require_login),
):
    from src.app.modules.partner.services.properties.operational_calendar import operational_calendar as _oc
    from datetime import date as dt_date
    y = year or dt_date.today().year
    m = month or dt_date.today().month
    return _oc(prop_id, y, m)


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
