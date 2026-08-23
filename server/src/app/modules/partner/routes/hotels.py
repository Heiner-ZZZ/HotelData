from __future__ import annotations

from datetime import datetime

from fastapi import Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr
from src.app.modules.partner.routes import (
    api_router,
    legacy_admin_api_router,
    web_router,
)
from src.app.modules.partner.services import (
    get_change_detail,
    list_hotel_changes,
    list_partner_hotels,
    list_property_options,
    partner_hotel_detail,
    partner_hotel_edit_profile,
    partner_hotel_performance,
    partner_hotel_profile,
    properties_dashboard,
    save_partner_hotel_profile,
)
from src.app.security.dependencies import (
    require_login,
    require_permission,
    require_prop_permission,
)
from src.app.security.role_helpers import UNFILTERED_ROLES, get_role_name

# ─── History: PropertyHistoryListResponse envelope ──────────────────


class ChangeRecordResponse(BaseModel):
    """Single change record (list item). Mirrors
    ``compute/list_hotel_changes()`` + Pydantic owns wire shape.

    - ``_id`` from Mongo is mapped to JSON ``id`` via
      ``ObjectIdStr`` + alias pair (FastAPI's jsonable_encoder uses
      by_alias=True by default, so we set ``serialization_alias``).
    - ``changed_at`` accepts datetime OR None and serializes to ISO 8601
      automatically. Legacy rows that lack ``changed_at`` become ``null``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    field: str = ""
    old_value: str = ""
    new_value: str = ""
    changed_by: str = ""
    changed_at: datetime | None = None
    source: str = ""
    reason: str = ""


class PaginationResponse(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    has_prev: bool
    has_next: bool


class FilterOptionsResponse(BaseModel):
    fields: list[str]
    users: list[str]


class PropertyHistoryListResponse(BaseModel):
    data: list[ChangeRecordResponse]
    pagination: PaginationResponse
    filters: FilterOptionsResponse


class ChangeDetailResponse(BaseModel):
    """Single change record (full detail). Superset of
    ``ChangeRecordResponse`` + ``prop_id`` + ``entity_type``.

    ``prop_id`` is Optional because content_changes documents don't
    carry ``prop_id`` directly (filtered via ``entity_type`` instead),
    but the lookup key is ``prop_id`` so we can echo it back.
    ``entity_type`` discriminates "profile" vs "content" for frontend
    rendering.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: ObjectIdStr = Field(validation_alias="_id", serialization_alias="id")
    prop_id: int | None = None
    field: str = ""
    old_value: str = ""
    new_value: str = ""
    changed_by: str = ""
    changed_at: datetime | None = None
    source: str = ""
    reason: str = ""
    entity_type: str = "profile"


# Rebuild Pydantic v2 models to resolve string-lazy annotations from
# ``from __future__ import annotations``. Without this explicit rebuild,
# FastAPI's ``TypeAdapter`` binding at ``response_model=…`` raises
# ``pydantic.errors.PydanticUserError`` on the first request, and any
# nested ``ObjectIdStr`` field surfaces as ``PydanticUndefinedAnnotation``
# when the eager rebuild graph walk hits it (transitively via
# ``PropertyHistoryListResponse.data: list[ChangeRecordResponse]``).
ChangeRecordResponse.model_rebuild()
PaginationResponse.model_rebuild()
FilterOptionsResponse.model_rebuild()
PropertyHistoryListResponse.model_rebuild()
ChangeDetailResponse.model_rebuild()


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
def properties_api(q: str = "", page: int = Query(default=1, ge=1), current_user: dict = Depends(require_permission("properties.read"))):
    return list_partner_hotels(q, page=page, page_size=10, user=current_user)


@api_router.get("/properties/context")
def properties_context_api(
    current_user: dict = Depends(require_login),
):
    """Return the property context for the current user.

    Opción 2 (2026-08): selector de scope → login-only. El modo y el alcance
    salen de ``assigned_hotels`` (deny-by-default por rol restringido), NO de
    códigos globales: sin ``properties.read``/``reservations.read`` globales
    el usuario con hoteles asignados debe poder arrancar la app.
    """
    from src.app.modules.partner.services.properties.listing import (
        list_property_options,
    )
    from src.app.security.hotel_filter import assigned_hotels_for_user

    role = get_role_name(current_user or {})

    # Roles sin restricción (super_admin, admin_sistema, cliente)
    if role in UNFILTERED_ROLES:
        return {"mode": "all", "assigned_properties": [], "default_prop_id": 0}

    assigned = assigned_hotels_for_user(current_user)

    # Escudo defensivo: si por algún camino el scope resultara None (sin
    # restricción), NO clasificarlo como "none" — solo [] (rol restringido
    # sin hoteles) significa "no puede ver nada".
    if assigned is None:
        return {"mode": "all", "assigned_properties": [], "default_prop_id": 0}

    if not assigned:
        # Tiene rol restringido pero sin assigned_hotels → no puede ver nada
        return {"mode": "none", "assigned_properties": [], "default_prop_id": 0}

    # Obtener nombres de los hoteles asignados — path ligero: solo id+label,
    # sin los aggregates de performance/operational por hotel (page_size=200
    # enriquecido costaba ~9s en el montaje de cada página).
    results = list_property_options("", page=1, page_size=200, user=current_user)
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
    """Lightweight selector de propiedades: login-only, scope por asignación.

    Opción 2 (2026-08): mismo contrato que ``/properties/context`` — el picker
    lista SOLO los hoteles asignados del usuario; sin códigos globales.
    """
    # Lightweight path: the selector only needs id+name; the enriched
    # listing runs per-hotel aggregates (performance/operational) that
    # cost seconds at page_size>=10.
    results = list_property_options(q, page=page, page_size=page_size, user=current_user)
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
def properties_dashboard_api(q: str = "", page: int = Query(default=1, ge=1), current_user: dict = Depends(require_permission("dashboard.read"))):
    return properties_dashboard(q, page=page, page_size=10, user=current_user)


@api_router.get("/properties/{prop_id}/edit")
def property_edit_api(prop_id: int, current_user: dict = Depends(require_prop_permission("properties.read"))):
    detail = partner_hotel_edit_profile(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/properties/{prop_id}/profile")
def property_profile_api(prop_id: int, current_user: dict = Depends(require_prop_permission("properties.read"))):
    detail = partner_hotel_profile(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.put("/properties/{prop_id}/profile")
def property_profile_update_api(
    prop_id: int,
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("properties.update")),
):
    saved = save_partner_hotel_profile(
        prop_id,
        hotel_name=str(payload.get("hotel_name") or ""),
        display_name=str(payload.get("display_name") or ""),
        description=str(payload.get("description") or ""),
        display_country_label=str(payload.get("display_country_label") or ""),
        currency=str(payload.get("currency") or ""),
        accepted_currencies=payload.get("accepted_currencies") or None,
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
    current_user: dict = Depends(require_prop_permission("properties.read")),
):
    from src.app.core.timezone import local_now
    from src.app.modules.partner.services.properties.operational_calendar import (
        operational_calendar as _oc,
    )
    now_local = local_now()
    y = year or now_local.year
    m = month or now_local.month
    return _oc(prop_id, y, m)


@api_router.get("/properties/{prop_id}")
def property_detail_api(prop_id: int, current_user: dict = Depends(require_prop_permission("properties.read"))):
    detail = partner_hotel_detail(prop_id, user=current_user)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


# ── History (vista de auditoría — excepción global documentada) ──
# ``audit.read`` es un código SYSTEM-SCOPE (los roles de hotel no lo portan
# por diseño): el historial de cambios del perfil es vista de PLATAFORMA, no
# operación del hotel. Se mantiene GLOBAL (require_permission) a propósito.


@api_router.get(
    "/properties/{prop_id}/history",
    response_model=PropertyHistoryListResponse,
)
def property_history_api(
    prop_id: int,
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    field: str | None = Query(default=None),
    user: str | None = Query(default=None),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    current_user: dict = Depends(require_permission("audit.read")),
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


@api_router.get(
    "/properties/{prop_id}/history/{change_id}",
    response_model=ChangeDetailResponse,
)
def property_history_detail_api(
    prop_id: int,
    change_id: str,
    current_user: dict = Depends(require_permission("audit.read")),
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
