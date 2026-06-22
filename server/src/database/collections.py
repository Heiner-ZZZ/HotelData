from __future__ import annotations

import logging

from pymongo import IndexModel, errors

from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _existing_indexes(collection) -> list[dict]:
    return list(collection.list_indexes())


def _keys_match(idx_spec: dict, keys: list) -> bool:
    spec_keys = list(idx_spec.get("key", {}).items())
    return spec_keys == keys


def ensure_collection(name: str, indexes: list[IndexModel]) -> list[str]:
    db = get_database()
    created: list[str] = []
    if name not in db.list_collection_names():
        try:
            db.create_collection(name)
            created.append(f"collection:{name}")
        except Exception:
            pass
    col = db[name]
    existing = _existing_indexes(col)
    existing_names = {e["name"] for e in existing}
    for idx in indexes:
        idx_name = idx.document["name"]
        if idx_name in existing_names:
            continue
        idx_keys = list(idx.document["key"].items())
        conflict = next(
            (e for e in existing if _keys_match(e, idx_keys) and e["name"] != "_id_"),
            None,
        )
        if conflict:
            logger.warning(
                "Dropping conflicting index '%s' on %s to create '%s'",
                conflict["name"], name, idx_name,
            )
            try:
                col.drop_index(conflict["name"])
            except Exception:
                pass
        try:
            col.create_indexes([idx])
            created.append(f"index:{idx_name}")
        except errors.OperationFailure as exc:
            logger.error("Failed to create index '%s' on %s: %s", idx_name, name, exc)
    return created


def drop_index_safe(collection_name: str, index_name: str) -> None:
    db = get_database()
    try:
        db[collection_name].drop_index(index_name)
    except Exception:
        pass
