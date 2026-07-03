"""Rate plans — create, update, delete, and list rate plans."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_rate_plan,
    delete_rate_plan,
    update_rate_plan,
)


def create_plan(payload: dict, current_user: dict) -> dict:
    """Create a new rate plan for a property."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_rate_plan(
            prop_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            base_rate=payload.get("base_rate"),
            currency=str(payload.get("currency") or "USD"),
            room_type_id=str(payload.get("room_type_id") or ""),
            base_occupancy=int(payload.get("base_occupancy") or 2),
            extra_adult_price=float(payload.get("extra_adult_price") or 0),
            extra_child_price=float(payload.get("extra_child_price") or 0),
            tax_included=payload.get("tax_included", False),
            tax_rate=float(payload.get("tax_rate") or 0),
            is_active=payload.get("is_active", True),
            eligible_roles=payload.get("eligible_roles"),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


def update_plan(plan_id: str, payload: dict, current_user: dict) -> dict:
    """Update an existing rate plan."""
    try:
        saved = update_rate_plan(
            plan_id,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            base_rate=payload.get("base_rate"),
            currency=str(payload.get("currency") or "USD"),
            room_type_id=str(payload.get("room_type_id") or ""),
            base_occupancy=int(payload.get("base_occupancy") or 2),
            extra_adult_price=float(payload.get("extra_adult_price") or 0),
            extra_child_price=float(payload.get("extra_child_price") or 0),
            tax_included=payload.get("tax_included", False),
            tax_rate=float(payload.get("tax_rate") or 0),
            is_active=payload.get("is_active", True),
            eligible_roles=payload.get("eligible_roles"),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate plan not found")
    return saved


def delete_plan(plan_id: str, current_user: dict) -> dict:
    """Delete a rate plan."""
    try:
        result = delete_rate_plan(plan_id, changed_by=current_user.get("username", "system"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate plan not found")
    return result
