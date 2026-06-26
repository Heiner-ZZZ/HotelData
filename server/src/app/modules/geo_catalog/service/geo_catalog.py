"""Geographic catalog CRUD operations.

Manages countries, states/provinces, cities, and tourist destinations.
Allows admin to create, read, update, and delete geographic entries.
Also provides a resolve endpoint to map IDs to display names.
"""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from .collections import GEO_COLLECTION
from ..schemas import GeoEntryCreate, GeoEntryUpdate, now_iso

logger = logging.getLogger(__name__)


# ─── CRUD ───────────────────────────────────────────────────────────────


def create_geo_entry(payload: GeoEntryCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()
    doc = {
        "type": payload.type,
        "code": payload.code,
        "name": payload.name,
        "country_code": payload.country_code,
        "state_code": payload.state_code,
        "category": payload.category,
        "iso_code": payload.iso_code,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "is_active": True,
        "created_at": now,
        "updated_at": None,
    }
    try:
        result = db[GEO_COLLECTION].insert_one(doc)
        doc["_id"] = result.inserted_id
        logger.info("Created geo entry %s/%s (%s)", payload.type, payload.code, payload.name)
        return _enrich(doc)
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            raise ValueError(f"Ya existe una entrada con type='{payload.type}' y code='{payload.code}'")
        raise


def list_geo_entries(
    geo_type: str | None = None,
    country_code: str | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {}
    if geo_type:
        query["type"] = geo_type
    if country_code:
        query["country_code"] = country_code
    if q:
        import re
        pattern = re.escape(q)
        query["$or"] = [
            {"name": {"$regex": pattern, "$options": "i"}},
            {"code": {"$regex": pattern, "$options": "i"}},
        ]

    total = db[GEO_COLLECTION].count_documents(query)
    cursor = (
        db[GEO_COLLECTION]
        .find(query)
        .sort("name", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_geo_entry(entry_id: str) -> dict[str, Any] | None:
    db = get_database()
    try:
        doc = db[GEO_COLLECTION].find_one({"_id": ObjectId(entry_id)})
        return _enrich(doc) if doc else None
    except Exception:
        return None


def update_geo_entry(entry_id: str, payload: GeoEntryUpdate) -> dict[str, Any] | None:
    db = get_database()
    set_doc: dict[str, Any] = {"updated_at": now_iso()}
    if payload.name is not None:
        set_doc["name"] = payload.name
    if payload.country_code is not None:
        set_doc["country_code"] = payload.country_code
    if payload.state_code is not None:
        set_doc["state_code"] = payload.state_code
    if payload.category is not None:
        set_doc["category"] = payload.category
    if payload.iso_code is not None:
        set_doc["iso_code"] = payload.iso_code
    if payload.latitude is not None:
        set_doc["latitude"] = payload.latitude
    if payload.longitude is not None:
        set_doc["longitude"] = payload.longitude
    if payload.is_active is not None:
        set_doc["is_active"] = payload.is_active

    if len(set_doc) == 1:
        return get_geo_entry(entry_id)

    try:
        result = db[GEO_COLLECTION].find_one_and_update(
            {"_id": ObjectId(entry_id)},
            {"$set": set_doc},
            return_document=True,
        )
        if result:
            logger.info("Updated geo entry %s", entry_id)
        return _enrich(result) if result else None
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            raise ValueError("El código ya existe para este tipo")
        raise


def delete_geo_entry(entry_id: str) -> bool:
    db = get_database()
    result = db[GEO_COLLECTION].delete_one({"_id": ObjectId(entry_id)})
    if result.deleted_count:
        logger.info("Deleted geo entry %s", entry_id)
    return result.deleted_count > 0


# ─── Resolve IDs to display names ──────────────────────────────────────


def resolve_display_names(
    destination_ids: list[int] | None = None,
    country_ids: list[int] | None = None,
    site_ids: list[int] | None = None,
) -> dict[str, dict[int, str]]:
    """Resolve numeric IDs from dim_* collections to human-readable display names."""
    db = get_database()
    result: dict[str, dict[int, str]] = {
        "destinations": {},
        "countries": {},
        "sites": {},
    }

    if destination_ids:
        for doc in db.dim_destinations.find(
            {"srch_destination_id": {"$in": destination_ids}},
            {"srch_destination_id": 1, "destination_display_name": 1, "_id": 0},
        ):
            sid = doc.get("srch_destination_id")
            name = doc.get("destination_display_name") or f"Destino {sid}"
            if sid is not None:
                result["destinations"][sid] = name

    if country_ids:
        for doc in db.dim_visitor_countries.find(
            {"visitor_location_country_id": {"$in": country_ids}},
            {"visitor_location_country_id": 1, "country_display_name": 1, "_id": 0},
        ):
            cid = doc.get("visitor_location_country_id")
            name = doc.get("country_display_name") or f"País {cid}"
            if cid is not None:
                result["countries"][cid] = name

    if site_ids:
        for doc in db.dim_sites.find(
            {"site_id": {"$in": site_ids}},
            {"site_id": 1, "site_display_name": 1, "_id": 0},
        ):
            sid = doc.get("site_id")
            name = doc.get("site_display_name") or f"Canal {sid}"
            if sid is not None:
                result["sites"][sid] = name

    return result


# ─── Helpers ────────────────────────────────────────────────────────────


def _enrich(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at"):
        if f in doc and hasattr(doc[f], "isoformat"):
            doc[f] = doc[f].isoformat()
    # CamelCase aliases for frontend
    doc["countryCode"] = doc.get("country_code", "")
    doc["stateCode"] = doc.get("state_code", "")
    doc["isoCode"] = doc.get("iso_code", "")
    doc["isActive"] = doc.get("is_active", True)
    doc["createdAt"] = doc.get("created_at", "")
    doc["updatedAt"] = doc.get("updated_at")
    return doc
