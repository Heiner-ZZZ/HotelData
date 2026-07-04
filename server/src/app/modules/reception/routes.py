from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.app.security.dependencies import require_login

from .shifts import (
    open_shift,
    close_shift,
    get_active_shift,
    get_shift,
    list_shifts,
    SHIFT_TYPE_LABELS,
)

api_router = APIRouter(prefix="/api/reception", tags=["reception-api"])


@api_router.get("/shifts/active")
def shift_active_api(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_login),
):
    """Return the currently active shift for a property, or null."""
    shift = get_active_shift(prop_id)
    if shift is None:
        return {"shift": None, "shift_type_labels": SHIFT_TYPE_LABELS}
    return {"shift": shift, "shift_type_labels": SHIFT_TYPE_LABELS}


@api_router.post("/shifts/open")
def shift_open_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Open a new reception shift."""
    prop_id = payload.get("prop_id")
    shift_type = payload.get("shift_type", "morning")
    employee = payload.get("employee", "")
    cash_initial = float(payload.get("cash_initial", 0) or 0)

    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id es requerido")
    if not employee:
        raise HTTPException(status_code=400, detail="employee es requerido")
    if shift_type not in ("morning", "afternoon", "evening"):
        raise HTTPException(status_code=400, detail="shift_type debe ser: morning, afternoon, evening")

    try:
        result = open_shift(
            prop_id=prop_id,
            shift_type=shift_type,
            employee=employee,
            cash_initial=cash_initial,
        )
        return {"shift": result, "message": f"Turno {SHIFT_TYPE_LABELS.get(shift_type, shift_type)} abierto"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.post("/shifts/{shift_id}/close")
def shift_close_api(
    shift_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Close an active shift with final cash count and optional deposits."""
    cash_final = float(payload.get("cash_final", 0) or 0)
    closed_by = payload.get("closed_by") or current_user.get("username", "web")
    deposits = payload.get("deposits") or None

    try:
        result = close_shift(
            shift_id=shift_id,
            cash_final=cash_final,
            closed_by=closed_by,
            deposits=deposits,
        )
        pbreak = result.get("payment_breakdown", {})
        return {
            "shift": result,
            "message": "Turno cerrado",
            "summary": {
                "cash_initial": result.get("cash_initial", 0),
                "cash_final": result.get("cash_final", 0),
                "total_collected": result.get("total_collected", 0),
                "cash_difference": result.get("cash_difference", 0),
                "cash_expected": result.get("cash_expected", 0),
                "transaction_count": len(result.get("transactions", [])),
                "payment_breakdown": {
                    "cash": pbreak.get("cash", 0),
                    "card": pbreak.get("card", 0),
                    "transfer": pbreak.get("transfer", 0),
                    "other": pbreak.get("other", 0),
                    "total": pbreak.get("total", 0),
                },
                "deposit_total": result.get("deposit_total", 0),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.get("/shifts/{shift_id}")
def shift_detail_api(
    shift_id: str,
    current_user: dict = Depends(require_login),
):
    """Return detailed info for a specific shift."""
    shift = get_shift(shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return {"shift": shift}


@api_router.get("/shifts")
def shift_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_login),
):
    """List shifts for a property, newest first."""
    shifts = list_shifts(prop_id=prop_id, status_filter=status_filter, limit=limit)
    return {"items": shifts, "total": len(shifts)}
