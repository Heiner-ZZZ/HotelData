from __future__ import annotations

from fastapi import Body, Depends, HTTPException, Query, status

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services.currencies import (
    currency_by_code,
    delete_currency,
    list_currencies,
    save_currency,
    toggle_currency_active,
)
from src.app.security.dependencies import require_login


@api_router.get("/currencies")
def list_currencies_api(
    active_only: bool = Query(default=False),
    current_user: dict = Depends(require_login),
):
    """Return all configured currencies."""
    return {"currencies": list_currencies(active_only=active_only)}


@api_router.get("/currencies/{code}")
def get_currency_api(
    code: str,
    current_user: dict = Depends(require_login),
):
    """Get a single currency by code."""
    cur = currency_by_code(code)
    if cur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    return cur


@api_router.post("/currencies", status_code=status.HTTP_201_CREATED)
def create_currency_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a new currency."""
    code = str(payload.get("code") or "")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Currency code is required")
    try:
        return save_currency(
            code=code,
            name=str(payload.get("name") or ""),
            symbol=str(payload.get("symbol") or "$"),
            decimals=int(payload["decimals"]) if "decimals" in payload and payload["decimals"] is not None else None,
            active=bool(payload.get("active", True)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.put("/currencies/{code}")
def update_currency_api(
    code: str,
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Update an existing currency."""
    existing = currency_by_code(code)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    try:
        return save_currency(
            code=code,
            name=str(payload.get("name") or existing.get("name", "")),
            symbol=str(payload.get("symbol") or existing.get("symbol", "$")),
            decimals=int(payload["decimals"]) if "decimals" in payload and payload["decimals"] is not None else existing.get("decimals"),
            active=bool(payload.get("active", existing.get("active", True))),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.patch("/currencies/{code}/toggle")
def toggle_currency_api(
    code: str,
    current_user: dict = Depends(require_login),
):
    """Toggle active/inactive status of a currency."""
    result = toggle_currency_active(code)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    return result


@api_router.delete("/currencies/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_currency_api(
    code: str,
    current_user: dict = Depends(require_login),
):
    """Delete a currency permanently. Refuses if referenced by properties."""
    try:
        if not delete_currency(code):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return None
