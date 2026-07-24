from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid

from src.app.modules.revenue.schemas import ModuleStatus
from src.database.connection import get_database


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="revenue",
        status="partial",
        description="Modulo de analytics y revenue con consulta analitica y operacion basica de tarifas y promociones.",
    )


def ensure_revenue_collections() -> dict[str, list[str]]:
    db = get_database()
    created_collections: list[str] = []
    for name in ("rate_plans", "hotel_rate_calendar", "rate_rules", "promotion_campaigns", "coupon_codes"):
        if name not in db.list_collection_names():
            try:
                db.create_collection(name)
                created_collections.append(name)
            except CollectionInvalid:
                pass

    index_specs: dict[str, list[tuple[str, tuple | str, dict]]] = {
        "rate_plans": [
            ("rate_plan_id_1", [("rate_plan_id", 1)], {"unique": True}),
            ("prop_id_1", "prop_id", {}),
            ("is_active_1", "is_active", {}),
        ],
        "hotel_rate_calendar": [
            ("prop_rate_date", [("prop_id", 1), ("rate_plan_id", 1), ("date", 1)], {"unique": True}),
            ("date_1", "date", {}),
        ],
        "rate_rules": [
            ("rule_id_1", [("rule_id", 1)], {"unique": True}),
            ("rate_plan_id_1", "rate_plan_id", {}),
            ("prop_id_1", "prop_id", {}),
        ],
        "promotion_campaigns": [
            ("campaign_id_1", [("campaign_id", 1)], {"unique": True}),
            ("prop_id_1", "prop_id", {}),
            ("is_active_1", "is_active", {}),
        ],
        "coupon_codes": [
            ("coupon_code_1", [("coupon_code", 1)], {"unique": True}),
            ("campaign_id_1", "campaign_id", {}),
        ],
    }
    created_indexes: list[str] = []
    for col_name, specs in index_specs.items():
        col = db[col_name]
        existing_names = {idx["name"] for idx in col.list_indexes()}
        for idx_name, keys, kwargs in specs:
            if idx_name not in existing_names:
                col.create_index(keys, **kwargs)
                created_indexes.append(f"{idx_name}")
    return {"collections": created_collections, "indexes": created_indexes}


def _active_fact_collection() -> tuple[Collection, str]:
    db = get_database()
    if db.fact_hotel_reservations.estimated_document_count() > 0:
        return db.fact_hotel_reservations, "fact_hotel_reservations"
    return db.fact_hotel_events, "fact_hotel_events"


def _money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.2f}"


def _number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.{decimals}f}"


def _now() -> datetime:
    return datetime.now(UTC)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    text = _clean_text(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    text = _clean_text(value)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _safe_bool(value: Any) -> bool:
    return _clean_text(value).lower() in {"1", "true", "on", "yes", "si"}


def _slugify(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "item"


def _hotel_label(prop_id: int) -> str:
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0, "display_name": 1, "hotel_name": 1})
    if not hotel:
        return f"Hotel Partner {prop_id}"
    return hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel Partner {prop_id}"


def _lookup_map(collection_name: str, id_field: str, label_fields: list[str], ids: list[Any]) -> dict[Any, str]:
    if not ids:
        return {}
    db = get_database()
    projection = {"_id": 0, id_field: 1}
    for field in label_fields:
        projection[field] = 1
    lookup = {}
    for item in db[collection_name].find({id_field: {"$in": ids}}, projection):
        label = None
        for field in label_fields:
            label = item.get(field)
            if label:
                break
        lookup[item.get(id_field)] = label or str(item.get(id_field))
    return lookup
