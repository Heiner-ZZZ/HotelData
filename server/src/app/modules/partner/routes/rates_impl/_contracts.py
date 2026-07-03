"""Corporate contracts — CRUD and validation."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.modules.partner.routes._common import require_prop_id
from src.app.modules.partner.services import (
    create_corporate_contract,
    delete_corporate_contract,
    list_corporate_contracts,
    update_corporate_contract,
    validate_contract_code,
)


def get_contracts(
    prop_id: int | None = None,
    is_active: bool | None = None,
) -> dict:
    """List corporate contracts with optional filters."""
    items = list_corporate_contracts(prop_id=prop_id, is_active=is_active)
    return {"items": items, "total": len(items)}


def create_contract(payload: dict, current_user: dict) -> dict:
    """Create a new corporate contract."""
    prop_id = require_prop_id(int(payload.get("prop_id") or 0))
    try:
        saved = create_corporate_contract(
            prop_id,
            company_name=str(payload.get("company_name") or ""),
            contract_code=str(payload.get("contract_code") or ""),
            description=str(payload.get("description") or ""),
            discount_percent=int(payload.get("discount_percent") or 0),
            fixed_rate=float(payload.get("fixed_rate") or 0),
            applicable_rate_plan_ids=payload.get("applicable_rate_plan_ids"),
            applicable_room_type_ids=payload.get("applicable_room_type_ids"),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            is_active=payload.get("is_active", True),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return saved


def update_contract(contract_id: str, payload: dict, current_user: dict) -> dict:
    """Update an existing corporate contract."""
    try:
        saved = update_corporate_contract(
            contract_id,
            company_name=str(payload.get("company_name") or ""),
            contract_code=str(payload.get("contract_code") or ""),
            description=str(payload.get("description") or ""),
            discount_percent=int(payload.get("discount_percent") or 0),
            fixed_rate=float(payload.get("fixed_rate") or 0),
            applicable_rate_plan_ids=payload.get("applicable_rate_plan_ids"),
            applicable_room_type_ids=payload.get("applicable_room_type_ids"),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            is_active=payload.get("is_active", True),
            changed_by=current_user.get("username", "system"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return saved


def delete_contract(contract_id: str, current_user: dict) -> dict:
    """Delete a corporate contract."""
    result = delete_corporate_contract(contract_id, changed_by=current_user.get("username", "system"))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return result


def validate_contract(payload: dict) -> dict:
    """Validate a corporate contract code for a given property and room type."""
    try:
        prop_id = int(payload.get("prop_id") or 0)
        contract_code = str(payload.get("contract_code") or "")
        room_type_id = str(payload.get("room_type_id") or "")
        if not contract_code:
            raise HTTPException(status_code=400, detail="contract_code is required")
        if not prop_id:
            raise HTTPException(status_code=400, detail="prop_id is required")
        error, contract = validate_contract_code(
            contract_code, prop_id,
            room_type_id=room_type_id,
        )
        if error:
            raise HTTPException(status_code=400, detail=error)
        return {
            "valid": True,
            "contract_id": contract.get("contract_id", "") if contract else "",
            "company_name": contract.get("company_name", "") if contract else "",
            "rate_label": _contract_rate_label(contract) if contract else "",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _contract_rate_label(contract: dict) -> str:
    """Generate a human-readable label for a contract's rate."""
    if contract.get("fixed_rate", 0) > 0:
        return f"${contract['fixed_rate']:.2f}/noche (tarifa fija)"
    pct = contract.get("discount_percent", 0)
    return f"{pct}% descuento"
