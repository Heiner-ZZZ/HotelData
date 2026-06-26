from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, IndexModel
from pymongo.database import Database

from src.database.collections import ensure_collection
from src.database.connection import get_database

SYSTEM_CONFIG = "system_config"
TAX_RATES = "tax_rates"
COMMISSION_RATES = "commission_rates"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_global_settings_collections() -> None:
    """Ensure all global settings collections and indexes exist."""
    db = get_database()

    # system_config — singleton document with global platform config
    if SYSTEM_CONFIG not in db.list_collection_names():
        db.create_collection(SYSTEM_CONFIG)
        db[SYSTEM_CONFIG].insert_one({
            "_id": "global",
            "default_commission_pct": 5.0,
            "default_iva_pct": 16.0,
            "updated_at": _now(),
            "updated_by": "system",
        })

    # tax_rates — per-country IVA rates
    ensure_collection(TAX_RATES, [
        IndexModel([("country_id", ASCENDING)], name="idx_tr_country", unique=True),
        IndexModel([("country_name", ASCENDING)], name="idx_tr_country_name"),
    ])

    # commission_rates — per-hotel commission overrides
    ensure_collection(COMMISSION_RATES, [
        IndexModel([("prop_id", ASCENDING)], name="idx_cr_prop", unique=True),
    ])


# ─── Platform Config ────────────────────────────────────────────────────


def get_platform_config() -> dict[str, Any]:
    db = get_database()
    config = db[SYSTEM_CONFIG].find_one({"_id": "global"})
    if not config:
        return {
            "default_commission_pct": 5.0,
            "default_iva_pct": 16.0,
            "updated_at": None,
            "updated_by": None,
        }
    return {
        "default_commission_pct": config.get("default_commission_pct", 5.0),
        "default_iva_pct": config.get("default_iva_pct", 16.0),
        "updated_at": config["updated_at"].isoformat() if isinstance(config.get("updated_at"), datetime) else config.get("updated_at"),
        "updated_by": config.get("updated_by"),
    }


def update_platform_config(
    default_commission_pct: float | None = None,
    default_iva_pct: float | None = None,
    updated_by: str = "admin",
) -> dict[str, Any]:
    db = get_database()
    set_doc: dict[str, Any] = {"updated_at": _now(), "updated_by": updated_by}
    if default_commission_pct is not None:
        set_doc["default_commission_pct"] = default_commission_pct
    if default_iva_pct is not None:
        set_doc["default_iva_pct"] = default_iva_pct

    db[SYSTEM_CONFIG].update_one(
        {"_id": "global"},
        {"$set": set_doc},
        upsert=True,
    )
    return get_platform_config()


# ─── Hotels Global Data ─────────────────────────────────────────────────


def list_global_hotels(
    q: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """List all dim_hotels entries with global data fields for admin editing."""
    db = get_database()
    match: dict[str, Any] = {}
    if q:
        import re
        pattern = re.escape(q)
        match["$or"] = [
            {"hotel_name": {"$regex": pattern, "$options": "i"}},
            {"display_name": {"$regex": pattern, "$options": "i"}},
            {"city": {"$regex": pattern, "$options": "i"}},
            {"province": {"$regex": pattern, "$options": "i"}},
            {"country_name": {"$regex": pattern, "$options": "i"}},
            {"hotel_group": {"$regex": pattern, "$options": "i"}},
        ]

    total = db.dim_hotels.count_documents(match)
    cursor = (
        db.dim_hotels.find(
            match,
            {
                "_id": 0,
                "prop_id": 1,
                "hotel_name": 1,
                "display_name": 1,
                "country_name": 1,
                "city": 1,
                "province": 1,
                "hotel_group": 1,
                "prop_country_id": 1,
                "prop_starrating": 1,
            },
        )
        .sort("prop_id", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items = []
    for doc in cursor:
        items.append({
            "prop_id": doc.get("prop_id"),
            "hotel_name": doc.get("hotel_name") or doc.get("display_name") or f"Hotel {doc.get('prop_id')}",
            "display_name": doc.get("display_name") or doc.get("hotel_name") or f"Hotel {doc.get('prop_id')}",
            "country_name": doc.get("country_name") or "",
            "city": doc.get("city") or "",
            "province": doc.get("province") or "",
            "hotel_group": doc.get("hotel_group") or "",
            "prop_country_id": doc.get("prop_country_id"),
            "prop_starrating": doc.get("prop_starrating"),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


def get_hotel_global_data(prop_id: int) -> dict[str, Any] | None:
    db = get_database()
    doc = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {
            "_id": 0,
            "prop_id": 1,
            "hotel_name": 1,
            "display_name": 1,
            "country_name": 1,
            "city": 1,
            "province": 1,
            "hotel_group": 1,
            "prop_country_id": 1,
        },
    )
    if not doc:
        return None
    return {
        "prop_id": doc.get("prop_id"),
        "hotel_name": doc.get("hotel_name") or doc.get("display_name") or f"Hotel {doc.get('prop_id')}",
        "display_name": doc.get("display_name") or "",
        "country_name": doc.get("country_name") or "",
        "city": doc.get("city") or "",
        "province": doc.get("province") or "",
        "hotel_group": doc.get("hotel_group") or "",
        "prop_country_id": doc.get("prop_country_id"),
    }


def update_hotel_global_data(
    prop_id: int,
    country_name: str | None = None,
    city: str | None = None,
    province: str | None = None,
    hotel_group: str | None = None,
    updated_by: str = "admin",
) -> dict[str, Any] | None:
    db = get_database()
    set_doc: dict[str, Any] = {}
    if country_name is not None:
        set_doc["country_name"] = country_name
    if city is not None:
        set_doc["city"] = city
    if province is not None:
        set_doc["province"] = province
    if hotel_group is not None:
        set_doc["hotel_group"] = hotel_group

    if not set_doc:
        return get_hotel_global_data(prop_id)

    set_doc["updated_at"] = _now()
    set_doc["updated_by"] = updated_by

    result = db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {"$set": set_doc},
    )
    if result.matched_count == 0:
        return None
    return get_hotel_global_data(prop_id)


# ─── Tax Rates (IVA per country) ────────────────────────────────────────


def list_tax_rates() -> list[dict[str, Any]]:
    db = get_database()
    cursor = db[TAX_RATES].find({}, {"_id": 0}).sort("country_id", 1)
    items = []
    for doc in cursor:
        items.append({
            "country_id": doc.get("country_id"),
            "country_name": doc.get("country_name") or f"País {doc.get('country_id')}",
            "iva_pct": doc.get("iva_pct", 16.0),
            "updated_at": doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
        })
    return items


def upsert_tax_rate(
    country_id: int,
    iva_pct: float,
    country_name: str = "",
    updated_by: str = "admin",
) -> dict[str, Any]:
    db = get_database()
    db[TAX_RATES].update_one(
        {"country_id": country_id},
        {
            "$set": {
                "iva_pct": iva_pct,
                "country_name": country_name,
                "updated_at": _now(),
                "updated_by": updated_by,
            }
        },
        upsert=True,
    )
    doc = db[TAX_RATES].find_one({"country_id": country_id}, {"_id": 0})
    return {
        "country_id": doc.get("country_id"),
        "country_name": doc.get("country_name") or f"País {doc.get('country_id')}",
        "iva_pct": doc.get("iva_pct", 16.0),
        "updated_at": doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
    } if doc else {"country_id": country_id, "iva_pct": iva_pct, "updated_at": _now().isoformat()}


def delete_tax_rate(country_id: int) -> bool:
    db = get_database()
    result = db[TAX_RATES].delete_one({"country_id": country_id})
    return result.deleted_count > 0


# ─── Commission Rates (per hotel override) ──────────────────────────────


def list_commission_rates() -> list[dict[str, Any]]:
    db = get_database()
    cursor = db[COMMISSION_RATES].find({}, {"_id": 0}).sort("prop_id", 1)
    # Enrich with hotel name
    items = []
    for doc in cursor:
        prop_id = doc.get("prop_id")
        hotel = db.dim_hotels.find_one(
            {"prop_id": prop_id},
            {"hotel_name": 1, "display_name": 1, "_id": 0},
        )
        hotel_name = (hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}") if hotel else f"Hotel {prop_id}"
        items.append({
            "prop_id": prop_id,
            "hotel_name": hotel_name,
            "commission_pct": doc.get("commission_pct", 0.0),
            "updated_at": doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
        })
    return items


def upsert_commission_rate(
    prop_id: int,
    commission_pct: float,
    updated_by: str = "admin",
) -> dict[str, Any]:
    db = get_database()

    # Verify hotel exists
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"display_name": 1, "hotel_name": 1, "_id": 0})
    hotel_name = (hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}") if hotel else None

    db[COMMISSION_RATES].update_one(
        {"prop_id": prop_id},
        {
            "$set": {
                "commission_pct": commission_pct,
                "updated_at": _now(),
                "updated_by": updated_by,
            }
        },
        upsert=True,
    )
    return {
        "prop_id": prop_id,
        "hotel_name": hotel_name or f"Hotel {prop_id}",
        "commission_pct": commission_pct,
        "updated_at": _now().isoformat(),
    }


def delete_commission_rate(prop_id: int) -> bool:
    db = get_database()
    result = db[COMMISSION_RATES].delete_one({"prop_id": prop_id})
    return result.deleted_count > 0
