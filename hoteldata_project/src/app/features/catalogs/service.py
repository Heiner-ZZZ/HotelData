from __future__ import annotations

from datetime import datetime, timezone

from src.database.connection import get_database


DEFAULT_CATALOG_TYPES = [
    "quality_levels",
    "issue_types",
    "status_flags",
    "metric_groups",
]


def ensure_default_catalogs() -> None:
    db = get_database()
    now = datetime.now(timezone.utc)
    for catalog_type in DEFAULT_CATALOG_TYPES:
        # if there are already items for this catalog_type, skip
        if db.system_catalogs.count_documents({"catalog_type": catalog_type}) > 0:
            continue
        # insert a minimal default entry
        default = {
            "catalog_type": catalog_type,
            "code": "DEFAULT",
            "label": "Default",
            "created_at": now,
            "updated_at": now,
        }
        db.system_catalogs.update_one(
            {"catalog_type": catalog_type, "code": default["code"]},
            {"$setOnInsert": default},
            upsert=True,
        )


def list_catalog_items(catalog_type: str) -> list[dict]:
    return list(
        get_database()
        .system_catalogs
        .find({"catalog_type": catalog_type}, {"_id": 0})
        .sort("code", 1)
    )


def list_catalog_types() -> list[str]:
    db = get_database()
    values = db.system_catalogs.distinct("catalog_type")
    catalog_types = sorted({*DEFAULT_CATALOG_TYPES, *[value for value in values if value]})
    return catalog_types


def catalog_overview() -> list[dict]:
    db = get_database()
    overview = []
    for catalog_type in list_catalog_types():
        count = db.system_catalogs.count_documents({"catalog_type": catalog_type})
        overview.append({"catalog_type": catalog_type, "count": count})
    return overview


def create_catalog_item(document: dict) -> None:
    get_database().system_catalogs.update_one(
        {"catalog_type": document["catalog_type"], "code": document["code"]},
        {"$setOnInsert": document},
        upsert=True,
    )


def update_catalog_item(catalog_type: str, code: str, changes: dict) -> None:
    get_database().system_catalogs.update_one(
        {"catalog_type": catalog_type, "code": code},
        {"$set": changes},
    )


def delete_catalog_item(catalog_type: str, code: str) -> None:
    get_database().system_catalogs.delete_one({"catalog_type": catalog_type, "code": code})
