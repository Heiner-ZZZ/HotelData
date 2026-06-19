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

from pymongo.errors import CollectionInvalid

from src.app.modules.partner.schemas import ModuleStatus
from src.database.connection import get_database


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="partner",
        status="partial",
        description="Modulo inicial de Hotel Partner con contenido, habitaciones e inventario operativo basico.",
    )


def ensure_hotel_content_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    for name in ("hotel_images", "hotel_policies", "hotel_content_pages", "hotel_content_changes"):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs = {
        "hotel_images": [
            ("prop_id_1", db.hotel_images.create_index("prop_id")),
            ("image_url_1", db.hotel_images.create_index([("prop_id", 1), ("image_url", 1)], unique=True)),
            ("created_at_-1", db.hotel_images.create_index([("created_at", -1)])),
        ],
        "hotel_policies": [
            ("prop_id_1", db.hotel_policies.create_index([("prop_id", 1)], unique=True)),
            ("updated_at_-1", db.hotel_policies.create_index([("updated_at", -1)])),
        ],
        "hotel_content_pages": [
            ("prop_id_1", db.hotel_content_pages.create_index([("prop_id", 1)], unique=True)),
            ("updated_at_-1", db.hotel_content_pages.create_index([("updated_at", -1)])),
        ],
        "hotel_content_changes": [
            ("prop_id_1", db.hotel_content_changes.create_index("prop_id")),
            ("entity_type_1", db.hotel_content_changes.create_index("entity_type")),
            ("changed_at_-1", db.hotel_content_changes.create_index([("changed_at", -1)])),
        ],
    }
    for indexes in index_specs.values():
        for label, name in indexes:
            created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}


def ensure_hotel_profile_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    if "hotel_profile_changes" not in db.list_collection_names():
        try:
            db.create_collection("hotel_profile_changes")
            created_collections.append("hotel_profile_changes")
        except CollectionInvalid:
            pass

    # Drop conflicting non-unique index before creating unique one
    try:
        db.dim_hotels.drop_index("prop_id_1")
    except Exception:
        pass
    index_specs = [
        ("hotel_profile_changes.prop_id_1", db.hotel_profile_changes.create_index("prop_id")),
        ("hotel_profile_changes.changed_at_-1", db.hotel_profile_changes.create_index([("changed_at", -1)])),
        ("hotel_profile_changes.prop_field_changed_at", db.hotel_profile_changes.create_index([("prop_id", 1), ("field", 1), ("changed_at", -1)])),
        ("dim_hotels.prop_id_1", db.dim_hotels.create_index([("prop_id", 1)], unique=True)),
        ("dim_hotels.display_name_1", db.dim_hotels.create_index("display_name")),
        ("dim_hotels.manual_override_1", db.dim_hotels.create_index("manual_override")),
    ]
    for label, name in index_specs:
        created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}


def ensure_inventory_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    for name in ("room_types", "hotel_rooms", "room_inventory_calendar", "room_availability_blocks", "blackout_dates"):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs = {
        "room_types": [
            ("room_type_id_1", db.room_types.create_index([("room_type_id", 1)], unique=True)),
            ("prop_id_1", db.room_types.create_index("prop_id")),
            ("is_active_1", db.room_types.create_index("is_active")),
        ],
        "hotel_rooms": [
            ("hotel_room_id_1", db.hotel_rooms.create_index([("hotel_room_id", 1)], unique=True)),
            ("prop_id_1", db.hotel_rooms.create_index("prop_id")),
            ("room_type_id_1", db.hotel_rooms.create_index("room_type_id")),
        ],
        "room_inventory_calendar": [
            ("prop_room_date", db.room_inventory_calendar.create_index([("prop_id", 1), ("room_type_id", 1), ("date", 1)], unique=True)),
            ("date_1", db.room_inventory_calendar.create_index("date")),
        ],
        "room_availability_blocks": [
            ("prop_id_1", db.room_availability_blocks.create_index("prop_id")),
            ("room_type_id_1", db.room_availability_blocks.create_index("room_type_id")),
            ("start_date_1", db.room_availability_blocks.create_index("start_date")),
        ],
        "blackout_dates": [
            ("prop_id_1", db.blackout_dates.create_index("prop_id")),
            ("room_type_id_1", db.blackout_dates.create_index("room_type_id")),
            ("start_date_1", db.blackout_dates.create_index("start_date")),
            ("end_date_1", db.blackout_dates.create_index("end_date")),
        ],
    }
    for indexes in index_specs.values():
        for label, name in indexes:
            created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}


def ensure_rate_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    created_indexes: list[str] = []
    for name in (
        "rate_plans",
        "hotel_rate_calendar",
        "rate_rules",
        "promotion_campaigns",
        "coupon_codes",
    ):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs = {
        "rate_plans": [
            ("rate_plan_id_1", db.rate_plans.create_index([("rate_plan_id", 1)], unique=True)),
            ("prop_id_1", db.rate_plans.create_index("prop_id")),
            ("is_active_1", db.rate_plans.create_index("is_active")),
        ],
        "hotel_rate_calendar": [
            (
                "prop_rate_date",
                db.hotel_rate_calendar.create_index(
                    [("prop_id", 1), ("rate_plan_id", 1), ("date", 1)],
                    unique=True,
                ),
            ),
            ("date_1", db.hotel_rate_calendar.create_index("date")),
        ],
        "rate_rules": [
            ("prop_id_1", db.rate_rules.create_index("prop_id")),
            ("rate_plan_id_1", db.rate_rules.create_index("rate_plan_id")),
        ],
        "promotion_campaigns": [
            ("campaign_id_1", db.promotion_campaigns.create_index([("campaign_id", 1)], unique=True)),
            ("prop_id_1", db.promotion_campaigns.create_index("prop_id")),
            ("is_active_1", db.promotion_campaigns.create_index("is_active")),
        ],
        "coupon_codes": [
            ("coupon_code_1", db.coupon_codes.create_index([("coupon_code", 1)], unique=True)),
            ("campaign_id_1", db.coupon_codes.create_index("campaign_id")),
            ("prop_id_1", db.coupon_codes.create_index("prop_id")),
        ],
    }
    for indexes in index_specs.values():
        for label, name in indexes:
            created_indexes.append(f"{label}:{name}")
    return {"collections": created_collections, "indexes": created_indexes}
