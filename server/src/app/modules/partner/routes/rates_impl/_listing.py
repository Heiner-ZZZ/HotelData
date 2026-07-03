"""Rates listing — hotel rates overview and property options."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    filter_eligible_plans,
    list_partner_hotels,
    partner_hotel_rates,
)


def get_hotel_rates_detail(prop_id: int) -> dict:
    """Get full rates detail for a hotel property."""
    prop_id = require_prop_id(prop_id)
    detail = partner_hotel_rates(prop_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return {
        "prop_id": detail["hotel"]["prop_id"],
        "hotel_label": detail["hotel"]["display_name"],
        "manual_override": detail["hotel"].get("manual_override", False),
        "profile_badge": detail["hotel"].get("profile_badge"),
        "rate_plans": detail.get("rate_plans", []),
        "calendar": detail.get("calendar", []),
        "rate_rules": detail.get("rate_rules", []),
        "promotions": detail.get("promotions", []),
        "coupon_codes": detail.get("coupon_codes", []),
        "room_types": detail.get("room_types", []),
    }


def get_rates_options(
    prop_id: int | None,
    q: str,
    page: int,
    page_size: int,
    current_user: dict,
) -> dict[str, Any]:
    """Get property options for the rates UI, optionally filtering by query and including rate plan info."""
    results = list_partner_hotels(q, page=page, page_size=page_size, user=current_user)
    response: dict[str, Any] = {
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
    if prop_id:
        require_prop_id(prop_id)
        detail = partner_hotel_rates(prop_id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        user_role = current_user.get("primary_role", "")
        eligible_plans = filter_eligible_plans(detail.get("rate_plans", []), user_role=user_role)
        response["rate_plans"] = [
            {
                "rate_plan_id": item["rate_plan_id"],
                "name": item.get("name") or item["rate_plan_id"],
                "eligible_roles": item.get("eligible_roles", []),
            }
            for item in eligible_plans
        ]
    return response
