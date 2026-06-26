from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class PlatformConfig(BaseModel):
    default_commission_pct: float = 5.0
    default_iva_pct: float = 16.0


class PlatformConfigResponse(PlatformConfig):
    updated_at: str | None = None
    updated_by: str | None = None


class TaxRateCreate(BaseModel):
    country_id: int
    country_name: str = ""
    iva_pct: float


class TaxRateResponse(TaxRateCreate):
    updated_at: str


class CommissionRateCreate(BaseModel):
    prop_id: int
    commission_pct: float


class CommissionRateResponse(CommissionRateCreate):
    updated_at: str


class HotelGlobalData(BaseModel):
    prop_id: int
    hotel_name: str = ""
    display_name: str = ""
    country_name: str = ""
    city: str = ""
    province: str = ""
    hotel_group: str = ""
    prop_country_id: int | None = None


class HotelGlobalUpdate(BaseModel):
    country_name: str | None = None
    city: str | None = None
    province: str | None = None
    hotel_group: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
