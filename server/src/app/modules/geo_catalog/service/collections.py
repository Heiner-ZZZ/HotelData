"""Collections and indexes for the geographic catalog module."""

from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from src.database.collections import ensure_collection

GEO_COLLECTION = "geo_catalog"

GEO_INDEXES = [
    IndexModel([("type", ASCENDING)], name="idx_geo_type"),
    IndexModel([("code", ASCENDING)], name="idx_geo_code"),
    IndexModel([("country_code", ASCENDING)], name="idx_geo_country"),
    IndexModel([("state_code", ASCENDING)], name="idx_geo_state"),
    IndexModel([("type", ASCENDING), ("code", ASCENDING)], name="idx_geo_type_code", unique=True),
    IndexModel([("name", ASCENDING)], name="idx_geo_name"),
]


def ensure_geo_collections() -> None:
    ensure_collection(GEO_COLLECTION, GEO_INDEXES)
