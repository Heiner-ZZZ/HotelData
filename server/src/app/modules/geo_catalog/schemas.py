"""Pydantic schemas for the geographic catalog module."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class GeoEntryCreate(BaseModel):
    """Create a geographic catalog entry (country, state, city, destination)."""
    type: str  # country, state, city, destination
    code: str
    name: str
    country_code: str = ""
    state_code: str = ""
    category: str = ""
    iso_code: str = ""
    latitude: float | None = None
    longitude: float | None = None


class GeoEntryUpdate(BaseModel):
    name: str | None = None
    country_code: str | None = None
    state_code: str | None = None
    category: str | None = None
    iso_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


class GeoEntryResponse(BaseModel):
    id: str = Field(alias="_id")
    type: str
    code: str
    name: str
    country_code: str = ""
    state_code: str = ""
    category: str = ""
    iso_code: str = ""
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True
    created_at: str = ""
    updated_at: str | None = None


class GeoResolveRequest(BaseModel):
    """Resolve multiple IDs to display names at once."""
    destination_ids: list[int] = []
    country_ids: list[int] = []
    site_ids: list[int] = []


class GeoResolveResponse(BaseModel):
    destinations: dict[int, str] = {}
    countries: dict[int, str] = {}
    sites: dict[int, str] = {}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utc_now().isoformat()
