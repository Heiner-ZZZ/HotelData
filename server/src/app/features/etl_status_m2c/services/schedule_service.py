"""Configuración horaria del DAG mongo_to_clickhouse (colección ``etl_pipeline_config``).

La UI de monitoreo lee/escribe aquí; el DAG lee el mismo documento al parsearse.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from config.settings import get_settings
from src.etl.mongo_to_clickhouse.config import (
    DEFAULT_REFRESH_MODE,
    DEFAULT_SCHEDULE_CRON,
    ETL_PIPELINE_CONFIG_COLLECTION,
    PIPELINE,
    REFRESH_MODES,
)


def _collection():
    settings = get_settings()
    from src.database.connection import get_database

    return get_database()[ETL_PIPELINE_CONFIG_COLLECTION]


def get_schedule() -> dict:
    doc = _collection().find_one({"pipeline": PIPELINE})
    if not doc:
        return {
            "pipeline": PIPELINE,
            "schedule_cron": DEFAULT_SCHEDULE_CRON,
            "enabled": True,
            "configured": False,
            "refresh_mode": DEFAULT_REFRESH_MODE,
            "updated_at": "",
            "updated_by": "",
        }
    mode = doc.get("refresh_mode")
    if mode not in REFRESH_MODES:
        mode = DEFAULT_REFRESH_MODE
    return {
        "id": str(doc.get("_id", "")),
        "pipeline": doc.get("pipeline", PIPELINE),
        "schedule_cron": doc.get("schedule_cron", DEFAULT_SCHEDULE_CRON),
        "enabled": bool(doc.get("enabled", True)),
        "configured": True,
        "refresh_mode": mode,
        "updated_at": doc.get("updated_at", ""),
        "updated_by": doc.get("updated_by", ""),
    }


def update_schedule(
    schedule_cron: str,
    enabled: bool,
    refresh_mode: str | None = None,
    updated_by: str = "system",
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    if refresh_mode is not None and refresh_mode not in REFRESH_MODES:
        raise ValueError(
            f"refresh_mode desconocido: {refresh_mode!r} (válidos: {', '.join(REFRESH_MODES)})"
        )
    update: dict[str, Any] = {
        "schedule_cron": schedule_cron,
        "enabled": bool(enabled),
        "updated_at": now,
        "updated_by": updated_by,
    }
    if refresh_mode is not None:
        update["refresh_mode"] = refresh_mode
    _collection().update_one(
        {"pipeline": PIPELINE},
        {"$set": update, "$setOnInsert": {"_id": ObjectId()}},
        upsert=True,
    )
    return get_schedule()
