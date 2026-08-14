"""Rate calendar — update single entry, batch update, and generate from rules."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    batch_update_rate_calendar,
    generate_calendar_from_rules,
    save_rate_calendar_entry,
)


def update_calendar_entry(payload: dict, current_user: dict) -> dict:
    """Update a single rate calendar entry."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = save_rate_calendar_entry(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            date=str(payload.get("date") or ""),
            rate_amount=payload.get("rate_amount"),
            min_stay_nights=payload.get("min_stay_nights"),
            is_closed=payload.get("is_closed", False),
            tax_included=payload.get("tax_included"),
            tax_rate=payload.get("tax_rate"),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


def batch_update_calendar(payload: dict, current_user: dict) -> dict:
    """Batch update rate calendar for a date range."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        result = batch_update_rate_calendar(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            rate_amount=payload.get("rate_amount"),
            min_stay_nights=payload.get("min_stay_nights"),
            is_closed=payload.get("is_closed"),
            only_weekends=bool(payload.get("only_weekends", False)),
            tax_included=payload.get("tax_included"),
            tax_rate=payload.get("tax_rate"),
            changed_by=current_user.get("username", "system"),
            dry_run=bool(payload.get("dry_run")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result


def generate_calendar(payload: dict) -> dict:
    """Generate calendar entries from base_price + seasonal rules."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        result = generate_calendar_from_rules(
            prop_id,
            rate_plan_id=str(payload.get("rate_plan_id") or "") or None,
            start_date=str(payload.get("start_date") or "") or None,
            end_date=str(payload.get("end_date") or "") or None,
            dry_run=bool(payload.get("dry_run")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result
