from __future__ import annotations

from fastapi import Body, HTTPException, Query, status

from fastapi import Depends

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    management_property_options,
    partner_hotel_content,
    save_partner_hotel_amenities,
)
from src.app.security.dependencies import require_login


@api_router.get("/amenities")
def amenities_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_content(require_prop_id(prop_id))
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/amenities/options")
def amenities_options_api(prop_id: int | None = Query(default=None, ge=1), current_user: dict = Depends(require_login)):
    response: dict[str, object] = {"properties": management_property_options(user=current_user)}
    if prop_id:
        detail = partner_hotel_content(require_prop_id(prop_id))
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        response["catalog"] = detail.get("amenities", {}).get("catalog", [])
        response["active_amenities"] = detail.get("amenities", {}).get("active_amenities", [])
    return response


@api_router.put("/amenities")
def amenities_update_api(payload: dict = Body(...)):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    active_amenities = payload.get("active_amenities") or []
    if not isinstance(active_amenities, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="active_amenities must be a list")
    saved = save_partner_hotel_amenities(
        prop_id,
        active_amenities=[str(item) for item in active_amenities],
        amenities_text=str(payload.get("amenities_text") or ""),
        changed_by="angular_api",
    )
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved
