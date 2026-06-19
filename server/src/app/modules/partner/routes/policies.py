from __future__ import annotations

from fastapi import Body, Form, Query, Request
from fastapi.responses import RedirectResponse

from src.app.modules.partner.routes import api_router, templates, web_router
from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    list_partner_hotels,
    partner_hotel_policies,
    save_partner_hotel_policies,
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


@api_router.get("/policies")
def policies_api(prop_id: int = Query(..., ge=1)):
    detail = partner_hotel_policies(require_prop_id(prop_id))
    if detail is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return detail


@api_router.get("/policies/options")
def policies_options_api(
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


@api_router.put("/policies")
def policies_update_api(payload: dict = Body(...)):
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
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
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved
