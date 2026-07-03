"""Seasonal rules — list, create, update, delete."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_seasonal_rule,
    delete_seasonal_rule,
    list_seasonal_rules,
    update_seasonal_rule,
)


def get_seasonal_rules(
    prop_id: int | None = None,
    rate_plan_id: str | None = None,
) -> dict:
    """List seasonal rules with optional filters."""
    items = list_seasonal_rules(prop_id=prop_id, rate_plan_id=rate_plan_id)
    return {"items": items, "total": len(items)}


def create_seasonal(payload: dict) -> dict:
    """Create a new seasonal rule."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_seasonal_rule(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            name=str(payload.get("name") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            price_override=payload.get("price_override"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


def update_seasonal(rule_id: str, payload: dict) -> dict:
    """Update an existing seasonal rule."""
    try:
        saved = update_seasonal_rule(
            rule_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            name=str(payload.get("name") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            price_override=payload.get("price_override"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seasonal rule not found")
    return saved


def delete_seasonal(rule_id: str) -> dict:
    """Delete a seasonal rule."""
    result = delete_seasonal_rule(rule_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seasonal rule not found")
    return result
