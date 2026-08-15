"""Promotions — create promotion campaigns from rate routes."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.app.modules.revenue.services.promotions import (
    CouponCodeExistsError,
    create_promotion_campaign,
)


def create_promotion(payload: dict) -> dict:
    """Create a new promotion campaign."""
    try:
        saved = create_promotion_campaign(
            prop_id=payload.get("prop_id"),
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            discount_percent=payload.get("discount_percent", 0),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            coupon_code=str(payload.get("coupon_code") or ""),
            is_active=payload.get("is_active", True),
        )
    except CouponCodeExistsError as exc:
        # Error ESTRUCTURADO (contrato único en ``exc.detail``, igual que en
        # marketing): el form de Tarifas detecta ``code == "COUPON_CODE_EXISTS"``
        # y muestra el conflicto de forma destacada sin parsear el mensaje.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return saved
