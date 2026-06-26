from __future__ import annotations

from pydantic import BaseModel, Field


class DestinationUpdate(BaseModel):
    visible_name: str = ""
    country: str = ""
    city: str = ""
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None


class DestinationResponse(BaseModel):
    srch_destination_id: int
    destination_display_name: str = ""
    destination_name: str = ""
    visible_name: str = ""
    country: str = ""
    city: str = ""
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None
    destination_region_label: str = ""
    active: bool = True


class GeoHotelResponse(BaseModel):
    prop_id: int
    hotel_name: str = ""
    display_name: str = ""
    stars: int | None = None
    review_score: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    srch_destination_id: int | None = None
    destination_display_name: str = ""
