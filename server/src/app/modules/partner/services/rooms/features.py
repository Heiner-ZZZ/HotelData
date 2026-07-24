"""Room features: configurable attribute tags for room types.

Each room type can have multiple feature tags like "Ocean View",
"Balcony", "Non-Smoking", "Accessible", "Quiet Zone", etc.

Features are stored as a simple array of strings on the room_type document
under the ``features`` field. A master catalog of available feature labels
is maintained in ``room_features`` collection for UI autocomplete.

Default features are seeded on first boot via ``seed_default_features()``
called from ``ensure_room_features_collections()`` in bootstrap.py.
"""

from __future__ import annotations

import json
import os
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc
from src.app.modules.partner.services.audit import register_action
from src.database.connection import get_database

# ── Icon resolution (DB-driven, no hardcoded data) ───────────────────

_icon_cache: dict[str, str] = {}


def _feature_icon(label: str) -> str:
    """Resolve a feature label to a Material Symbols icon from room_features.

    Used for custom features added at runtime — default features get their
    icons from the JSON seed, not this function.
    Falls back to ``"check"`` if the label is not found in the DB.
    """
    key = label.lower()
    if key in _icon_cache:
        return _icon_cache[key]
    db = get_database()
    doc = db.room_features.find_one({"label": label}, {"icon": 1})
    icon = doc.get("icon", "") if doc else ""
    result = icon or "check"
    _icon_cache[key] = result
    return result


# ── Default features loader ───────────────────────────────────────────

def _load_default_features() -> dict[str, list[dict[str, str]]]:
    """Load the default feature catalog from JSON — each entry has label + icon."""
    json_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "room_features_defaults.json",
    )
    try:
        with open(json_path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def seed_default_features() -> int:
    """Populate ``room_features`` with the built-in catalog on first boot.

    Uses upsert so it is idempotent — running it multiple times is safe.
    Icons come directly from the JSON file (not from DB) so the seed works
    correctly even on an empty database.
    """
    defaults = _load_default_features()
    if not defaults:
        return 0

    db = get_database()
    count = 0
    for category, entries in defaults.items():
        for entry in entries:
            label = entry["label"]
            icon = entry["icon"]
            result = db.room_features.update_one(
                {"label": label},
                {
                    "$setOnInsert": {
                        "label": label,
                        "category": category,
                        "icon": icon,
                        "created_by": "system",
                        "created_at": now_utc(),
                    },
                },
                upsert=True,
            )
            if result.upserted_id is not None:
                count += 1
    return count


def _lookup_feature_category(label: str) -> str:
    """Look up a feature's category from the room_features collection."""
    db = get_database()
    doc = db.room_features.find_one({"label": label}, {"category": 1})
    return doc.get("category", "") if doc else ""


# ── Public API ─────────────────────────────────────────────────────────


def get_all_features() -> list[dict[str, Any]]:
    """Return the master catalog of available features, grouped by category.

    Reads exclusively from the ``room_features`` collection.  Default
    features are seeded on first boot by ``ensure_room_features_collections()``.
    """
    db = get_database()

    cursor = db.room_features.find(
        {},
        {"_id": 0, "label": 1, "category": 1, "icon": 1},
    ).sort([("category", 1), ("label", 1)])

    merged: dict[str, list[dict[str, Any]]] = {}
    for doc in cursor:
        cat = doc.get("category") or "Otros"
        merged.setdefault(cat, []).append({
            "label": doc["label"],
            "category": cat,
            "icon": doc.get("icon", ""),
            "custom": doc.get("created_by") != "system",
            "source": "custom" if doc.get("created_by") != "system" else "feature",
        })

    result = []
    for category in sorted(merged.keys()):
        items = merged[category]
        items.sort(key=lambda x: x["label"].lower())
        result.append({"category": category, "items": items})
    return result


def _normalize_features(raw: Any) -> list[dict[str, Any]]:
    """Normalize features from DB (strings or objects) to a list of dicts."""
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for f in raw:
        if isinstance(f, dict):
            result.append({"label": str(f.get("label", ""))})
        elif isinstance(f, str):
            result.append({"label": f})
    return result


def get_room_type_features(prop_id: int, room_type_id: str) -> list[dict[str, Any]]:
    """Return the feature tags (with prices) for a specific room type."""
    db = get_database()
    room = db.room_types.find_one(
        {"prop_id": prop_id, "room_type_id": room_type_id},
        {"_id": 0, "features": 1},
    )
    if room is None:
        return []
    return _normalize_features(room.get("features", []))


def update_room_type_features(
    prop_id: int,
    room_type_id: str,
    *,
    features: list[str] | list[dict[str, Any]],
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    """Set the feature tags for a room type.

    Accepts either:
      - list of strings: legacy format
      - list of dicts with ``label``
    """
    db = get_database()
    room = db.room_types.find_one(
        {"prop_id": prop_id, "room_type_id": room_type_id},
        {"_id": 0, "name": 1},
    )
    if room is None:
        return None

    clean_objects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feat in features:
        if isinstance(feat, dict):
            label = clean_text(str(feat.get("label", "")))
        else:
            label = clean_text(str(feat))
        key = label.lower()
        if label and key not in seen:
            seen.add(key)
            clean_objects.append({"label": label})

    result = db.room_types.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": room_type_id},
        {"$set": {"features": clean_objects, "updated_at": now_utc()}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )

    room_name = room.get("name", room_type_id)
    register_action(
        prop_id=prop_id,
        entity_type="room_type",
        entity_id=room_type_id,
        action="update",
        summary=f"Caracteristicas de '{room_name}' actualizadas: {len(clean_objects)} atributos",
        changed_by=changed_by,
        metadata={"features_count": len(clean_objects)},
    )
    return result


def add_custom_feature(
    *,
    label: str,
    category: str = "",
    icon: str = "",
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    """Add a custom feature to the master catalog."""
    db = get_database()
    clean_label = clean_text(label)
    if not clean_label:
        raise ValueError("Debe indicar un nombre para la caracteristica.")

    clean_category = clean_text(category) or _lookup_feature_category(clean_label) or "Otros"
    clean_icon = clean_text(icon) or _feature_icon(clean_label)

    existing = db.room_features.find_one({"label": clean_label}, {"_id": 1})
    if existing is not None:
        raise ValueError(f"La caracteristica '{clean_label}' ya existe.")

    doc = {
        "label": clean_label,
        "category": clean_category,
        "icon": clean_icon,
        "created_by": changed_by,
        "created_at": now_utc(),
    }
    db.room_features.insert_one(doc)
    return doc
