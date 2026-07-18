"""Idempotent MongoDB collection + index bootstrap for the partner domain.

Owns `module_status` and the four `ensure_*_collections` functions that
create collections and indexes for content, profile, inventory and rates.

These four functions are now called once at FastAPI `lifespan` startup
(`src/app/main.py`) instead of being invoked from every service write
path. The functions are kept as the public API of this module (re-exported
via `services/__init__.py`) so external scripts like
`scripts/init_hotel_content_ga03.py` and `scripts/init_inventory_ga03.py`
can still invoke them directly outside of a running app process.
"""
from __future__ import annotations

import logging

from pymongo import IndexModel, ASCENDING, DESCENDING

from src.app.modules.partner.schemas import ModuleStatus
from src.database.collections import ensure_collection, drop_index_safe

logger = logging.getLogger(__name__)


CONTENT_COLLECTIONS: dict[str, list[IndexModel]] = {
    "hotel_images": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("prop_id", ASCENDING), ("image_url", ASCENDING)], name="image_url_1", unique=True),
        IndexModel([("created_at", DESCENDING)], name="created_at_-1"),
    ],
    "hotel_policies": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1", unique=True),
        IndexModel([("updated_at", DESCENDING)], name="updated_at_-1"),
    ],
    "hotel_content_pages": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1", unique=True),
        IndexModel([("updated_at", DESCENDING)], name="updated_at_-1"),
    ],
    "hotel_content_changes": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("entity_type", ASCENDING)], name="entity_type_1"),
        IndexModel([("changed_at", DESCENDING)], name="changed_at_-1"),
    ],
}

INVENTORY_COLLECTIONS: dict[str, list[IndexModel]] = {
    "room_types": [
        IndexModel([("room_type_id", ASCENDING)], name="room_type_id_1", unique=True),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("is_active", ASCENDING)], name="is_active_1"),
    ],
    "hotel_rooms": [
        IndexModel([("hotel_room_id", ASCENDING)], name="hotel_room_id_1", unique=True),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("room_type_id", ASCENDING)], name="room_type_id_1"),
    ],
    "room_inventory_calendar": [
        IndexModel([("prop_id", ASCENDING), ("room_type_id", ASCENDING), ("date", ASCENDING)], name="prop_room_date", unique=True),
        IndexModel([("date", ASCENDING)], name="date_1"),
    ],
    "room_availability_blocks": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("room_type_id", ASCENDING)], name="room_type_id_1"),
        IndexModel([("start_date", ASCENDING)], name="start_date_1"),
    ],
    "blackout_dates": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("room_type_id", ASCENDING)], name="room_type_id_1"),
        IndexModel([("start_date", ASCENDING)], name="start_date_1"),
        IndexModel([("end_date", ASCENDING)], name="end_date_1"),
    ],
}

RATE_COLLECTIONS: dict[str, list[IndexModel]] = {
    "rate_plans": [
        IndexModel([("rate_plan_id", ASCENDING)], name="rate_plan_id_1", unique=True),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("is_active", ASCENDING)], name="is_active_1"),
    ],
    "hotel_rate_calendar": [
        IndexModel([("prop_id", ASCENDING), ("rate_plan_id", ASCENDING), ("date", ASCENDING)], name="prop_rate_date", unique=True),
        IndexModel([("date", ASCENDING)], name="date_1"),
    ],
    "rate_rules": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("rate_plan_id", ASCENDING)], name="rate_plan_id_1"),
    ],
    "promotion_campaigns": [
        IndexModel([("campaign_id", ASCENDING)], name="campaign_id_1", unique=True),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("is_active", ASCENDING)], name="is_active_1"),
    ],
    "coupon_codes": [
        IndexModel([("coupon_code", ASCENDING)], name="coupon_code_1", unique=True),
        IndexModel([("campaign_id", ASCENDING)], name="campaign_id_1"),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
    ],
}

PROFILE_COLLECTIONS: dict[str, list[IndexModel]] = {
    "hotel_profile_changes": [
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("changed_at", DESCENDING)], name="changed_at_-1"),
        IndexModel([("prop_id", ASCENDING), ("field", ASCENDING), ("changed_at", DESCENDING)], name="prop_field_changed_at"),
    ],
}

AUDIT_INDEXES = [
    IndexModel([("timestamp", DESCENDING)], name="timestamp_-1"),
    IndexModel([("prop_id", ASCENDING), ("timestamp", DESCENDING)], name="prop_id_1_timestamp_-1"),
    IndexModel([("entity_type", ASCENDING), ("timestamp", DESCENDING)], name="entity_type_1_timestamp_-1"),
]

DIM_HOTELS_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="prop_id_1", unique=True),
    IndexModel([("display_name", ASCENDING)], name="display_name_1"),
    IndexModel([("manual_override", ASCENDING)], name="manual_override_1"),
]


# ── Room features collection ──
ROOM_FEATURES_COLLECTIONS: dict[str, list[IndexModel]] = {
    "room_features": [
        IndexModel([("label", ASCENDING)], name="label_1", unique=True),
        IndexModel([("category", ASCENDING)], name="category_1"),
    ],
    "hotel_products": [
        IndexModel([("prop_id", ASCENDING), ("product_id", ASCENDING)], name="prop_product", unique=True),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("category", ASCENDING)], name="category_1"),
    ],
    "platform_earnings": [
        IndexModel([("booking_id", ASCENDING)], name="booking_id_1", unique=True),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("created_at", DESCENDING)], name="created_at_-1"),
    ],
}


def ensure_room_features_collections() -> dict[str, list[str]]:
    reports = [_ensure_with_report(name, idxs) for name, idxs in ROOM_FEATURES_COLLECTIONS.items()]
    return _merge_reports(reports)


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="partner",
        status="partial",
        description="Modulo inicial de Hotel Partner con contenido, habitaciones e inventario operativo basico.",
    )


def _ensure_with_report(name: str, indexes: list[IndexModel]) -> dict[str, list[str]]:
    created = ensure_collection(name, indexes)
    return {"collections": [name] if any(c.startswith("collection:") for c in created) else [], "indexes": [c for c in created if c.startswith("index:")]}


def _merge_reports(reports: list[dict[str, list[str]]]) -> dict[str, list[str]]:
    collections: list[str] = []
    indexes: list[str] = []
    for r in reports:
        collections.extend(r.get("collections", []))
        indexes.extend(r.get("indexes", []))
    return {"collections": collections, "indexes": indexes}


def ensure_hotel_content_collections() -> dict[str, list[str]]:
    reports = [_ensure_with_report(name, idxs) for name, idxs in CONTENT_COLLECTIONS.items()]
    return _merge_reports(reports)


def ensure_hotel_profile_collections() -> dict[str, list[str]]:
    drop_index_safe("dim_hotels", "prop_id_1")
    reports = [_ensure_with_report(name, idxs) for name, idxs in PROFILE_COLLECTIONS.items()]
    dim_created = ensure_collection("dim_hotels", DIM_HOTELS_INDEXES)
    dim_indexes = [c for c in dim_created if c.startswith("index:")]
    reports.append({"collections": [], "indexes": dim_indexes})
    return _merge_reports(reports)


def ensure_inventory_collections() -> dict[str, list[str]]:
    reports = [_ensure_with_report(name, idxs) for name, idxs in INVENTORY_COLLECTIONS.items()]
    return _merge_reports(reports)


def ensure_rate_collections() -> dict[str, list[str]]:
    reports = [_ensure_with_report(name, idxs) for name, idxs in RATE_COLLECTIONS.items()]
    return _merge_reports(reports)
